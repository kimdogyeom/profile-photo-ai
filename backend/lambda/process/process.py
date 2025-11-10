import boto3
import os
import json
import sys
import time
import resource
from urllib.parse import urlparse
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from datetime import datetime

# Lambda Layer에서 dynamodb_helper 및 logging_helper 임포트
sys.path.append('/opt/python')
from dynamodb_helper import ImageJobService, UserService
from logging_helper import StructuredLogger

# AWS 클라이언트 초기화 (LocalStack 지원)
endpoint_url = os.environ.get('AWS_ENDPOINT_URL')
if endpoint_url:
    print(f"Using LocalStack S3 endpoint: {endpoint_url}")
    s3_client = boto3.client('s3', endpoint_url=endpoint_url)
else:
    print("Using AWS S3")
    s3_client = boto3.client('s3')

secretsmanager_client = boto3.client('secretsmanager')
api_gateway_client = None  # WebSocket 사용 시에만 초기화

# Gemini API 키 가져오기 (Secrets Manager 또는 환경 변수)
def get_gemini_api_key():
    """Secrets Manager에서 Gemini API 키를 가져오거나 환경 변수에서 읽기"""
    # 1. 환경 변수에서 직접 확인 (로컬 테스트용)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print("Using GEMINI_API_KEY from environment variable")
        return api_key

    # 2. Secrets Manager ARN에서 가져오기 (프로덕션)
    secret_arn = os.environ.get("GEMINI_API_KEY_SECRET_ARN")
    if secret_arn:
        try:
            print(f"Retrieving Gemini API key from Secrets Manager: {secret_arn}")
            response = secretsmanager_client.get_secret_value(SecretId=secret_arn)
            secret_string = response['SecretString']

            # JSON이 아니면 plain text로 처리
            return secret_string.strip()
        except Exception as e:
            print(f"Error retrieving Gemini API key from Secrets Manager: {e}")
    
    raise ValueError("GEMINI_API_KEY not found in Secrets Manager or environment variables")

# Gemini API 설정
GEMINI_API_KEY = get_gemini_api_key()

# google-genai 클라이언트 초기화
client = genai.Client(api_key=GEMINI_API_KEY)

# 환경 변수
RESULT_BUCKET = os.environ.get('RESULT_BUCKET', 'profilephotoai-results-final')
MODEL_NAME = os.environ.get('MODEL_NAME', 'gemini-2.5-flash-image')
WEBSOCKET_ENDPOINT = os.environ.get("WEBSOCKET_ENDPOINT")

# WebSocket 클라이언트 초기화 (사용 가능한 경우)
if WEBSOCKET_ENDPOINT:
    api_gateway_client = boto3.client('apigatewaymanagementapi', endpoint_url=WEBSOCKET_ENDPOINT)


def lambda_handler(event, context):
    """
    SQS 메시지를 처리하여 Gemini API로 이미지를 생성하고 결과를 S3에 저장합니다.
    DynamoDB에 작업 상태를 업데이트하고, WebSocket이 있으면 실시간 알림을 전송합니다.
    """
    log = StructuredLogger('ImageProcessFunction', context.request_id)
    processed_count = 0
    failed_count = 0
    
    for record in event['Records']:
        job_id = None
        user_id = None
        start_time = time.time()
        
        try:
            # SQS 메시지 파싱
            message_body = json.loads(record['body'])
            job_id = message_body.get('jobId')
            user_id = message_body.get('userId')
            s3_uri = message_body.get('s3_uri')
            prompt = message_body.get('prompt')
            style = message_body.get('style', 'professional')
            connection_id = message_body.get('connectionId')  # WebSocket (선택적)

            log.info('job_processing_started',
                jobId=job_id,
                userId=user_id,
                style=style,
                s3Uri=s3_uri)

            # 필수 데이터 검증
            if not all([job_id, user_id, s3_uri, prompt]):
                raise ValueError("Missing required data in SQS message")

            # Job 상태를 processing으로 업데이트
            ImageJobService.update_job_status(job_id, 'processing')

            # 1. S3에서 입력 이미지 다운로드
            parsed_uri = urlparse(s3_uri)
            input_bucket = parsed_uri.netloc
            input_key = parsed_uri.path.lstrip('/')

            download_start = time.time()
            response = s3_client.get_object(Bucket=input_bucket, Key=input_key)
            input_image_bytes = response['Body'].read()
            input_image = Image.open(BytesIO(input_image_bytes))
            download_time = (time.time() - download_start) * 1000

            log.info('image_downloaded',
                jobId=job_id,
                fileSize=len(input_image_bytes),
                downloadTime=download_time,
                imageSize=f"{input_image.width}x{input_image.height}")

            # 2. Gemini 2.5 Flash Image API로 이미지 생성 요청 (google-genai)
            log.info('gemini_api_request',
                jobId=job_id,
                promptLength=len(prompt),
                modelName=MODEL_NAME)
            
            generation_start = time.time()
            
            # PIL Image를 bytes로 변환
            img_byte_arr = BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            image_bytes = img_byte_arr.read()
            
            # google-genai API로 이미지 생성 요청
            # 텍스트와 이미지를 함께 전달
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    prompt,  # 텍스트 프롬프트
                    types.Part(inline_data=types.Blob(
                        data=image_bytes,
                        mime_type='image/png'
                    ))
                ]
            )
            
            generation_time = (time.time() - generation_start) * 1000
            
            # 느린 응답 경고
            if generation_time > 30000:  # 30초 초과
                log.warning('gemini_api_slow_response',
                    jobId=job_id,
                    responseTime=generation_time,
                    threshold=30000)

            # 응답 검증
            if not response.candidates:
                raise Exception("Image generation failed: no candidates in response")
            
            candidate = response.candidates[0]
            
            # finish_reason 확인
            if hasattr(candidate, 'finish_reason'):
                finish_reason = str(candidate.finish_reason)
                if 'STOP' not in finish_reason.upper() and finish_reason != '1':
                    log.warning('unexpected_finish_reason',
                        jobId=job_id,
                        finishReason=finish_reason)
            
            
            # 응답에서 생성된 이미지 데이터 추출
            generated_image_bytes = None
            
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    # inline_data 속성 확인 (생성된 이미지)
                    if hasattr(part, 'inline_data') and part.inline_data:
                        generated_image_bytes = part.inline_data.data
                        mime_type = getattr(part.inline_data, 'mime_type', 'unknown')
                        log.info('gemini_api_success',
                            jobId=job_id,
                            responseTime=generation_time,
                            mimeType=mime_type,
                            imageSize=len(generated_image_bytes))
                        break
                    # text 응답인 경우 (설명만 생성된 경우)
                    elif hasattr(part, 'text') and part.text:
                        log.warning('gemini_text_response',
                            jobId=job_id,
                            textPreview=part.text[:200])

            if not generated_image_bytes:
                error_msg = "Image generation failed: no image data in response"
                log.error('gemini_api_error',
                    jobId=job_id,
                    error=error_msg,
                    responseStructure=str(candidate)[:500])
                raise Exception(error_msg)

            log.info('image_generated',
                jobId=job_id,
                generationTime=generation_time,
                outputSize=len(generated_image_bytes))

            # 3. 생성된 이미지를 결과 S3 버킷에 업로드
            output_key = f"generated/{user_id}/{job_id}.png"
            upload_start = time.time()
            
            s3_client.put_object(
                Bucket=RESULT_BUCKET,
                Key=output_key,
                Body=generated_image_bytes,
                ContentType='image/png',
                ServerSideEncryption='AES256',
                Metadata={
                    'userId': user_id,
                    'jobId': job_id,
                    'style': style,
                    'generatedAt': datetime.utcnow().isoformat()
                }
            )
            
            upload_time = (time.time() - upload_start) * 1000
            output_s3_uri = f"s3://{RESULT_BUCKET}/{output_key}"
            
            log.info('s3_upload_success',
                jobId=job_id,
                s3Uri=output_s3_uri,
                uploadTime=upload_time,
                fileSize=len(generated_image_bytes))

            # 5. DynamoDB에 작업 완료 상태 업데이트 (S3 URI만 저장)
            processing_time = (time.time() - start_time) * 1000
            ImageJobService.update_job_status(
                job_id=job_id,
                status='completed',
                output_url=output_s3_uri,  # S3 URI 저장 (API에서 Presigned URL 생성)
                processing_time=float(processing_time),
                metadata={
                    'generationTime': float(generation_time),
                    'modelName': MODEL_NAME,
                    'outputKey': output_key,  # Presigned URL 생성에 사용
                    's3Uri': output_s3_uri
                }
            )

            # 6. 사용자 통계 업데이트
            UserService.increment_total_images(user_id)
            
            # 메모리 사용량 추적
            memory_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB
            
            log.info('job_completed',
                jobId=job_id,
                userId=user_id,
                processingTime=processing_time,
                generationTime=generation_time,
                downloadTime=download_time,
                uploadTime=upload_time,
                memoryUsed=memory_used,
                outputSize=len(generated_image_bytes))

            # 7. WebSocket으로 결과 전송 (연결이 있는 경우)
            if connection_id and api_gateway_client:
                try:
                    notification_data = {
                        'type': 'image_completed',
                        'jobId': job_id,
                        'status': 'completed',
                        's3Uri': output_s3_uri,
                        'processingTime': processing_time
                    }
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps(notification_data).encode('utf-8')
                    )
                    log.info('websocket_notification_sent',
                        jobId=job_id,
                        connectionId=connection_id,
                        notificationType='image_completed')
                except Exception as ws_error:
                    log.warning('websocket_notification_failed',
                        jobId=job_id,
                        connectionId=connection_id,
                        error=str(ws_error))

            processed_count += 1

        except Exception as e:
            failed_count += 1
            error_message = str(e)
            
            import traceback
            error_traceback = traceback.format_exc()
            
            # 메모리 사용량 추적 (에러 시에도)
            try:
                memory_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            except:
                memory_used = None
            
            log.error('job_failed',
                jobId=job_id,
                userId=user_id,
                error=error_message,
                errorType=type(e).__name__,
                processingTime=(time.time() - start_time) * 1000 if start_time else None,
                memoryUsed=memory_used,
                traceback=error_traceback[:500])

            # DynamoDB에 실패 상태 기록
            if job_id:
                try:
                    processing_time = (time.time() - start_time) * 1000
                    ImageJobService.update_job_status(
                        job_id=job_id,
                        status='failed',
                        error=error_message,
                        processing_time=processing_time
                    )
                except Exception as db_error:
                    log.error('dynamodb_update_failed',
                        jobId=job_id,
                        error=str(db_error),
                        errorType=type(db_error).__name__)

            # WebSocket으로 에러 메시지 전송 (연결이 있는 경우)
            if 'connection_id' in locals() and connection_id and api_gateway_client:
                try:
                    error_notification = {
                        'type': 'image_failed',
                        'jobId': job_id,
                        'status': 'failed',
                        'error': error_message
                    }
                    api_gateway_client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps(error_notification).encode('utf-8')
                    )
                    log.info('websocket_error_notification_sent',
                        jobId=job_id,
                        connectionId=connection_id)
                except Exception as api_error:
                    log.warning('websocket_error_notification_failed',
                        jobId=job_id,
                        error=str(api_error))

    # 최종 배치 처리 결과
    log.info('batch_processing_complete',
        totalRecords=len(event['Records']),
        processedCount=processed_count,
        failedCount=failed_count)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Processing complete',
            'processed': processed_count,
            'failed': failed_count
        })
    }
