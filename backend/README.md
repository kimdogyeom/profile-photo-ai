# ProfilePhotoAI Backend 코드 구조

## 📁 디렉토리 구조

```
backend/
├── lambda/
│   ├── file_transfer/
│   │   └── file_transfer.py      (221 lines) - Presigned URL 생성
│   ├── api/
│   │   └── api_manager.py        (304 lines) - API 요청 처리 및 SQS 발행
│   └── process/
│       └── process.py            (212 lines) - AI 이미지 생성 처리
└── layers/
    └── dynamodb_helper.py        (248 lines) - DynamoDB 데이터 액세스
```

## 🔄 데이터 플로우

### 1단계: 파일 업로드 준비
```
Client → API Gateway → file_transfer.py
                           ├─ extract_user_id(event)
                           ├─ validate_upload_request()
                           └─ generate_presigned_upload_url()
                                   ↓
Client ← Presigned URL (PUT)
```

### 2단계: 클라이언트가 S3에 직접 업로드
```
Client → S3 (profilephotoai-uploads-raw)
         uploads/{userId}/{timestamp}_{uuid}.{ext}
```

### 3단계: 이미지 생성 요청
```
Client → API Gateway → api_manager.py
                           ├─ extract_user_id(event)
                           ├─ UserService.get_user()
                           ├─ UsageService.can_generate_image() ← dynamodb_helper
                           ├─ verify_s3_file_exists()
                           ├─ ImageJobService.create_job() ← dynamodb_helper
                           ├─ sqs_client.send_message()
                           └─ UsageService.increment_usage() ← dynamodb_helper
                                   ↓
                                  SQS
```

### 4단계: 비동기 이미지 생성
```
SQS → process.py
        ├─ ImageJobService.update_job_status('processing') ← dynamodb_helper
        ├─ s3_client.get_object() (원본 이미지)
        ├─ genai.Client().generate_content() (Gemini AI)
        ├─ s3_client.put_object() (결과 이미지)
        ├─ ImageJobService.update_job_status('completed') ← dynamodb_helper
        ├─ UserService.increment_total_images() ← dynamodb_helper
        └─ api_gateway_client.post_to_connection() (WebSocket 알림)
```

## 🔑 핵심 설계 원칙

### 1. 사용자 인증 일관성
모든 Lambda에서 동일한 방식으로 Cognito 사용자 ID 추출:
```python
user_id = extract_user_id(event)
# requestContext.authorizer.claims.sub
```

### 2. 사용량 관리 정확성
**중요**: SQS 발행 성공 후에만 사용량 차감
```python
# api_manager.py
can_generate, remaining = UsageService.can_generate_image(user_id)
if not can_generate:
    return 429  # Too Many Requests

job_id = ImageJobService.create_job(...)
sqs_response = sqs_client.send_message(...)  # 이 시점에 실패 가능

# SQS 발행 성공 후에만 차감
UsageService.increment_usage(user_id)
```

### 3. Job 상태 관리
```
pending (초기) → queued (SQS 발행) → processing (처리 중) → completed/failed
```

### 4. 에러 처리 계층화
- **file_transfer.py**: 파일 검증 실패 → 400
- **api_manager.py**: 사용량 초과 → 429, 파일 없음 → 404
- **process.py**: AI 생성 실패 → Job status 'failed', WebSocket 알림

### 5. Lambda Layer 활용
`dynamodb_helper.py`를 Lambda Layer로 패키징:
```python
# api_manager.py, process.py
sys.path.append('/opt/python')
from dynamodb_helper import UserService, UsageService, ImageJobService
```

## 📊 DynamoDB 테이블 구조

### Users Table
```
PK: userId (string)
Attributes: email, provider, displayName, profileImage, totalImagesGenerated, 
            createdAt, lastLoginAt
```

### UsageLog Table
```
PK: userIdDate (string) - format: "userId#YYYY-MM-DD"
GSI: UserIdIndex (userId)
Attributes: count, date, lastUpdated, ttl (90일 후 자동 삭제)
```

### ImageJobs Table
```
PK: jobId (string)
GSI: UserIdCreatedAtIndex (userId, createdAt)
GSI: StatusIndex (status)
Attributes: userId, status, style, inputImageUrl, outputImageUrl, prompt, 
            error, processingTime, metadata, createdAt, updatedAt
```

## 🔧 환경 변수 설정

### file_transfer.py
```bash
UPLOAD_BUCKET=profilephotoai-uploads-raw
PRESIGNED_URL_EXPIRATION=3600
```

### api_manager.py
```bash
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/...
UPLOAD_BUCKET=profilephotoai-uploads-raw
ProfilePhotoAI-Users-Table=Users
ProfilePhotoAI-UsageLog-Table=UsageLog
ProfilePhotoAI-ImageJobs-Table=ImageJobs
```

### process.py
```bash
GEMINI_API_KEY=your-gemini-api-key
RESULT_BUCKET=profilephotoai-results-final
MODEL_NAME=gemini-2.0-flash-exp
WEBSOCKET_ENDPOINT=https://xxx.execute-api.us-east-1.amazonaws.com/production
ProfilePhotoAI-Users-Table=Users
ProfilePhotoAI-UsageLog-Table=UsageLog
ProfilePhotoAI-ImageJobs-Table=ImageJobs
```

### dynamodb_helper.py (Lambda Layer)
```bash
DAILY_LIMIT=10
ProfilePhotoAI-Users-Table=Users
ProfilePhotoAI-UsageLog-Table=UsageLog
ProfilePhotoAI-ImageJobs-Table=ImageJobs
```

## 🧪 테스트 시나리오

### 1. 정상 플로우
```bash
# 1. Presigned URL 요청
POST /upload/presigned
Body: {"fileName": "profile.jpg", "contentType": "image/jpeg", "fileSize": 1024000}
Response: {"uploadUrl": "...", "fileKey": "uploads/user123/..."}

# 2. 클라이언트가 S3에 직접 업로드
PUT {uploadUrl}
Body: <binary image data>

# 3. 이미지 생성 요청
POST /generate
Body: {"fileKey": "uploads/user123/...", "style": "professional"}
Response: {"jobId": "job_abc123", "status": "queued", "remainingQuota": 9}

# 4. 결과 확인 (비동기)
# WebSocket 알림 또는 polling API로 확인
```

### 2. 사용량 초과
```bash
POST /generate
Response: 429 {"error": "Daily quota exceeded", "remainingQuota": 0}
```

### 3. 파일 없음
```bash
POST /generate
Body: {"fileKey": "uploads/invalid/file.jpg", ...}
Response: 404 {"error": "Uploaded file not found in S3"}
```

## 🚨 주의사항

### 코드 수정 시
1. **사용자 ID 추출 로직**: 모든 Lambda에서 동일하게 유지
2. **파일 키 형식**: file_transfer.py와 api_manager.py 동기화
3. **Job 상태 추가**: ImageJobService와 process.py 동시 수정
4. **사용량 차감 타이밍**: SQS 발행 성공 후에만 (매우 중요!)

### 보안
- Presigned URL에 ServerSideEncryption 설정
- S3 버킷은 모두 비공개
- Cognito 인증 필수
- CORS 헤더 적절히 설정

### 성능
- DynamoDB 읽기/쓰기 용량 모니터링
- Lambda 동시 실행 제한 설정
- SQS 배치 크기 조정
- Gemini API 호출 시간 추적

## 📈 모니터링

### CloudWatch Metrics
- Lambda 실행 시간 (P50, P95, P99)
- Lambda 에러율
- SQS 메시지 처리 지연
- DynamoDB 사용량

### CloudWatch Logs
- 각 Lambda에서 user_id 로깅
- Job ID 추적
- 에러 스택 트레이스

### 알람 설정
- Lambda 에러율 > 5%
- SQS 메시지 age > 5분
- DynamoDB throttling 발생
- Gemini API 호출 실패율 > 10%
