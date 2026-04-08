# ProfilePhotoAI Remediation Plan

이 문서는 현재 프로젝트의 보완 작업을 단계별 체크리스트로 관리하는 기준 문서입니다.

## 운영 규칙

- 상태 기준: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`
- 체크는 이 문서에서 먼저 반영하고, `task.md`는 현재 phase와 핵심 항목만 요약합니다.
- 각 항목은 완료 시 검증 명령 또는 증빙 로그를 남깁니다.

## 현재 목표

- GitHub Actions와 배포 경로를 실서비스 기준으로 안전하게 복구
- 백엔드와 프론트엔드 테스트를 다시 실행 가능한 상태로 복원
- 오래된 운영 가정(SAM, Google OAuth, 가짜 health check)을 제거
- 이후 작업자가 문서를 따라 순차적으로 보완할 수 있도록 기준 문서화

## Phase 1. 운영 안정화

상태: `DONE`

### CI/CD 가드레일

- [x] `R-001` prod 배포를 `workflow_dispatch` 전용으로 제한
  - 완료 기준: `main` push만으로는 prod 워크플로우가 자동 시작되지 않음
  - 검증: `.github/workflows/deploy-prod.yml`
- [x] `R-002` dev/prod workflow에 `concurrency` 추가
  - 완료 기준: 동일 환경 배포가 중첩 실행되지 않음
  - 검증: `.github/workflows/deploy-dev.yml`, `.github/workflows/deploy-prod.yml`
- [x] `R-003` Python/Node/Terraform 버전 고정
  - 완료 기준: 각 workflow job이 명시적으로 버전을 setup함
  - 검증: workflow YAML, `.nvmrc`
- [x] `R-004` Lambda 아티팩트를 빌드 job에서 생성하고 deploy job은 artifact를 소비
  - 완료 기준: deploy job이 `./scripts/build-lambdas.sh`를 직접 호출하지 않음
  - 검증: workflow YAML

### 배포 검증 정상화

- [x] `R-005` 인증 없는 `GET /healthz` 추가
  - 완료 기준: API Gateway route와 Lambda handler가 모두 존재
  - 검증: Terraform route, API handler 테스트
- [x] `R-006` `/health` 404 허용 로직 제거
  - 완료 기준: smoke test가 `200`만 성공으로 인정
  - 검증: deploy workflows
- [x] `R-007` GitHub Environment 기반 `TF_VAR_*` 주입 추가
  - 완료 기준: workflow가 `TF_VAR_domain_name`, `TF_VAR_hosted_zone_name`를 사용
  - 검증: workflow YAML
- [x] `R-008` prod 필수 Terraform 값 누락 시 preflight 실패
  - 완료 기준: 필수 값이 비면 `plan` 전 단계에서 실패
  - 검증: deploy-prod workflow
- [x] `R-009` `destroy-env.sh` 인자 전달 버그 수정
  - 완료 기준: 환경명과 추가 terraform 인자가 정상 분리됨
  - 검증: 스크립트 코드, 실행 예시

## Phase 2. 테스트 복구

상태: `DONE`

### 백엔드 테스트 가능 구조

- [x] `R-010` `backend/common/dynamodb_helper.py`의 import-time env/AWS 초기화 제거
  - 완료 기준: 모듈 import만으로 RuntimeError가 발생하지 않음
  - 검증: Python 단위 테스트
- [x] `R-011` `api_manager`, `file_transfer`, `process`의 import-time boto3 초기화 제거
  - 완료 기준: 테스트에서 env/클라이언트 주입이 가능
  - 검증: Python 단위 테스트

### Python 테스트 스위트

- [x] `R-012` `tests/unit` 및 `tests/integration` 기준으로 pytest 스위트 복구
  - 완료 기준: 최소 핵심 API/업로드/healthz 테스트가 존재
  - 검증: `pytest --collect-only`, `pytest`
- [x] `R-013` “0 tests collected”가 CI 실패가 되도록 workflow 정리
  - 완료 기준: 테스트 존재 여부를 조건문으로 skip하지 않음
  - 검증: workflow YAML
- [x] `R-014` coverage 경로를 단일 설정으로 통일
  - 완료 기준: Python coverage target이 하나로 고정됨
  - 검증: `pytest.ini`, workflow YAML

## Phase 3. 프론트엔드 검증 강화

상태: `DONE`

- [x] `R-015` 빌드 전 필수 `REACT_APP_*` env 검증 스크립트 추가
  - 완료 기준: env 누락 시 `npm run build`가 실패
  - 검증: 로컬 빌드
- [x] `R-016` 최소 프론트 테스트 추가
  - 완료 기준: auth/api 흐름에 대한 Jest 테스트가 존재
  - 검증: `npm test -- --watch=false --runInBand`
- [x] `R-017` workflow에서 프론트 테스트 실행
  - 완료 기준: 단순 build만 아니라 테스트도 수행
  - 검증: workflow YAML

## Phase 4. E2E 및 문서 정리

상태: `DONE`

- [x] `R-018` `tests/api-test/api-test.sh`를 실제 업로드/생성/polling 검증형으로 재작성
  - 완료 기준: presigned upload, `/generate`, `/jobs/{jobId}`, 다운로드 URL 검증 포함
  - 검증: 스크립트 코드
- [x] `R-019` README와 workflow 문서를 현행 구조 기준으로 정리
  - 완료 기준: Terraform/Cognito/Bedrock/healthz 기준으로 문서 일치
  - 검증: `README.md`, `.github/workflows/README.md`
- [x] `R-020` 오래된 문서 체계를 `docs/archive/legacy` 정책으로 정리
  - 완료 기준: 현재 기준 문서는 루트에 남고, 레거시 문서는 archive 정책 하에 분리
  - 검증: `.gitignore`, 문서 구조

## 검증 로그

- [x] `python3 -m compileall backend`
- [x] `python -m pytest --collect-only`
- [x] `python -m pytest --cov=backend --cov-report=term-missing`
- [x] `npm run test:ci`
- [x] `npm run build`
- [x] GitHub Actions `Verify Actions Preflight`의 `terraform-validate`
- [x] GitHub Actions `Verify Actions Preflight`의 `dev-preflight`
- [x] GitHub Actions `Verify Actions Preflight`의 `prod-preflight`

### 검증 메모

- `2026-04-04` `python3 -m compileall backend` 통과
- `2026-04-04` `venv/bin/python -m pytest --collect-only -q tests/unit tests/integration` 통과
- `2026-04-04` `venv/bin/python -m pytest -q tests/unit tests/integration --cov=backend --cov-report=term-missing` 통과
- `2026-04-04` `cd frontend && REACT_APP_* ... npm run test:ci` 통과
- `2026-04-04` `cd frontend && REACT_APP_* ... npm run build` 통과
- `2026-04-04` `cd frontend && npm run build` 실패 확인: 필수 `REACT_APP_*` 누락 시 의도대로 prebuild 차단
- `2026-04-04` `docs/archive/*` 레거시 문서를 `docs/archive/legacy/*` 로 재배치
- `2026-04-04` Terraform validate는 이 샌드박스의 AWS provider plugin schema 로딩 실패로 로컬 검증 불가
- `2026-04-05` 실제 GitHub Actions PR 검증(`PR #2`, run `23981725338`)에서 `Terraform Validate` 성공
- `2026-04-05` 실제 GitHub Actions PR 검증(`PR #2`, run `23981725338`)에서 `Dev Preflight Plan` 실패: `Configure AWS credentials (OIDC)` 단계에서 `Could not load credentials from any providers`
- `2026-04-05` 실제 GitHub Actions PR 검증(`PR #2`, run `23981725338`)에서 `Prod Preflight Plan` 실패: `Configure AWS credentials (OIDC)` 단계에서 `Could not load credentials from any providers`
- `2026-04-05` AWS CLI 확인: 계정 `701111311029` 에 `token.actions.githubusercontent.com` OIDC provider 존재, `ClientIDList=["sts.amazonaws.com"]`
- `2026-04-05` AWS CLI 확인: `profile-photo-ai-dev-role`, `profile-photo-ai-prod-role` trust policy가 각각 `repo:kimdogyeom/profile-photo-ai:environment:dev|prod` 를 허용
- `2026-04-05` AWS CLI 확인: CloudTrail 에 최근 `AssumeRoleWithWebIdentity` 이벤트가 전혀 없음. GitHub Actions 실패는 AWS trust 거부보다 `role-to-assume` 입력 누락/오설정 가능성이 높음
- `2026-04-05` GitHub Environment `dev` / `prod` 에 `AWS_ROLE_TO_ASSUME_*`, `TF_VAR_*` 주입 완료
- `2026-04-05` Terraform bootstrap apply로 원격 state backend(`profile-photo-ai-terraform-state`, `profile-photo-ai-terraform-locks`) 생성 완료
- `2026-04-05` AWS IAM managed policy 보완: GitHub Actions role에 Terraform lock table 접근, `ap-northeast-1` 리전 리소스 접근, CloudFront cache policy 조회 권한 추가
- `2026-04-05` 실제 GitHub Actions PR 검증(`PR #2`, run `23982353354`)에서 `Terraform Validate`, `Dev Preflight Plan`, `Prod Preflight Plan` 모두 성공
- `2026-04-05` 잔여 이슈: GitHub Actions에서 Node.js 20 deprecation warning 발생. 즉시 blocker는 아니지만 action version 정리는 후속 작업으로 필요

## 결정 기록

- prod 배포는 안전성을 위해 자동 push 트리거 대신 수동 dispatch를 기본값으로 사용
- 새 헬스체크는 의존 서비스 전체 진단이 아니라 라우팅/런타임 정상성 확인용 `healthz`로 시작
- remediation의 상세 기준 문서는 `docs/REMEDIATION_PLAN.md`, 요약 현황판은 `task.md`
