# GitHub Actions (Terraform, Cognito, Bedrock)

이 프로젝트는 이제 GitHub Actions에서 `Terraform` 기반 배포를 사용합니다.

## 워크플로우 구성

### `ci-test.yml`
- 트리거: `pull_request(main, develop)`, `push(develop)`
- 수행:
  - Backend lint (`compileall`, `flake8`)
  - Backend 테스트 (`tests/unit`, `tests/integration`)
  - Frontend 테스트 + 빌드
  - Trivy 보안 스캔 + secret regex 체크
  - Terraform validate (`terraform/bootstrap`, `terraform/envs/dev`, `terraform/envs/prod`)
  - `concurrency` 로 이전 CI 실행 취소

### `deploy-dev.yml`
- 트리거: `push(develop)`, `workflow_dispatch`
- 수행:
  - 테스트(옵션 스킵 가능)
  - Lambda 아티팩트 빌드 후 artifact 업로드
  - `./scripts/tf.sh init dev` + `./scripts/tf.sh validate dev` + `./scripts/tf.sh plan dev -out=tfplan`
  - `tfplan`(바이너리) 및 `tfplan.txt`(텍스트 뷰) 생성 후 아티팩트 업로드
    - 업로드명: `tfplan-dev-${{ github.sha }}-${{ github.run_id }}`
    - 보존 기간: `3`일
  - `./scripts/tf.sh apply dev -auto-approve tfplan`
  - API `/healthz` 헬스체크
  - `./scripts/deploy-frontend.sh dev`로 프론트 배포
  - `concurrency: deploy-dev` 로 중첩 배포 방지

### `deploy-prod.yml`
- 트리거: `workflow_dispatch`
- 수행:
  - prod 배포 전 `DEPLOY` 확인 입력 검증
  - 테스트 실행
  - Lambda 아티팩트 빌드 후 artifact 업로드
- 동일한 Terraform 배포 파이프라인(`prod`)
  - `tfplan`(바이너리) 및 `tfplan.txt`(텍스트 뷰) 생성 후 아티팩트 업로드
    - 업로드명: `tfplan-prod-${{ github.sha }}-${{ github.run_id }}`
    - 보존 기간: `14`일
  - API `/healthz` 헬스체크
  - 프론트엔드 배포
  - Discord 알림
  - `concurrency: deploy-prod` 로 prod 중첩 배포 방지

## 필수 GitHub Secrets / Variables

- `AWS_ROLE_TO_ASSUME_DEV`
- `AWS_ROLE_TO_ASSUME_PROD`
- `DISCORD_WEBHOOK_URL` (옵션)
- `TF_VAR_DOMAIN_NAME` (GitHub Environment variable)
- `TF_VAR_HOSTED_ZONE_ID` (GitHub Environment variable)
- `TF_VAR_CERTIFICATE_ARN` (GitHub Environment variable)
- `TF_STATE_BUCKET` (선택: 지정하지 않으면 `profile-photo-ai-terraform-state` 사용)
- `TF_STATE_KEY` (선택: 기본값 `profile-photo-ai/{env}/terraform.tfstate`)
- `TF_STATE_REGION` (선택: 기본값 `ap-northeast-1`)
- `TF_STATE_DYNAMODB_TABLE` (선택: 기본값 `profile-photo-ai-terraform-locks`)

## 로컬 검증

```bash
./scripts/build-lambdas.sh
venv/bin/flake8 backend/common backend/lambda/api backend/lambda/file_transfer backend/lambda/process tests --max-line-length=120 --extend-ignore=E203,E266,E501
python -m pytest --collect-only -q tests/unit tests/integration
python -m pytest -v tests/unit tests/integration --cov=backend --cov-report=term-missing
cd frontend && npm run test:ci && npm run build
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
- Frontend build는 필수 `REACT_APP_*` 값이 없으면 `prebuild` 단계에서 실패합니다.
- 배포 실패 시 `deploy-backend` 또는 `deploy-frontend` 로그의 Terraform 출력 확인이 가장 빠른 추적 지점입니다.
- `tests/api-test/api-test.sh` 는 `tests/api-test/.env` 기준으로 실제 Cognito 로그인, S3 presigned upload, `/generate`, `/jobs/{jobId}`, download URL까지 검증합니다.
