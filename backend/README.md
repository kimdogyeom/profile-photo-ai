# Backend Overview

백엔드는 다섯 개의 Lambda 아티팩트로 구성됩니다.

- `file-transfer`: Cognito 인증 사용자에게 S3 presigned POST 발급
- `api-manager`: 사용자 정보, quota, job 생성/조회 관리
- `image-process`: SQS 소비 후 Bedrock Nova Canvas 호출
- `stats-aggregator`: CloudWatch Logs 기반 일일 집계
- `webhook-notifier`: CloudWatch Alarm SNS 알림을 Discord Webhook으로 전달

## 공용 코드

공용 DynamoDB 로직은 `backend/common/dynamodb_helper.py` 에 있습니다. 예전 Lambda Layer는 제거했고, 빌드 스크립트가 각 함수 패키지에 공용 모듈을 함께 포함합니다.

## 이미지 생성 설정

`image-process` Lambda 기본값:

- 모델: `amazon.nova-canvas-v1:0`
- task type: `IMAGE_VARIATION`
- 해상도: `1024x1024`
- quality: `standard`
- cfg scale: `6.5`
- similarity strength: `0.8`

환경 변수로 조정할 수 있습니다.

## 중요 변경점

- 기존 외부 이미지 모델 의존성 제거, Bedrock Nova Canvas로 통합
- 프론트엔드 인증은 Cognito Hosted UI + Authorization Code + PKCE 기준으로 정리
- quota 차감은 DynamoDB 조건식 기반 원자 업데이트로 변경
- `fileKey` 는 반드시 현재 사용자 prefix(`uploads/{userId}/`) 와 일치해야 함
- 결과 다운로드 URL은 API 조회 시점에 presigned URL로 생성됨
