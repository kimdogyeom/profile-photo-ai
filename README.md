# ProfilePhotoAI 🖼️

AI 기반 프로필/증명사진 생성 서비스

서비스 사진 추가 필요

## 아키텍처

- **프론트엔드**: React + S3 Static Hosting + CloudFront
- **백엔드**: AWS Lambda (Python) + API Gateway
- **인증**: AWS Cognito (Google OAuth)
- **데이터베이스**: DynamoDB
- **스토리지**: S3
- **메시지 큐**: SQS
- **AI**: Google Gemini API
- **모니터링**: CloudWatch Logs & Metrics
- **IaC**: AWS SAM (Serverless Application Model)

## 프로젝트 구조

```
profile-photo-ai/
├── template.yaml            # AWS SAM 템플릿 (인프라 정의)
├── samconfig.toml          # SAM 설정 파일
├── backend/                # Lambda 함수 및 백엔드 로직
│   ├── lambda/
│   │   ├── file_transfer/  # 파일 업로드 URL 생성
│   │   ├── api/            # 이미지 생성 요청 처리
│   │   └── process/        # AI 이미지 처리
│   └── layers/             # Lambda Layer (공통 라이브러리)
│       └── dynamodb_helper.py
├── frontend/               # React 애플리케이션
├── tests/
│   └── events/             # Lambda 테스트 이벤트
├── scripts/
│   └── local-setup.sh      # 로컬 환경 설정 스크립트
└── docs/                   # 문서
```

## 시작하기

### 사전 요구사항

- **Python 3.11+**
- **Node.js 18+**
- **AWS CLI**
- **AWS SAM CLI** 
- **Docker** (로컬 테스트용)
- **Gemini API Key**

## API 엔드포인트

### POST /upload
파일 업로드를 위한 Presigned URL 생성

**요청:**
```json
{
  "fileName": "profile.jpg",
  "fileSize": 2048000,
  "contentType": "image/jpeg"
}
```

**응답:**
```json
{
  "uploadUrl": "https://s3.amazonaws.com/...",
  "fileKey": "uploads/user123/20240101_abc123.jpg",
  "expiresIn": 3600
}
```

### POST /generate
이미지 생성 요청

**요청:**
```json
{
  "fileKey": "uploads/user123/20240101_abc123.jpg",
  "prompt": "Create a professional business profile photo with a clean background"
}
```

**응답:**
```json
{
  "jobId": "job_abc123def456",
  "status": "queued",
  "remainingQuota": 9
}
```

### 배포 확인

```bash
# 스택 정보 확인
aws cloudformation describe-stacks --stack-name profilephotoai-dev

# API 엔드포인트 확인
sam list endpoints --stack-name profilephotoai-dev

# 리소스 목록
sam list resources --stack-name profilephotoai-dev
```


## 모니터링

### CloudWatch Logs

모니터링 방법 추가 작성 필요

### CloudWatch Metrics

- Lambda 실행 횟수, 에러율, 실행 시간
- SQS 큐 깊이, 메시지 처리 시간
- DynamoDB 읽기/쓰기 용량
- API Gateway 요청 수, 레이턴시

## 아키텍처 상세

Todo 
아키텍처 사진 추가 필요

**주요 플로우:**
1. 사용자가 프론트엔드에서 파일 업로드 요청
2. 백엔드에서 S3 Presigned URL 생성 및 반환
3. 사용자가 파일을 S3에 업로드
4. 사용자가 이미지 생성 요청
5. 백엔드에서 SQS에 작업 큐잉
6. Image Process Lambda가 SQS 메시지 처리
7. Gemini API 호출 및 이미지 생성
8. 생성된 이미지 S3에 저장 및 DynamoDB에 메타데이터 기록

## 개발 가이드

### 코드 위치
- **File Transfer Lambda**: `backend/lambda/file_transfer/file_transfer.py`
- **API Manager Lambda**: `backend/lambda/api/api_manager.py`
- **Image Process Lambda**: `backend/lambda/process/process.py`
- **DynamoDB Helper**: `backend/layers/dynamodb_helper.py` (Lambda Layer)

### 환경 변수

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `GEMINI_API_KEY` | Google Gemini API 키 | ✓ |
| `UPLOAD_BUCKET` | 업로드 S3 버킷명 | ✓ |
| `RESULT_BUCKET` | 결과 S3 버킷명 | ✓ |
| `SQS_QUEUE_URL` | SQS 큐 URL | ✓ |
| `DAILY_LIMIT` | 일일 생성 한도 | - (기본: 10) |
