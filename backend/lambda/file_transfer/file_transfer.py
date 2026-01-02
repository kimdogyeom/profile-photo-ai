import json
import os
import time
import uuid
from datetime import datetime

import boto3
# AWS Lambda Powertools
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths

# Powertools 초기화
logger = Logger()
tracer = Tracer()

# AWS 클라이언트 초기화 (LocalStack 지원)
endpoint_url = os.environ.get('AWS_ENDPOINT_URL')
if endpoint_url:
    logger.info("Using LocalStack S3 endpoint", extra={"endpoint_url": endpoint_url})
    s3_client = boto3.client('s3', endpoint_url=endpoint_url)
else:
    logger.info("Using AWS S3")
    s3_client = boto3.client('s3')

# 환경 변수
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET', 'profilephotoai-uploads-raw')
PRESIGNED_URL_EXPIRATION = int(os.environ.get('PRESIGNED_URL_EXPIRATION', '3600'))  # 1시간

# 허용된 파일 확장자 및 MIME 타입
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_CONTENT_TYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp'
}

# 파일 크기 제한 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    """
    클라이언트의 파일 업로드 요청을 받아 S3 Presigned URL을 생성하여 반환합니다.
    
    Request Body:
    {
        "fileName": "profile.jpg",
        "contentType": "image/jpeg",
        "fileSize": 1024000
    }
    
    Response:
    {
        "uploadUrl": "https://s3.amazonaws.com/...",
        "fileKey": "uploads/user123/uuid.jpg",
        "expiresIn": 3600
    }
    """
    # 요청 시작 시간 기록
    request_start_time = time.time()
    
    try:
        # Cognito 사용자 ID 추출
        user_id = extract_user_id(event)
        if not user_id:
            logger.error('user_id_not_found',
                requestContext=event.get('requestContext', {}))
            return error_response(401, "Unauthorized: User ID not found")
        
        # 요청 본문 파싱
        body = parse_request_body(event)
        if not body:
            logger.error('invalid_request_body',
                userId=user_id,
                body=event.get('body', '')[:100])  # 처음 100자만 로깅
            return error_response(400, "Invalid request body")
        
        file_name = body.get('fileName')
        content_type = body.get('contentType')
        file_size = body.get('fileSize', 0)
        
        # 업로드 요청 로깅
        logger.info('upload_request',
            userId=user_id,
            fileName=file_name,
            contentType=content_type,
            fileSize=file_size)
        
        # 입력 검증
        validation_error = validate_upload_request(file_name, content_type, file_size)
        if validation_error:
            logger.warning('validation_failed',
                userId=user_id,
                fileName=file_name,
                contentType=content_type,
                fileSize=file_size,
                reason=validation_error)
            return error_response(400, validation_error)
        
        # 파일 확장자 추출
        file_extension = get_file_extension(file_name, content_type)
        
        # S3 키 생성 (uploads/userId/uuid.ext)
        file_key = generate_file_key(user_id, file_extension)
        
        # Presigned URL 생성
        presigned_url = generate_presigned_upload_url(
            bucket=UPLOAD_BUCKET,
            key=file_key,
            content_type=content_type,
            expiration=PRESIGNED_URL_EXPIRATION
        )
        
        # 처리 시간 계산
        processing_time = (time.time() - request_start_time) * 1000  # ms
        
        # 성공 로깅
        logger.info('presigned_url_created',
            userId=user_id,
            fileKey=file_key,
            bucket=UPLOAD_BUCKET,
            expiresIn=PRESIGNED_URL_EXPIRATION,
            processingTime=processing_time)
        
        # 성공 응답
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'fileKey': file_key,
                'expiresIn': PRESIGNED_URL_EXPIRATION,
                'bucket': UPLOAD_BUCKET
            })
        }
        
    except Exception as e:
        logger.error('presigned_url_failed',
            error=e,
            userId=user_id if 'user_id' in locals() else None)
        return error_response(500, f"Internal server error: {str(e)}")


def extract_user_id(event):
    """API Gateway에서 전달된 Cognito 사용자 ID 추출"""
    try:
        # API Gateway authorizer에서 설정한 사용자 정보
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # HTTP API (JWT authorizer)에서 오는 경우
        jwt = authorizer.get('jwt', {})
        if jwt:
            claims = jwt.get('claims', {})
            user_id = claims.get('sub') or claims.get('cognito:username')
            if user_id:
                return user_id
        
        # REST API (Cognito User Pool)에서 오는 경우
        claims = authorizer.get('claims', {})
        user_id = claims.get('sub') or claims.get('cognito:username')
        if user_id:
            return user_id
        
        # Lambda authorizer에서 오는 경우
        user_id = authorizer.get('principalId') or authorizer.get('userId')
        
        return user_id
    except Exception as e:
        logger.error("Error extracting user ID", extra={"error": str(e)})
        return None


def parse_request_body(event):
    """요청 본문 파싱"""
    try:
        body = event.get('body', '{}')
        if isinstance(body, str):
            return json.loads(body)
        return body
    except json.JSONDecodeError as e:
        logger.error("Error parsing request body", extra={"error": str(e)})
        return None


def validate_upload_request(file_name, content_type, file_size):
    """업로드 요청 유효성 검증"""
    if not file_name:
        return "fileName is required"
    
    if not content_type:
        return "contentType is required"
    
    if content_type not in ALLOWED_CONTENT_TYPES:
        return f"Unsupported content type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES.keys())}"
    
    # 파일 확장자 검증
    file_ext = os.path.splitext(file_name.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # 파일 크기 검증
    if file_size > MAX_FILE_SIZE:
        return f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB"
    
    if file_size <= 0:
        return "Invalid file size"
    
    return None


def get_file_extension(file_name, content_type):
    """파일 확장자 결정"""
    # 먼저 파일명에서 확장자 추출
    file_ext = os.path.splitext(file_name.lower())[1]
    
    # 확장자가 없거나 유효하지 않으면 content type에서 결정
    if not file_ext or file_ext not in ALLOWED_EXTENSIONS:
        file_ext = '.' + ALLOWED_CONTENT_TYPES.get(content_type, 'jpg')
    
    return file_ext


def generate_file_key(user_id, file_extension):
    """S3 파일 키 생성"""
    # UUID 생성으로 파일명 충돌 방지
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.utcnow().strftime('%Y%m%d')
    
    # uploads/userId/date_uuid.ext 형식
    file_key = f"uploads/{user_id}/{timestamp}_{unique_id}{file_extension}"
    
    return file_key


def generate_presigned_upload_url(bucket, key, content_type, expiration):
    """S3 업로드용 Presigned URL 생성"""
    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket,
                'Key': key,
                'ContentType': content_type,
                # 보안 강화: 업로드된 파일이 공개되지 않도록 설정
                'ServerSideEncryption': 'AES256'
                # ACL은 제거: BucketOwnerEnforced 설정으로 자동 소유권 부여
            },
            ExpiresIn=expiration,
            HttpMethod='PUT'
        )
        return presigned_url
    except Exception as e:
        logger.error("Error generating presigned URL", extra={"error": str(e)})
        raise


def error_response(status_code, message):
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps({
            'error': message
        })
    }
