# ProfilePhotoAI 작업 목록

## 📋 작업 관리 가이드

이 문서는 프로젝트의 진행 중인 작업, 예정된 작업, 완료된 작업을 추적하는 중앙 관리 파일입니다.

**작업 상태:**
- `⏳ TODO`: 예정된 작업
- `🚧 IN_PROGRESS`: 진행 중인 작업
- `✅ DONE`: 완료된 작업
- `🔴 BLOCKED`: 블로킹된 작업 (의존성 또는 이슈로 인해 대기)
- `❌ CANCELLED`: 취소된 작업

---

## 🚧 진행 중 (IN_PROGRESS)

*현재 진행 중인 작업이 없습니다.*

---

## ⏳ 예정 작업 (TODO)

### [P0] [Infrastructure] GitHub Actions CI/CD 파이프라인 구축
- **설명**: Dev/Prod 환경 자동 배포 파이프라인 구성 (OIDC 기반)
- **작업 내용**:
  - [x] Discord Webhook 설정 가이드 작성 (`docs/setup/DISCORD_WEBHOOK_SETUP.md`)
  - [x] IAM OIDC Policy 생성 스크립트 작성 (`scripts/setup-github-oidc.py`)
  - [x] Dev 배포 워크플로우 작성 (`.github/workflows/deploy-dev.yml`)
  - [x] Prod 배포 워크플로우 작성 (`.github/workflows/deploy-prod.yml`)
  - [x] 리소스 네이밍 일관성 수정 (`profilephotoai` → `profile-photo-ai`)
  - [x] AWS OIDC Provider 생성 (token.actions.githubusercontent.com)
  - [x] IAM Role 생성: profile-photo-ai-dev-role, profile-photo-ai-prod-role
  - [x] GitHub Secrets 설정 (AWS_ACCOUNT_ID, DISCORD_WEBHOOK_URL, OAuth Credentials)
  - [x] AWS Secrets Manager에 Gemini API Key 저장
  - [ ] Develop 브랜치 생성 및 첫 배포 테스트
  - [ ] Main 브랜치 Prod 배포 테스트
- **우선순위**: P0 (Critical)
- **예상 소요 시간**: 5시간 (4시간 완료, 1시간 남음)
- **관련 파일**:
  - `.github/workflows/deploy-dev.yml`
  - `.github/workflows/deploy-prod.yml`
  - `scripts/setup-github-oidc.py`
  - `docs/setup/DISCORD_WEBHOOK_SETUP.md`
- **브랜치 전략**: GitHub Flow (develop → main만 사용)
- **다음 단계**: AWS Console에서 OIDC Provider/IAM Role 생성 → GitHub Secrets 설정

---

### [P1] [Frontend] 스타일 선택 UI 개선 - 이모지 → 샘플 이미지로 변경
- **설명**: StyleSelector 컴포넌트에서 이모지 아이콘을 실제 생성 결과 샘플 이미지로 교체
- **작업 내용**:
  - [ ] 각 스타일별 샘플 이미지 제작/수집 (Professional, Friendly, Outdoor, Formal, Academic)
  - [ ] 이미지 최적화 (WebP 포맷, 적절한 해상도)
  - [ ] StyleSelector.jsx 수정: 이모지 → `<img>` 태그로 변경
  - [ ] 호버 시 확대 효과 추가 (미리보기 강화)
  - [ ] 로딩 상태 처리 (lazy loading)
  - [ ] 반응형 이미지 사이즈 조정
  - [ ] 접근성: alt 텍스트 추가
- **우선순위**: High
- **예상 소요 시간**: 3시간
- **관련 파일**: 
  - `frontend/src/components/StyleSelector.jsx`
  - `frontend/src/components/StyleSelector.css`
  - `frontend/public/images/samples/` (새로 생성)
- **참고**: 사용자가 스타일 선택 시 실제 결과를 미리 볼 수 있어 UX 크게 향상됨

#### 2. 프론트엔드 카메라 촬영 기능 추가
- **설명**: 파일 첨부 외에 웹캠/모바일 카메라 직접 촬영 옵션 추가
- **작업 내용**:
  - [ ] HTML5 MediaStream API 통합
  - [ ] 카메라 시작/중지 컨트롤
  - [ ] 사진 캡처 with Canvas
  - [ ] 전면/후면 카메라 전환 (모바일)
  - [ ] 미리보기 및 재촬영 기능
  - [ ] CameraCapture.jsx 컴포넌트 생성
- **우선순위**: Medium
- **의존성**: 없음

#### 2. 프론트엔드 모바일 최적화
- **설명**: 반응형 디자인 완성도 향상
- **작업 내용**:
  - [ ] 768px 이하 브레이크포인트 테스트
  - [ ] 터치 인터랙션 개선
  - [ ] 이력 목록 스크롤 최적화
  - [ ] 로딩 애니메이션 성능 검증
- **우선순위**: Medium
- **의존성**: 없음

#### 3. API 엔드포인트 페이지네이션 개선
      animation: fadeInSharpen 0.5s ease-out;
    }
    @keyframes fadeInSharpen {
      from { filter: blur(8px); opacity: 0.7; }
      to { filter: blur(0); opacity: 1; }
    }
    ```
- **UI/UX 아이디어 (모바일)**:
  - 🎨 **추천 방식 1: 플로팅 + 풀스크린 이력**
    - 메인 화면: 전체를 생성 이력으로 사용 (카드 그리드)
    - 우측 하단: 플로팅 버튼 "+" (항상 고정)
    - 버튼 클릭 시: 바텀시트 또는 전체 화면 모달로 생성 메뉴 표시
    - 장점: 이력 확인이 주요 작업, 생성은 필요 시에만
  - 🎨 **추천 방식 2: 상단 고정 + 하단 스크롤**
    - 상단 고정: 간소화된 생성 메뉴 (이미지 + 스타일 + 생성)
    - 하단 무한 스크롤: 생성 이력
    - 장점: 한 화면에서 모든 기능 접근 가능
  - 🎨 **추천 방식 3: 탭 네비게이션**
    - 하단 탭: "생성하기" / "내 이력"
    - 각 탭은 전체 화면 사용
    - 장점: 명확한 구분, 직관적
- **API 엔드포인트 (이미 구현됨)**:
  - `GET /user/jobs` - 사용자의 Job 이력 조회 (페이징 지원)
  - Response: `{ jobs: [{jobId, style, status, createdAt, outputImageUrl}], nextToken }`

#### 2. CloudWatch 모니터링 설정
- **설명**: 프로덕션 환경을 위한 CloudWatch Alarms 및 Dashboard 구성
- **작업 내용**:
  - [ ] Lambda Errors, Throttles, Duration(p95) 알람 설정
  - [ ] SQS Queue Depth, Old Message Age 알람 설정
  - [ ] DLQ Messages > 0 알람 설정 (Critical)
  - [ ] DynamoDB Throttles 알람 설정
  - [ ] API Gateway 5xx Error Rate 알람 설정
  - [ ] CloudWatch Dashboard 생성 (주요 지표 한눈에 보기)
- **우선순위**: High
- **예상 소요 시간**: 4시간
- **관련 문서**: `docs/CICD와_IaC_관리_전략.md` (모니터링 섹션)
- **비고**: template.yaml에 CloudWatch Alarm 리소스 추가 필요

---

### 우선순위 중간 (Medium Priority)


#### 2. README 업데이트
- **설명**: 주요 플로우 및 아키텍처 설명 개선
- **작업 내용**:
  - [ ] 모니터링 섹션 확장 (CloudWatch Metrics, Alarms)
  - [ ] 보안 섹션 추가
- **우선순위**: medium
- **예상 소요 시간**: 1시간
- **관련 문서**: `README.md`
- **비고**: 아키텍처 다이어그램 이미지 업데이트 필요


#### 3. GitHub Actions CI/CD 파이프라인 구축
- **설명**: 자동 배포 파이프라인 구성 (OIDC 기반)
- **작업 내용**:
  - [ ] AWS OIDC Provider 설정
  - [ ] IAM Role 생성 (GitHub Actions용, 최소 권한 원칙)
  - [ ] `.github/workflows/deploy-backend.yml` 작성
  - [ ] `.github/workflows/deploy-frontend.yml` 작성
  - [ ] Path-based 트리거 설정 (backend/**, frontend/**)
  - [ ] 테스트 자동화 통합 (pytest, npm test)
  - [ ] CloudFormation Outputs 자동 추출 → frontend .env 생성
- **우선순위**: Medium
- **예상 소요 시간**: 2시간
- **관련 문서**: `docs/CICD와_IaC_관리_전략.md`
- **비고**: OIDC 방식 권장 (IAM User Access Key 사용 금지)

#### 4. 테스트 코드 작성
- **설명**: Backend Lambda 함수 단위 테스트 및 통합 테스트
- **작업 내용**:
  - [ ] FileTransfer Lambda 단위 테스트 (`tests/test_file_transfer.py`)
  - [ ] ApiManager Lambda 단위 테스트 (`tests/test_api_manager.py`)
  - [ ] ImageProcess Lambda 단위 테스트 (`tests/test_image_process.py`)
  - [ ] DynamoDB Helper 유틸 테스트 (`tests/test_dynamodb_helper.py`)
  - [ ] 통합 테스트 (SAM Local + LocalStack)
  - [ ] 테스트 커버리지 80% 이상 목표
- **우선순위**: Medium
- **예상 소요 시간**: 8시간
- **관련 문서**: `backend/tests/`
- **비고**: pytest, moto(AWS 서비스 모킹) 사용

#### 5. Frontend 배포 자동화
- **설명**: Frontend 빌드 및 S3/CloudFront 배포 자동화
- **작업 내용**:
  - [ ] CloudFormation Outputs 자동 추출 스크립트
  - [ ] `.env.production` 자동 생성 (API_URL, USER_POOL_ID 등)
  - [ ] `npm run build` 자동화
  - [ ] S3 동기화 (`aws s3 sync build/ s3://...`)
  - [ ] CloudFront 캐시 무효화 (`aws cloudfront create-invalidation`)
  - [ ] GitHub Actions workflow 통합
- **우선순위**: Medium
- **예상 소요 시간**: 4시간
- **관련 문서**: `scripts/deploy-frontend.sh`
- **비고**: 기존 스크립트 개선 및 자동화

---

### 우선순위 낮음 (Low Priority)

#### 6. Terraform 학습 및 마이그레이션 (선택)
- **설명**: CloudFormation을 Terraform으로 변환 (학습 목적)
- **작업 내용**:
  - [ ] Terraform 기본 문법 학습
  - [ ] 동일한 인프라를 Terraform 코드로 작성
  - [ ] State 관리 (S3 + DynamoDB)
  - [ ] 모듈 구조화
  - [ ] 비교 문서 작성 (`docs/IaC_비교분석.md`)
- **우선순위**: Low
- **예상 소요 시간**: 20시간
- **관련 문서**: `docs/CICD와_IaC_관리_전략.md` (CloudFormation vs Terraform)
- **비고**: 실제 배포는 CloudFormation 유지, 학습 목적

#### 7. 멀티 환경 지원 (dev, staging, prod)
- **설명**: 환경별 독립적인 Stack 배포
- **작업 내용**:
  - [ ] `config/staging.json`, `config/prod.json` 생성
  - [ ] samconfig.toml 환경별 설정 추가
  - [ ] Foundation Stack 분리 (Route53, ACM)
  - [ ] Security Stack 분리 (Cognito, Secrets Manager)
  - [ ] Application Stack (Lambda, API Gateway, DynamoDB)
  - [ ] CloudFormation Exports/Imports 설정
  - [ ] 환경별 배포 스크립트 작성
- **우선순위**: Low
- **예상 소요 시간**: 12시간
- **관련 문서**: `docs/CICD와_IaC_관리_전략.md` (레벨 2: 멀티 환경)
- **비고**: 프로덕션 출시 시 필요

#### 8. X-Ray 분산 추적 설정
- **설명**: Lambda 함수 간 트레이싱 및 병목 지점 분석
- **작업 내용**:
  - [ ] template.yaml에 X-Ray Tracing 활성화
  - [ ] Lambda 함수 코드에 X-Ray SDK 추가
  - [ ] API Gateway X-Ray 활성화
  - [ ] DynamoDB, S3 호출 추적
  - [ ] X-Ray Service Map 확인
- **우선순위**: Low
- **예상 소요 시간**: 2시간
- **관련 문서**: AWS X-Ray 공식 문서
- **비고**: 성능 최적화 시 유용

#### 9. Cost Explorer 대시보드 설정
- **설명**: AWS 비용 모니터링 및 예산 알람
- **작업 내용**:
  - [ ] AWS Budgets 설정 (월 예산 $50, 알람 80%/100%)
  - [ ] Cost Explorer 태그 기반 분석 (Environment=dev)
  - [ ] 서비스별 비용 분석 (Lambda, S3, DynamoDB, Gemini API)
  - [ ] 예산 초과 알람 → Slack/Email 통합
- **우선순위**: Low
- **예상 소요 시간**: 2시간
- **관련 문서**: `docs/CICD와_IaC_관리_전략.md` (모니터링 섹션)
- **비고**: 프로덕션 출시 전 필수

---

## ✅ 완료된 작업 (DONE)

### 2025-11-07
- ✅ **프로젝트 초기 설정**: AWS SAM 프로젝트 구조 생성
- ✅ **Lambda 함수 구현**: FileTransfer, ApiManager, ImageProcess 3개 Lambda 작성
- ✅ **DynamoDB Helper Layer**: 공통 DynamoDB 유틸리티 Lambda Layer 작성
- ✅ **S3 Direct Upload Pattern**: Presigned URL 기반 파일 업로드 구현
- ✅ **SQS Async Processing**: 비동기 이미지 처리 파이프라인 구현
- ✅ **Usage Quota Pattern**: SQS 발행 성공 후 사용량 증가 로직 구현
- ✅ **Cognito OAuth 설정**: Google/Kakao 소셜 로그인 연동
- ✅ **API Gateway JWT Authorizer**: Cognito JWT 기반 인증 설정
- ✅ **Gemini API 연동**: Google Gemini API로 AI 이미지 생성 구현
- ✅ **로컬 테스트 환경**: SAM Local + LocalStack 설정

### 2025-11-08
- ✅ **CI/CD 가이드 문서 작성**: `docs/CICD와_IaC_관리_전략.md` 작성
- ✅ **아키텍처 플로우 정리**: Draw.io 스크립트 및 레이어 구조 정의
- ✅ **모니터링 계획 수립**: CloudWatch 모니터링 항목 및 알람 기준 정의
- ✅ **CloudFormation vs Terraform 비교 분석**: 커리어 관점에서 도구 선택 가이드 작성

### 2025-11-10
- ✅ **통합 로깅 및 모니터링 시스템 구축 완료** (12시간 소요)
  - ✅ Phase 1: 로깅 인프라 설계 (logging_helper.py, 단위 테스트, 문서화)
  - ✅ Phase 2: Lambda 함수별 로깅 구현 (총 43개 로그 이벤트 추가)
  - ✅ Phase 3: CloudWatch Metric Filters & Alarms (8개 Metric Filters, 9개 Alarms)
  - ✅ Phase 4: 통계 및 성능 메트릭 (StatsAggregator Lambda, 매시간 실행)
  - ✅ Phase 5: Webhook 알림 시스템 (Discord Embed, CloudWatch 링크 자동 생성)
  - ✅ Phase 6: 로그 아카이빙 (S3 Archive, Kinesis Firehose, Subscription Filters)
- ✅ **프론트엔드 UI/UX 개선 완료** (4시간 소요)
  - ✅ 레이아웃 재설계: 좌측(생성 이력) + 우측(생성 메뉴)
  - ✅ 사진 TIP 사이드바 제거
  - ✅ JobCard 컴포넌트: blur 효과 + 로딩 스피너 + fade-in 애니메이션
  - ✅ JobHistoryList 컴포넌트: 3초 간격 폴링, pending/completed 자동 병합
  - ✅ GeneratePage 수정: 이미지 상태 유지 (setSelectedFile(null) 제거)
  - ✅ API 서비스: getUserJobs() 추가
  - ✅ 반응형 디자인: 1200px/768px/480px 브레이크포인트
  - ✅ 빌드 성공: 110.24KB gzip (경고 없음)

<<<<<<< HEAD
=======
### 2025-11-13
- ✅ **GitHub Actions CI/CD 워크플로우 작성 완료** (3시간 소요)
  - ✅ Discord Webhook 설정 가이드 문서 작성 (`docs/setup/DISCORD_WEBHOOK_SETUP.md`)
  - ✅ IAM OIDC Policy 생성 스크립트 작성 (`scripts/setup-github-oidc.py`)
  - ✅ Dev 배포 워크플로우 작성 (`.github/workflows/deploy-dev.yml`)
    - develop 브랜치 push 시 자동 배포
    - 테스트 → 배포 → S3 프론트엔드 배포 → CloudFront 캐시 무효화 → Discord 알림
  - ✅ Prod 배포 워크플로우 작성 (`.github/workflows/deploy-prod.yml`)
    - main 브랜치 push 시 자동 배포
    - 테스트 → 백업 → 배포 → S3 프론트엔드 배포 → CloudFront 캐시 무효화 → 릴리즈 태그 → Discord 알림
  - ✅ 불필요한 Google OAuth 자동화 스크립트 제거 (수동 설정 권장)
  - ✅ 브랜치 전략 결정: GitHub Flow (develop → main만 사용, feature 브랜치 제외)
  - ✅ 최소 권한 원칙 적용: 리소스 ARN을 `profile-photo-ai-*` 패턴으로 제한
  - ✅ Route53, CloudFront, ACM 권한 포함 (커스텀 도메인 지원)
  - ✅ 프론트엔드 자동 배포: S3 sync + CloudFront invalidation 추가
  - ✅ **리소스 네이밍 일관성 수정 완료** (1시간 소요)
    - ✅ 프로젝트 전체 `profilephotoai` → `profile-photo-ai` 수정
    - ✅ S3 버킷명: `profile-photo-ai-frontend-dev/prod`
    - ✅ CloudFormation 스택명: `profile-photo-ai-dev/prod`
    - ✅ IAM Role명: `profile-photo-ai-dev-role/prod-role`
    - ✅ DynamoDB 테이블명: `Profile-Photo-AI-Users-dev` 등
    - ✅ SQS 큐명: `Profile-Photo-AI-ImageProcess-dev` 등
    - ✅ Lambda 로그 그룹명: `/aws/lambda/Profile-Photo-AI-*`
    - ✅ LocalStack 스크립트, 테스트 파일, Makefile, docker-compose 모두 수정

### 2025-11-12
- ✅ **프론트엔드 카메라 촬영 기능 추가 완료** (3시간 소요)
  - ✅ 디바이스 타입 감지 (768px 기준으로 PC/모바일 구분)
  - ✅ PC에서만 웹캠 버튼 표시
  - ✅ MediaStream API로 웹캠 스트림 시작/종료
  - ✅ Canvas로 사진 캡처 및 File 객체 변환 (JPEG 95% 품질)
  - ✅ 웹캠 UI 컴포넌트 (비디오 + 촬영/취소 버튼)
  - ✅ CSS 스타일 추가 (웹캠 컨테이너, 버튼, 거울 모드)
  - ✅ 비디오 재생 로직 개선 (loadedmetadata 이벤트 대기)
  - ✅ 로컬 테스트 완료 (PC 크롬: 웹캠 촬영 → 이미지 업로드 → 생성 → 다운로드)
  - ✅ 모바일: 네이티브 카메라 동작 확인
  - ✅ 빌드 성공: 110.66KB gzip (+551B)

>>>>>>> 29bb018 (추가: task관리, GitHub Actions CI/CD 파이프라인 구축 및 관련 작업 완료)
---

## 🔴 블로킹된 작업 (BLOCKED)

### 없음
현재 블로킹된 작업이 없습니다.

---

## ❌ 취소된 작업 (CANCELLED)

### 없음
현재 취소된 작업이 없습니다.

---

## 📝 작업 추가 템플릿

새로운 작업을 추가할 때 아래 템플릿을 사용하세요:

```markdown
#### [작업 번호]. [작업 제목]
- **설명**: [작업에 대한 간단한 설명]
- **작업 내용**:
  - [ ] [세부 작업 1]
  - [ ] [세부 작업 2]
  - [ ] [세부 작업 3]
- **우선순위**: [High/Medium/Low]
- **예상 소요 시간**: [시간]
- **관련 문서**: [파일 경로 또는 링크]
- **비고**: [추가 메모]
```

---

## 📌 참고사항

### 작업 진행 시 체크리스트
- [ ] 작업 시작 시 상태를 `🚧 IN_PROGRESS`로 변경
- [ ] 관련 브랜치 생성 (예: `feature/cloudwatch-monitoring`)
- [ ] 커밋 메시지에 작업 번호 포함 (예: `[Task-1] Add CloudWatch Alarms`)
- [ ] 작업 완료 시 PR 생성 및 리뷰 요청
- [ ] PR 머지 후 상태를 `✅ DONE`으로 변경
- [ ] 완료 날짜 기록

### Git 브랜치 전략
- `main`: 프로덕션 배포 브랜치
- `develop`: 개발 통합 브랜치 (선택)
- `feature/[task-name]`: 기능 개발 브랜치
- `hotfix/[issue-name]`: 긴급 수정 브랜치

### 커밋 메시지 컨벤션
```
[Task-번호] 작업 요약

- 세부 변경 사항 1
- 세부 변경 사항 2

관련 이슈: #123
```

---

---

**마지막 업데이트**: 2025-11-13
  
