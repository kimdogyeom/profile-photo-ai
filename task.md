# ProfilePhotoAI Active Tasks

이 파일은 현재 진행 상태만 요약합니다. 상세 체크리스트와 완료 기준은 [`docs/REMEDIATION_PLAN.md`](/home/gyeom/profile-photo-ai/docs/REMEDIATION_PLAN.md)를 기준으로 관리합니다.

## 현재 상태

- 현재 Phase: `Remote Verification Done`
- 기준 문서: `docs/REMEDIATION_PLAN.md`
- 원격 검증 상태: GitHub Actions `Verify Actions Preflight`에서 Terraform validate, dev preflight, prod preflight 모두 성공

## 완료된 보완 범위

- GitHub Actions 가드레일 복구
  - prod 수동 배포 전환
  - dev/prod concurrency 추가
  - Python/Node/Terraform 버전 고정
  - Lambda 아티팩트 빌드/배포 분리
- 배포 검증 정상화
  - `GET /healthz` 추가
  - `/health` 404 허용 제거
  - GitHub Environment `TF_VAR_*` 주입
- IaC 재현성 강화
  - GitHub Actions OIDC/IAM deploy role bootstrap Terraform 코드화
  - CloudFront용 ACM 인증서와 Route53 validation/alias Terraform 코드화
  - bootstrap backend 생성 스크립트 및 artifact 검증 강화
- 테스트 복구
  - import-time AWS 초기화 제거
  - `tests/unit`, `tests/integration` pytest 스위트 추가
  - 프론트 env 검증 및 Jest 테스트 추가
  - `tests/api-test/api-test.sh` 재작성

## 남은 TODO

- [x] 실제 GitHub Actions 환경에서 Terraform validate 재검증
- [x] GitHub Environment `AWS_ROLE_TO_ASSUME_DEV` / `AWS_ROLE_TO_ASSUME_PROD` 및 IAM OIDC trust 보완
- [x] 실제 GitHub Actions 환경에서 dev/prod deploy preflight 재검증
- [ ] GitHub Actions Node.js 20 deprecation warning 대응(action version 정리 또는 Node 24 호환성 확인)

## 운영 원칙

- 상세 작업 상태 변경은 `docs/REMEDIATION_PLAN.md`의 체크박스를 우선 업데이트
- `task.md`는 현재 phase와 핵심 TODO만 유지
- 새 blocker가 생기면 `task.md`에도 한 줄로 반영
- 현재 잔여 리스크: `Verify Actions Preflight`는 성공했지만 GitHub Actions의 Node.js 20 deprecation warning은 남아 있음
