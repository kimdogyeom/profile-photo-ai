# GitHub Actions (Terraform, Cognito, Bedrock)

이 프로젝트는 이제 GitHub Actions에서 `Terraform` 기반 배포를 사용합니다.  
SAM, CloudFormation 출력, Google OAuth 관련 단계는 모두 제거되었습니다.

## 워크플로우 구성

### `ci-test.yml`
- 트리거: `pull_request(main, develop)`, `push(develop)`
- 수행:
  - Backend lint (`compileall`, `black`, `flake8`)
  - Backend 테스트(테스트 디렉터리가 존재할 때만 실행)
  - Frontend 빌드
  - Trivy 보안 스캔 + secret regex 체크
  - Terraform validate (`terraform/bootstrap`, `terraform/envs/dev`, `terraform/envs/prod`)

### `deploy-dev.yml`
- 트리거: `push(develop)`, `workflow_dispatch`
- 수행:
  - 테스트(옵션 스킵 가능)
  - `./scripts/build-lambdas.sh`
  - `./scripts/tf.sh init dev` + `./scripts/tf.sh validate dev` + `./scripts/tf.sh plan dev -out=tfplan`
  - `./scripts/tf.sh apply dev -auto-approve tfplan`
  - API `/health` 헬스체크
  - `./scripts/deploy-frontend.sh dev`로 프론트 배포

### `deploy-prod.yml`
- 트리거: `push(main, tag)`, `workflow_dispatch`
- 수행:
  - prod 배포 전 `DEPLOY` 확인 입력 검증
  - 테스트 실행
  - 동일한 Terraform 배포 파이프라인(`prod`)
  - 프론트엔드 배포
  - Discord 알림

## 필수 GitHub Secrets

- `AWS_ROLE_TO_ASSUME_DEV`
- `AWS_ROLE_TO_ASSUME_PROD`
- `TF_STATE_BUCKET` (선택: 지정하지 않으면 `profile-photo-ai-terraform-state` 사용)
- `TF_STATE_KEY` (선택: 기본값 `profile-photo-ai/{env}/terraform.tfstate`)
- `TF_STATE_REGION` (선택: 기본값 `ap-northeast-1`)
- `TF_STATE_DYNAMODB_TABLE` (선택: 기본값 `profile-photo-ai-terraform-locks`)
- `DISCORD_WEBHOOK_URL` (옵션)

## 로컬 검증

```bash
./scripts/build-lambdas.sh
terraform -chdir=terraform/bootstrap init -backend=false
terraform -chdir=terraform/bootstrap validate
terraform -chdir=terraform/envs/dev init -backend=false
terraform -chdir=terraform/envs/dev validate
terraform -chdir=terraform/envs/prod init -backend=false
terraform -chdir=terraform/envs/prod validate
```

```bash
./scripts/tf.sh init dev
./scripts/tf.sh validate dev
./scripts/tf.sh plan dev -out=tfplan
./scripts/tf.sh apply dev -auto-approve tfplan
./scripts/deploy-frontend.sh dev
```

## 트러블슈팅 메모

- Terraform 출력은 아래 값이 배포/프론트엔드에서 사용됩니다.
  - `api_base_url`
  - `cognito_user_pool_id`
  - `cognito_user_pool_client_id`
  - `frontend_bucket_name`
  - `frontend_distribution_id`
- `frontend/.env.production`/`.env.prod`는 워크플로에서 생성하지 않으며, `deploy-frontend.sh`가 Terraform output을 기준으로 빌드 환경변수를 주입합니다.
- 배포 실패 시 `deploy-backend` 또는 `deploy-frontend` 로그의 Terraform 출력 확인이 가장 빠른 추적 지점입니다.
