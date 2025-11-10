import boto3
import json
import os
import sys
import time
from datetime import datetime
from decimal import Decimal

# Lambda Layer에서 dynamodb_helper 및 logging_helper 임포트
sys.path.append('/opt/python')
from dynamodb_helper import UserService, UsageService, ImageJobService
from logging_helper import StructuredLogger

# AWS 클라이언트 초기화 (LocalStack 지원)
endpoint_url = os.environ.get('AWS_ENDPOINT_URL')
if endpoint_url:
    print(f"Using LocalStack endpoint: {endpoint_url}")
    sqs_client = boto3.client('sqs', endpoint_url=endpoint_url)
    s3_client = boto3.client('s3', endpoint_url=endpoint_url)
else:
    print("Using AWS services")
    sqs_client = boto3.client('sqs')
    s3_client = boto3.client('s3')

# 환경 변수
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET', 'profilephotoai-uploads-raw')


def lambda_handler(event, context):
    """
    API Gateway 요청을 라우팅하여 적절한 핸들러로 전달합니다.
    
    지원 엔드포인트:
    - POST /generate: 이미지 생성 요청
    - GET /jobs/{jobId}: Job 상태 조회
    - GET /user/me: 사용자 정보 조회
    - GET /user/jobs: 사용자 작업 목록 조회
    """
    try:
        # HTTP 메서드 및 경로 추출
        http_method = event.get('requestContext', {}).get('http', {}).get('method') or \
                     event.get('requestContext', {}).get('httpMethod')
        raw_path = event.get('rawPath') or event.get('path', '')
        
        # API Gateway v2 HTTP API는 스테이지명을 경로에 포함시킵니다
        # 스테이지명 제거 (예: /dev/user/me -> /user/me)
        stage = event.get('requestContext', {}).get('stage', '')
        if stage and raw_path.startswith(f'/{stage}/'):
            raw_path = raw_path[len(f'/{stage}'):]
        
        print(f"Request: {http_method} {raw_path}")
        
        # OPTIONS 처리 (CORS preflight)
        if http_method == 'OPTIONS':
            return cors_response(200, {})
        
        # 경로 기반 라우팅
        if http_method == 'POST' and raw_path == '/generate':
            return handle_generate_image(event, context)
        
        if http_method == 'GET' and raw_path.startswith('/jobs/'):
            # /jobs/{jobId}/download 경로 체크
            if raw_path.endswith('/download'):
                return handle_download_image(event, context)
            return handle_get_job(event, context)
        
        if http_method == 'GET' and raw_path == '/user/me':
            return handle_get_user_info(event, context)
        
        if http_method == 'GET' and raw_path == '/user/jobs':
            return handle_get_user_jobs(event, context)
        
        # 지원하지 않는 경로
        return cors_response(404, {'error': 'Not Found'})
        
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        import traceback
        traceback.print_exc()
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})


def handle_generate_image(event, context):
    """이미지 생성 요청 처리 (POST /generate)"""
    log = StructuredLogger('ApiManagerFunction', context.request_id)
    start_time = time.time()
    
    try:
        # Cognito 사용자 ID 추출
        user_id = extract_user_id(event)
        if not user_id:
            log.error('user_id_not_found',
                requestContext=event.get('requestContext', {}))
            return cors_response(401, {'error': 'Unauthorized: User ID not found'})
        
        # 요청 본문 파싱
        body = parse_request_body(event)
        if not body:
            log.error('invalid_request_body',
                userId=user_id,
                body=event.get('body', '')[:100])
            return cors_response(400, {'error': 'Invalid request body'})
        
        file_key = body.get('fileKey')
        prompt = body.get('prompt', '')
        
        # Job 생성 요청 로깅
        log.info('job_create_request',
            userId=user_id,
            fileKey=file_key,
            promptLength=len(prompt))
        
        # 입력 검증
        validation_error = validate_generation_request(file_key, prompt)
        if validation_error:
            log.warning('validation_failed',
                userId=user_id,
                fileKey=file_key,
                reason=validation_error)
            return cors_response(400, {'error': validation_error})
        
        # S3 파일 존재 확인
        if not verify_s3_file_exists(UPLOAD_BUCKET, file_key):
            log.warning('s3_file_not_found',
                userId=user_id,
                bucket=UPLOAD_BUCKET,
                fileKey=file_key)
            return cors_response(404, {'error': 'Uploaded file not found in S3'})
        
        # 사용자 정보 조회 및 생성
        user = UserService.get_user(user_id)
        if not user:
            # 신규 사용자 생성 (Cognito 정보로부터)
            user_data = extract_user_data(event)
            user = UserService.create_or_update_user(user_data)
            log.info('user_created',
                userId=user_id,
                email=user_data.get('email'))
        
        # 사용량 체크
        can_generate, remaining = UsageService.can_generate_image(user_id)
        if not can_generate:
            log.warning('quota_exceeded',
                userId=user_id,
                currentUsage=UsageService.DAILY_LIMIT,
                dailyLimit=UsageService.DAILY_LIMIT,
                remainingQuota=0)
            return cors_response(429, {
                'error': 'Daily quota exceeded',
                'remainingQuota': 0,
                'message': 'You have reached your daily limit. Please try again tomorrow.'
            })
        
        # S3 URI 생성
        s3_uri = f"s3://{UPLOAD_BUCKET}/{file_key}"
        
        # ImageJob 생성
        job_id = ImageJobService.create_job(
            user_id=user_id,
            style='custom',  # 클라이언트에서 프롬프트 관리
            input_url=s3_uri,
            prompt=prompt
        )
        
        log.info('job_created',
            jobId=job_id,
            userId=user_id,
            inputUrl=s3_uri)
        
        # SQS 메시지 발행
        message_body = {
            'jobId': job_id,
            'userId': user_id,
            's3_uri': s3_uri,
            'prompt': prompt,
            'style': 'custom',
            'createdAt': datetime.utcnow().isoformat()
        }
        
        try:
            sqs_response = sqs_client.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    'userId': {
                        'StringValue': user_id,
                        'DataType': 'String'
                    },
                    'jobId': {
                        'StringValue': job_id,
                        'DataType': 'String'
                    }
                }
            )
            
            log.info('sqs_publish_success',
                jobId=job_id,
                userId=user_id,
                messageId=sqs_response['MessageId'])
            
            # SQS 발행 성공 시에만 사용량 차감
            new_usage = UsageService.increment_usage(user_id)
            remaining_quota = UsageService.DAILY_LIMIT - new_usage
            
            log.info('usage_incremented',
                userId=user_id,
                currentUsage=new_usage,
                remainingQuota=remaining_quota)
            
            # Job 상태를 queued로 업데이트
            ImageJobService.update_job_status(
                job_id=job_id,
                status='queued',
                metadata={'sqsMessageId': sqs_response['MessageId']}
            )
            
            # 처리 시간 측정
            processing_time = (time.time() - start_time) * 1000
            
            log.info('job_queued',
                jobId=job_id,
                userId=user_id,
                processingTime=processing_time)
            
            # 성공 응답
            return cors_response(200, {
                'jobId': job_id,
                'status': 'queued',
                'remainingQuota': remaining_quota,
                'message': 'Image generation request has been queued successfully'
            })
            
        except Exception as sqs_error:
            # SQS 발행 실패 시 Job을 failed로 표시
            log.error('sqs_publish_failed',
                error=sqs_error,
                jobId=job_id,
                userId=user_id)
            ImageJobService.update_job_status(
                job_id=job_id,
                status='failed',
                error=f"Failed to queue job: {str(sqs_error)}"
            )
            return cors_response(500, {
                'error': 'Failed to queue image generation request',
                'jobId': job_id
            })
        
    except Exception as e:
        log.error('job_creation_failed',
            error=e,
            userId=user_id if 'user_id' in locals() else None)
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})


def handle_get_job(event, context):
    """Job 상태 조회 (GET /jobs/{jobId})"""
    log = StructuredLogger('ApiManagerFunction', context.request_id)
    
    try:
        # 사용자 ID 추출
        user_id = extract_user_id(event)
        if not user_id:
            log.error('user_id_not_found')
            return cors_response(401, {'error': 'Unauthorized: User ID not found'})
        
        # Path에서 jobId 추출
        raw_path = event.get('rawPath') or event.get('path', '')
        job_id = raw_path.split('/')[-1]
        
        if not job_id:
            log.warning('job_id_missing',
                userId=user_id)
            return cors_response(400, {'error': 'jobId is required'})
        
        log.info('job_status_query',
            jobId=job_id,
            userId=user_id)
        
        # DynamoDB에서 Job 조회
        job = ImageJobService.get_job(job_id)
        
        if not job:
            log.warning('job_not_found',
                jobId=job_id,
                userId=user_id)
            return cors_response(404, {'error': 'Job not found'})
        
        # 권한 확인: 본인의 Job만 조회 가능
        if job.get('userId') != user_id:
            log.warning('job_access_denied',
                jobId=job_id,
                userId=user_id,
                jobOwner=job.get('userId'))
            return cors_response(403, {'error': 'Forbidden: Access denied'})
        
        log.info('job_retrieved',
            jobId=job_id,
            userId=user_id,
            status=job.get('status'))
        
        # 응답 반환
        return cors_response(200, job)
        
    except Exception as e:
        log.error('job_retrieval_failed',
            error=e,
            jobId=job_id if 'job_id' in locals() else None,
            userId=user_id if 'user_id' in locals() else None)
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})


def handle_get_user_info(event, context):
    """사용자 정보 조회 (GET /user/me)"""
    try:
        user_id = extract_user_id(event)
        if not user_id:
            return cors_response(401, {'error': 'Unauthorized: User ID not found'})
        
        print(f"Getting user info for {user_id}")
        
        # 사용자 정보 조회
        user = UserService.get_user(user_id)
        if not user:
            # 신규 사용자 생성
            user_data = extract_user_data(event)
            user = UserService.create_or_update_user(user_data)
            print(f"Created new user on info request: {user_id}")
        
        # 오늘 사용량 조회
        can_generate, remaining = UsageService.can_generate_image(user_id)
        daily_limit = int(os.environ.get('DAILY_LIMIT', 10))
        used_today = daily_limit - remaining
        
        # 응답 구성
        response = {
            'userId': user.get('userId'),
            'email': user.get('email', ''),
            'displayName': user.get('displayName', ''),
            'profileImage': user.get('profileImage', ''),
            'provider': user.get('provider', 'cognito'),
            'dailyLimit': daily_limit,
            'remainingQuota': remaining,
            'usedToday': used_today,
            'totalImages': user.get('totalImagesGenerated', 0),
            'createdAt': user.get('createdAt', ''),
            'lastLoginAt': user.get('lastLoginAt', '')
        }
        
        return cors_response(200, response)
        
    except Exception as e:
        print(f"Error getting user info: {e}")
        import traceback
        traceback.print_exc()
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})


def handle_get_user_jobs(event, context):
    """사용자 작업 목록 조회 (GET /user/jobs)"""
    try:
        user_id = extract_user_id(event)
        if not user_id:
            return cors_response(401, {'error': 'Unauthorized: User ID not found'})
        
        # 쿼리 파라미터 파싱
        query_params = event.get('queryStringParameters') or {}
        limit = min(int(query_params.get('limit', 20)), 100)  # 최대 100
        status = query_params.get('status', 'all')
        
        print(f"Getting jobs for user {user_id}, limit={limit}, status={status}")
        
        # DynamoDB 조회
        result = ImageJobService.get_user_jobs(
            user_id=user_id,
            limit=limit,
            status=status if status != 'all' else None
        )
        
        jobs = result.get('jobs', [])
        
        # 응답 구성
        response = {
            'jobs': jobs,
            'total': len(jobs),
            'limit': limit,
            'hasMore': result.get('lastEvaluatedKey') is not None
        }
        
        return cors_response(200, response)
        
    except Exception as e:
        print(f"Error getting user jobs: {e}")
        import traceback
        traceback.print_exc()
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})


def handle_download_image(event, context):
    """이미지 다운로드 Presigned URL 생성 (GET /jobs/{jobId}/download)"""
    try:
        user_id = extract_user_id(event)
        if not user_id:
            return cors_response(401, {'error': 'Unauthorized: User ID not found'})
        
        # Path에서 jobId 추출
        raw_path = event.get('rawPath') or event.get('path', '')
        # /jobs/{jobId}/download -> jobId 추출
        path_parts = raw_path.split('/')
        job_id = path_parts[-2] if len(path_parts) >= 3 else None
        
        if not job_id:
            return cors_response(400, {'error': 'jobId is required'})
        
        print(f"Generating download URL for job {job_id}, user {user_id}")
        
        # DynamoDB에서 Job 조회
        job = ImageJobService.get_job(job_id)
        
        if not job:
            return cors_response(404, {'error': 'Job not found'})
        
        # 권한 확인: 본인의 Job만 다운로드 가능
        if job.get('userId') != user_id:
            return cors_response(403, {'error': 'Forbidden: Access denied'})
        
        # Job이 완료되지 않은 경우
        if job.get('status') != 'completed':
            return cors_response(400, {'error': 'Job not completed yet'})
        
        # outputImageUrl에서 S3 키 추출 (metadata에 저장된 경우)
        output_key = None
        metadata = job.get('metadata', {})
        
        if 'outputKey' in metadata:
            output_key = metadata['outputKey']
        elif 's3Uri' in metadata:
            # s3://bucket/key 형식에서 키 추출
            s3_uri = metadata['s3Uri']
            output_key = s3_uri.split('/', 3)[3] if s3_uri.startswith('s3://') else None
        
        if not output_key:
            return cors_response(404, {'error': 'Output image not found'})
        
        # Presigned URL 생성 (이 Lambda의 Role 권한 사용)
        result_bucket = os.environ.get('RESULT_BUCKET', 'profilephotoai-results-final')
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': result_bucket,
                'Key': output_key
            },
            ExpiresIn=3600  # 1시간
        )
        
        print(f"Generated presigned URL for {output_key}")
        
        return cors_response(200, {
            'downloadUrl': presigned_url,
            'expiresIn': 3600,
            'jobId': job_id
        })
        
    except Exception as e:
        print(f"Error generating download URL: {e}")
        import traceback
        traceback.print_exc()
        return cors_response(500, {'error': f'Internal server error: {str(e)}'})


def extract_user_id(event):
    """API Gateway에서 전달된 Cognito 사용자 ID 추출"""
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # HTTP API (JWT authorizer)
        jwt = authorizer.get('jwt', {})
        if jwt:
            claims = jwt.get('claims', {})
            user_id = claims.get('sub') or claims.get('cognito:username')
            if user_id:
                return user_id
        
        # REST API (Cognito User Pool)
        claims = authorizer.get('claims', {})
        user_id = claims.get('sub') or claims.get('cognito:username')
        if user_id:
            return user_id
        
        # Lambda authorizer
        user_id = authorizer.get('principalId') or authorizer.get('userId')
        
        return user_id
    except Exception as e:
        print(f"Error extracting user ID: {e}")
        return None


def extract_user_data(event):
    """Cognito에서 사용자 데이터 추출"""
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # HTTP API (JWT authorizer)
        jwt = authorizer.get('jwt', {})
        if jwt:
            claims = jwt.get('claims', {})
        else:
            # REST API (Cognito User Pool)
            claims = authorizer.get('claims', {})
        
        return {
            'userId': claims.get('sub') or claims.get('cognito:username'),
            'email': claims.get('email', ''),
            'displayName': claims.get('name') or claims.get('cognito:username', ''),
            'profileImage': claims.get('picture', ''),
            'provider': extract_provider(claims)
        }
    except Exception as e:
        print(f"Error extracting user data: {e}")
        return None


def extract_provider(claims):
    """로그인 제공자 추출 (Google 등)"""
    identities = claims.get('identities')
    if identities:
        try:
            identities_data = json.loads(identities) if isinstance(identities, str) else identities
            if isinstance(identities_data, list) and len(identities_data) > 0:
                return identities_data[0].get('providerName', 'cognito')
        except:
            pass
    return 'cognito'


def parse_request_body(event):
    """요청 본문 파싱"""
    try:
        body = event.get('body', '{}')
        if isinstance(body, str):
            return json.loads(body)
        return body
    except json.JSONDecodeError as e:
        print(f"Error parsing request body: {e}")
        return None


def validate_generation_request(file_key, prompt):
    """이미지 생성 요청 유효성 검증"""
    if not file_key:
        return "fileKey is required"
    
    if not prompt:
        return "prompt is required"
    
    if len(prompt) > 2000:
        return "prompt is too long (max 2000 characters)"
    
    # 파일 키 형식 검증 (uploads/userId/filename)
    if not file_key.startswith('uploads/'):
        return "Invalid file key format"
    
    return None


def verify_s3_file_exists(bucket, key):
    """S3 파일 존재 여부 확인"""
    try:
        print(f"HEAD object request: Bucket={bucket}, Key={key}")
        response = s3_client.head_object(Bucket=bucket, Key=key)
        print(f"File exists: s3://{bucket}/{key}, Size={response.get('ContentLength')}")
        return True
    except Exception as e:
        error_code = e.response['Error']['Code'] if hasattr(e, 'response') else 'Unknown'
        print(f"Error checking S3 file (Code: {error_code}): {e}")
        print(f"Attempted: s3://{bucket}/{key}")
        if error_code == '404':
            return False
        else:
            raise


def cors_response(status_code, body):
    """CORS 헤더가 포함된 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,GET,OPTIONS'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal을 JSON으로 변환하는 커스텀 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Decimal을 int 또는 float로 변환
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)
