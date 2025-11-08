# ProfilePhotoAI 🖼️

AI 기반 프로필/증명사진 생성 서비스

![메인화면](/images/ai_profile_photo_main.png)

## 사용기술

- **프론트엔드**: React + S3 Static Hosting + CloudFront
- **백엔드**: AWS Lambda (Python 3.12) + API Gateway (HTTP API v2)
- **인증**: AWS Cognito (Google OAuth)
- **데이터베이스**: DynamoDB
- **스토리지**: S3
- **메시지 큐**: SQS
- **Image Gen AI**: Google Gemini API
- **보안**: AWS Secrets Manager
- **모니터링**: CloudWatch Logs & Metrics
- **IaC**: AWS SAM (Serverless Application Model)

## 아키텍처 상세

![아키텍처](/images/ai_profile_photo_architecture.png)

**주요 플로우:**

### 1. 파일 업로드 (Direct Upload Pattern)
1. 사용자가 프론트엔드에서 파일 업로드 요청 (`POST /upload`)
2. FileTransfer Lambda가 S3 Presigned URL 생성 및 반환
3. 사용자가 **S3에 직접 업로드** (Lambda를 거치지 않음)

### 2. 이미지 생성 요청 (Async Processing)
4. 사용자가 이미지 생성 요청 (`POST /generate`)
5. ApiManager Lambda가 사용자 권한 및 일일 쿼터 확인 (DynamoDB UsageLog)
6. ImageJobs 테이블에 Job 생성 (`status=pending`)
7. SQS Queue에 작업 메시지 발행
8. Job 상태 업데이트 (`status=queued`)
9. **SQS 발행 성공 후에만** 사용량 증가 (DynamoDB UsageLog)

### 3. 백그라운드 AI 처리 (SQS Triggered)
10. SQS 메시지가 ImageProcess Lambda를 트리거
11. Job 상태 업데이트 (`status=processing`)
12. S3 Upload Bucket에서 원본 이미지 다운로드
13. AWS Secrets Manager에서 Gemini API Key 조회
14. Google Gemini API 호출 (AI 이미지 생성)
15. 생성된 이미지를 S3 Result Bucket에 업로드
16. S3 Presigned GET URL 생성 (24시간 유효)
17. Job 상태 업데이트 (`status=completed`, outputImageUrl 저장)
18. 사용자 통계 업데이트 (DynamoDB Users - totalImagesGenerated)

### 4. 결과 조회 (Polling)
19. 사용자가 주기적으로 Job 상태 확인 (`GET /jobs/{jobId}`)
20. ApiManager Lambda가 DynamoDB ImageJobs 조회
21. `status=completed`일 경우 Presigned URL 반환
22. 사용자가 **S3에서 직접 다운로드** (Lambda를 거치지 않음)

### 5. 에러 처리 (DLQ Pattern)
- Gemini API 호출 실패 시 SQS 자동 재시도 (최대 3회)
- 3회 실패 후 Dead Letter Queue로 메시지 이동
- CloudWatch Alarm 트리거 → 운영자 알림


## 모니터링

### CloudWatch Logs

모니터링 방법 추가 작성 필요

### CloudWatch Metrics

- Lambda 실행 횟수, 에러율, 실행 시간
- SQS 큐 깊이, 메시지 처리 시간
- DynamoDB 읽기/쓰기 용량
- API Gateway 요청 수, 레이턴시
