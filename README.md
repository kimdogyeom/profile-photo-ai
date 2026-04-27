# ProfilePhotoAI

사용자가 원본 사진을 업로드하면 AWS Bedrock Nova Canvas로 AI 프로필/증명사진 스타일 이미지를 생성하는 서버리스 웹 서비스입니다.
이 프로젝트의 핵심은 이미지 생성 기능 자체보다, 사용량이 일정하지 않은 서비스를 저비용·저운영관리로 배포하기 위해 AWS 서버리스 구성요소를 조합하고, 인증·업로드·비동기 처리·결과 제공·IaC 배포까지 하나의 운영 흐름으로 설계한 점입니다.

![메인화면](images/ai_profile_photo_main.png)

## 프로젝트 소개

ProfilePhotoAI는 인증된 사용자가 이미지를 업로드하고, 원하는 프로필/증명사진 스타일을 선택한 뒤, 생성 작업 상태를 조회하고 결과 이미지를 다운로드할 수 있는 AI 이미지 생성 서비스입니다.

이 프로젝트는 상시 서버를 운영하는 구조 대신 AWS managed service와 서버리스 컴퓨팅을 조합했습니다. 이용이 뜸한 시간에는 고정 서버 비용을 줄이고, 생성 요청이 몰리는 순간에는 API 요청과 이미지 생성 작업을 분리해 SQS 큐와 Lambda worker가 작업을 흡수하도록 설계했습니다.

- 프론트엔드: React, CloudFront, S3 static hosting
- 인증/인가: Amazon Cognito Hosted UI, API Gateway JWT Authorizer
- API/처리: API Gateway, Lambda, SQS
- 저장소: S3, DynamoDB
- 이미지 생성: Amazon Bedrock `amazon.nova-canvas-v1:0`
- 인프라 관리: Terraform, GitHub OIDC 기반 배포 권한

## 문제 정의: 이용량이 일정하지 않은 AI 이미지 생성 서비스 운영

AI 이미지 생성 서비스는 단순 CRUD API보다 운영상 고려할 부분이 많습니다. 특히 개인 프로젝트나 소규모 서비스처럼 사용량이 일정하지 않은 환경에서는, 계속 떠 있는 서버를 운영하는 것보다 요청이 있을 때만 비용이 발생하고 관리 부담이 적은 구조가 더 적합합니다.

이 프로젝트에서 해결하려고 한 운영 문제는 다음과 같습니다.

- **상시 서버 비용 부담**: 이용이 없을 때도 서버가 계속 실행되는 구조를 피해야 했습니다.
- **장시간 이미지 생성 요청**: Bedrock 이미지 생성은 응답 시간이 길 수 있어 API 요청 안에서 동기 처리하기 어렵습니다.
- **트래픽 burst 대응**: 특정 시점에 생성 요청이 몰려도 API와 worker가 함께 병목이 되지 않아야 했습니다.
- **사용자 파일 보안**: 업로드 파일이 다른 사용자에게 참조되거나 결과 저장소 경로가 직접 노출되지 않아야 했습니다.
- **모델 호출 비용 제어**: 사용자별 quota와 실패 시 복구 로직이 없으면 비용과 사용량 데이터가 쉽게 틀어질 수 있습니다.
- **실패 재시도와 격리**: 이미지 생성 실패가 조용히 성공 처리되면 재시도나 DLQ 기반 후속 대응이 불가능합니다.
- **배포 재현성**: dev/prod 인프라와 GitHub Actions 배포 경로를 코드로 재현할 수 있어야 했습니다.

## 아키텍처

![아키텍처](images/ai_profile_photo_architecture.png)

전체 구조는 API 요청 경로와 이미지 생성 처리 경로를 분리하는 방식입니다. API Lambda는 인증, 업로드 URL 발급, job 생성, 상태 조회처럼 짧게 끝나는 작업을 맡고, 시간이 오래 걸리는 이미지 생성은 SQS 뒤의 worker Lambda가 처리합니다.

### 처리 흐름

1. 사용자는 Cognito Hosted UI를 통해 로그인합니다.
2. 프론트엔드는 API Gateway에 업로드 URL을 요청합니다.
3. file-transfer Lambda는 사용자별 prefix가 포함된 S3 presigned POST를 발급합니다.
4. 브라우저는 원본 이미지를 애플리케이션 서버를 거치지 않고 S3 `uploads/` 경로에 직접 업로드합니다.
5. 사용자가 생성 요청을 보내면 API Lambda가 `fileKey` 소유권과 S3 객체 존재 여부를 검증합니다.
6. API Lambda는 DynamoDB에 job 상태를 저장하고 사용자 quota를 조건부로 차감합니다.
7. 생성 작업 메시지를 SQS에 enqueue합니다.
8. process Lambda가 SQS 메시지를 소비해 Bedrock Nova Canvas를 호출합니다.
9. 생성 결과는 S3에 저장되고 DynamoDB job 상태가 완료로 갱신됩니다.
10. 사용자는 job 상태를 polling하고, 완료 후 presigned download URL로 결과 이미지를 다운로드합니다.

## AWS 서비스 선택 이유

| 운영 문제 | 선택한 구성 | 운영상 의미 |
| --- | --- | --- |
| 이용이 뜸한 시간의 고정 비용 | API Gateway + Lambda | 상시 서버 없이 요청 단위로 API를 처리해 유휴 시간 비용을 줄입니다. |
| 장시간 이미지 생성 요청 | SQS + worker Lambda | API 응답 경로와 생성 처리 경로를 분리해 사용자는 빠르게 job을 받고, 실제 생성은 비동기로 처리합니다. |
| 요청 급증 시 처리 부담 | SQS queue buffering | 생성 요청을 큐에 적재해 worker가 순차/병렬로 소비할 수 있게 하고, API가 곧바로 생성 처리 병목을 떠안지 않도록 했습니다. |
| 사용자 인증과 API 보호 | Cognito Hosted UI + JWT Authorizer | 자체 인증 서버를 두지 않고 managed auth를 사용해 회원가입, 로그인, JWT 검증 부담을 줄였습니다. |
| 대용량 이미지 업로드 | S3 presigned POST | 파일이 Lambda/API 서버를 통과하지 않게 해 네트워크 부하와 서버 구현 부담을 줄였습니다. |
| 결과 이미지 전달 | S3 + presigned download URL | 결과 저장소를 공개하지 않고 다운로드 시점에만 제한된 URL을 발급합니다. |
| job 상태와 quota 관리 | DynamoDB | 서버리스 저장소로 job 상태, 생성 이력, 사용자별 일일 quota를 관리합니다. |
| 실패 재시도와 격리 | SQS partial batch response + DLQ | 실패한 메시지만 재시도 대상으로 남기고, 반복 실패 메시지는 DLQ로 격리할 수 있게 했습니다. |
| 환경 재현성과 배포 권한 | Terraform + GitHub OIDC | dev/prod 인프라와 배포 권한을 코드로 관리하고 장기 AWS access key 의존을 줄였습니다. |
| 정적 프론트엔드 제공 | S3 + CloudFront | 별도 웹 서버 없이 정적 리소스를 배포하고 CDN을 통해 전달합니다. |

## 운영 및 보안 설계 포인트

### 1. 저비용·저운영관리 서버리스 구성

상시 서버가 필요한 구조 대신 API Gateway, Lambda, SQS, S3, DynamoDB를 조합했습니다. 이용량이 적은 시간에는 고정 컴퓨팅 비용을 줄이고, 트래픽이 발생할 때만 필요한 구성요소가 동작하도록 설계했습니다.

이 선택은 소규모 서비스에서 중요한 운영 부담도 줄입니다. 서버 패치, 프로세스 관리, 오토스케일링 그룹 운영보다 managed service 경계를 조합하는 방식에 집중했습니다.

### 2. 비동기 처리와 트래픽 완충

이미지 생성은 모델 호출 시간이 길고 실패 가능성도 있기 때문에 API Gateway 요청 안에서 직접 처리하지 않았습니다. API는 job 생성과 SQS enqueue까지만 담당하고, process Lambda가 큐를 소비하면서 Bedrock을 호출합니다.

이 구조에서는 생성 요청이 몰려도 API는 작업을 큐에 넣고 빠르게 응답할 수 있습니다. worker 처리량은 Lambda/SQS 쪽에서 조절되며, 큐가 트래픽 burst를 완충하는 역할을 합니다.

### 3. 실패 복구와 DLQ

SQS를 사용하더라도 Lambda가 실패 메시지를 성공 처리하면 재시도와 DLQ가 동작하지 않습니다. 이를 막기 위해 worker Lambda는 실패한 record의 `messageId`를 `batchItemFailures`로 반환하고, Terraform event source mapping에는 `ReportBatchItemFailures`를 설정했습니다.

운영상 의미는 단순합니다. 성공한 메시지는 중복 처리하지 않고, 실패한 메시지만 재시도 대상으로 남기며, 반복 실패 메시지는 DLQ에서 따로 확인할 수 있습니다.

### 4. 업로드 보안과 파일 소유권 검증

이미지는 S3 presigned POST로 직접 업로드합니다. 이 방식은 Lambda가 이미지 파일을 중계하지 않아도 되므로 비용과 부하를 줄일 수 있지만, presigned URL만 발급한다고 보안이 끝나는 것은 아닙니다.

그래서 생성 요청 단계에서 현재 로그인한 사용자의 `fileKey` prefix를 다시 확인하고, 실제 S3 객체가 존재하는지도 검증합니다. 사용자가 다른 사용자의 업로드 경로를 임의로 참조하는 상황을 막기 위한 경계입니다.

### 5. 결과 저장소 비공개와 응답 노출 최소화

생성 결과는 S3에 저장하지만 버킷을 공개하지 않습니다. 다운로드가 필요한 시점에 API가 presigned URL을 발급하고, 클라이언트 응답에는 불필요한 bucket 정보를 노출하지 않도록 줄였습니다.

CORS도 환경별 허용 origin을 설정할 수 있게 해, 모든 origin을 전제로 한 응답보다 배포 환경에 맞게 접근 경계를 좁힐 수 있도록 했습니다.

### 6. quota 일관성과 비용 제어

Bedrock 모델 호출은 비용이 발생하므로 사용자별 일일 quota를 둡니다. 생성 요청 시 DynamoDB 조건식 기반으로 quota를 차감하고, SQS enqueue가 실패하면 quota를 다시 복구합니다.

이 구조는 “요청은 실패했는데 quota만 차감되는” 상태를 줄이기 위한 것입니다. 작은 서비스라도 비용이 연결된 API에서는 사용량 데이터의 일관성이 중요하다고 보았습니다.

### 7. IaC 기반 dev/prod 재현성

Terraform으로 bootstrap, dev, prod 인프라를 관리합니다. GitHub Actions는 OIDC 기반으로 AWS 권한을 받아 배포하도록 구성해 장기 access key를 저장하지 않는 방향으로 정리했습니다.

프론트엔드 배포도 S3/CloudFront 기준으로 구성되어 있으며, Lambda zip 빌드와 Terraform 배포 경로를 스크립트와 Makefile로 묶어 재현 가능한 운영 절차를 만들었습니다.

## 핵심 기능

- Cognito Hosted UI 기반 회원가입/로그인과 인증된 사용자 전용 API 접근 제어
- 브라우저에서 S3로 직접 업로드하는 presigned POST 기반 파일 업로드
- JPG, PNG, WEBP 업로드 지원과 데스크톱 웹캠 촬영 지원
- 취업/증명사진 용도에 맞춘 10개 스타일 프리셋과 커스텀 프롬프트 입력
- 생성 요청 후 작업 상태 polling, 생성 이력 조회, 결과 이미지 다운로드 제공
- 사용자별 일일 생성 횟수 관리와 quota 초과 시 요청 차단

## API 및 데이터 흐름 요약

주요 API 경로는 인증된 사용자 흐름을 기준으로 구성됩니다.

- `POST /upload`: S3 presigned POST 발급
- `POST /generate`: 업로드 파일 검증, quota 차감, job 생성, SQS enqueue
- `GET /jobs/{jobId}`: 생성 job 상태 조회
- `GET /jobs/{jobId}/download`: 결과 이미지 presigned download URL 발급
- `GET /user/me`: 현재 사용자 정보 조회
- `GET /user/jobs`: 사용자 생성 이력 조회
- `GET /healthz`: 배포 검증용 health check

저장소는 역할별로 나뉩니다.

- S3 `uploads/`: 원본 이미지 업로드 경로
- S3 result bucket `generated/`: 생성 결과 이미지 저장 경로
- DynamoDB jobs: job 상태, 입력/출력 메타데이터, 생성 이력
- DynamoDB usage/quota: 사용자별 일일 생성량 관리
- SQS: 이미지 생성 작업 큐와 DLQ

## 로컬 개발 및 검증

### 빠른 온보딩

- `make bootstrap-apply`로 Terraform bootstrap 스택을 먼저 적용할 수 있습니다. 이 단계는 AWS state backend, GitHub OIDC/IAM role, GitHub Environment variable까지 함께 관리하므로 `GITHUB_TOKEN`이 필요합니다.
- `make tf-bootstrap-dev` 또는 `make tf-bootstrap-prod`는 bootstrap output 기준으로 각 환경의 `backend.hcl`을 생성하고 backend를 초기화합니다.
- `./scripts/tf.sh init <dev|prod>`는 `backend.hcl`이 없으면 각 환경의 `backend.hcl.example`을 자동으로 사용합니다.
- `./scripts/build-lambdas.sh`는 `dist/lambda/*.zip`을 다시 만들고, `./scripts/deploy-frontend.sh <env>`는 `frontend/build/index.html`이 생성된 뒤에만 S3/CloudFront에 반영합니다.

### 검증 명령

```bash
make test
make lint
make tf-validate-dev
make tf-validate-prod
```

검증 범위는 다음을 포함합니다.

- Python Lambda unit/integration test
- React service test
- Python compile check / flake8
- Terraform fmt check / validate

현재 로컬 기준 주요 테스트 수:

- Backend: 14 tests
- Frontend: 7 tests

## 개선 이력 / 트러블슈팅

### SQS 메시지 실패가 DLQ로 가지 않던 구조 개선

초기 구조에서는 worker Lambda가 record별 예외를 내부에서 처리한 뒤 전체 Lambda 호출을 성공으로 종료할 수 있었습니다. 이 경우 SQS는 메시지를 성공 처리하므로 재시도와 DLQ 적재가 발생하지 않습니다.

이를 해결하기 위해 실패한 messageId를 `batchItemFailures`에 포함해 반환하고, Lambda event source mapping에 `ReportBatchItemFailures`를 활성화했습니다. 결과적으로 성공한 메시지와 실패한 메시지를 분리해 처리할 수 있게 되었습니다.

### API 응답 노출 범위 축소와 CORS 경계 정리

업로드 URL 응답에는 클라이언트가 사용할 필요 없는 bucket 정보가 포함되어 있었습니다. 클라이언트에는 업로드에 필요한 URL, fields, fileKey만 반환하도록 줄이고, 결과 다운로드도 API가 presigned URL을 발급하는 방식으로 유지했습니다.

또한 CORS origin을 환경변수 기반 allowlist로 관리해 dev/prod 배포 환경에 맞게 접근 경계를 조정할 수 있도록 했습니다.

### 루트 검증 진입점 정리

백엔드 테스트, 프론트엔드 테스트, Python 정적 점검, Terraform 포맷/검증을 매번 개별 명령으로 실행하면 작업자마다 검증 범위가 달라질 수 있습니다. 이를 줄이기 위해 root `Makefile`에 `test`, `lint`, `tf-validate-dev`, `tf-validate-prod` 진입점을 정리했습니다.

## 남은 개선 과제

- CloudWatch alarm, dashboard, DLQ replay 절차를 더 명확히 문서화
- 실제 브라우저 기반 E2E 테스트 추가
- 배포 후 smoke test 자동화 범위 확대
- 비용 추정과 사용량 기준별 운영 한계 문서화
