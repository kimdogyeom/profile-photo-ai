# ProfilePhotoAI

AWS Bedrock Nova Canvas 기반 프로필 사진 생성 서비스입니다.

## 현재 아키텍처

- 프론트엔드: React
- 인증: Amazon Cognito User Pool 이메일/비밀번호 인증
- API: API Gateway HTTP API + Lambda
- 비동기 처리: SQS + Lambda
- 저장소: S3
- 데이터: DynamoDB
- 이미지 생성: Amazon Bedrock `amazon.nova-canvas-v1:0`
- IaC: Terraform
- 기본 리전: `ap-northeast-1`

## 주요 흐름

1. 사용자가 로그인/회원가입 후 소스 이미지를 업로드합니다.
2. `POST /upload` 가 Cognito 인증된 사용자에게 S3 presigned POST를 발급합니다.
3. 프론트엔드가 이미지를 S3에 직접 업로드합니다.
4. `POST /generate` 가 사용자 소유 파일인지 검증하고 quota를 원자적으로 차감한 뒤 Job을 생성합니다.
5. SQS가 `image-process` Lambda를 트리거하고 Bedrock Nova Canvas로 이미지 variation을 생성합니다.
6. 결과 이미지는 S3에 저장되고, `/jobs/*` API는 presigned download URL을 반환합니다.

## 로컬 작업 순서

### 1. 프론트엔드

```bash
cd frontend
npm ci
npm run build
```

필수 환경 변수:

- `REACT_APP_API_BASE_URL`
- `REACT_APP_AWS_REGION`
- `REACT_APP_COGNITO_USER_POOL_ID`
- `REACT_APP_COGNITO_CLIENT_ID`

`frontend/.env.example` 를 기준으로 `frontend/.env.local` 을 만들면 됩니다.

### 2. Lambda 아티팩트 빌드

```bash
./scripts/build-lambdas.sh
```

빌드 결과는 `dist/lambda/*.zip` 에 생성됩니다.

### 3. Terraform bootstrap

```bash
terraform -chdir=terraform/bootstrap init
terraform -chdir=terraform/bootstrap apply
```

원격 상태용 S3/DynamoDB를 먼저 만듭니다.

### 4. Terraform env 초기화

예시:

```bash
cp terraform/envs/dev/backend.hcl.example terraform/envs/dev/backend.hcl
cp terraform/envs/dev/terraform.tfvars.example terraform/envs/dev/terraform.tfvars
terraform -chdir=terraform/envs/dev init -backend-config=backend.hcl
terraform -chdir=terraform/envs/dev plan
terraform -chdir=terraform/envs/dev apply
```

prod도 동일하게 `terraform/envs/prod` 를 사용합니다.

### 5. 프론트엔드 배포

```bash
./scripts/deploy-frontend.sh dev
```

이 스크립트는 Terraform output에서 API URL, Cognito 설정, S3 버킷, CloudFront 배포 ID를 읽어 프론트엔드를 빌드하고 배포합니다.

## Makefile 명령

```bash
make lambda-build
make tf-fmt
make tf-plan-dev
make tf-apply-dev
make deploy-frontend-dev
```

## 참고

- GitHub Actions 워크플로우는 이번 전환 범위에서 손대지 않았습니다.
- 기존 SAM/LocalStack 기반 경로는 제거되었습니다.
