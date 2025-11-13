# GitHub Actions CI/CD 설정 가이드

ProfilePhotoAI의 자동 배포 및 테스트 파이프라인 설정 방법입니다.

## 📋 워크플로우 구조

### 1. `ci-test.yml` - 지속적 통합 (CI)
**트리거**: PR 생성/업데이트, develop 브랜치 푸시

**단계**:
- ✅ Python 코드 린팅 (Black, Flake8)
- ✅ Python 유닛 테스트 (pytest + coverage)
- ✅ Frontend 린팅 (ESLint)
- ✅ Frontend 빌드 테스트
- 🔒 보안 스캔 (Trivy, 시크릿 검사)
- 📦 SAM 템플릿 검증

### 2. `deploy-dev.yml` - 개발 환경 자동 배포
**트리거**: develop 브랜치 푸시, feature/add-onsite-camera-func 푸시

**단계**:
1. 테스트 실행
2. SAM 빌드 및 배포 (dev)
3. Smoke 테스트
4. Frontend 빌드
5. Discord 알림 (선택)

### 3. `deploy-prod.yml` - 프로덕션 배포
**트리거**: main 브랜치 푸시, 수동 트리거 (확인 필요)

**단계**:
1. 배포 확인 (수동 트리거 시)
2. 전체 테스트 실행
3. 백업 생성
4. SAM 배포 (prod)
5. 프로덕션 Smoke 테스트
6. 릴리스 태그 생성
7. 실패 시 롤백 알림

## 🔐 필수 GitHub Secrets 설정

### Repository Settings → Secrets and variables → Actions

#### 개발 환경 (Dev)
```
AWS_ACCESS_KEY_ID          # AWS IAM 사용자 Access Key
AWS_SECRET_ACCESS_KEY      # AWS IAM 사용자 Secret Key
```

#### 프로덕션 환경 (Prod) - 별도 계정 권장
```
AWS_ACCESS_KEY_ID_PROD     # 프로덕션 AWS Access Key
AWS_SECRET_ACCESS_KEY_PROD # 프로덕션 AWS Secret Key
```

#### 선택 사항
```
DISCORD_WEBHOOK_URL        # Discord 알림용 Webhook URL
S3_BUCKET_DEV             # Frontend 호스팅 S3 버킷 (개발)
S3_BUCKET_PROD            # Frontend 호스팅 S3 버킷 (프로덕션)
CLOUDFRONT_ID_DEV         # CloudFront Distribution ID (개발)
CLOUDFRONT_ID_PROD        # CloudFront Distribution ID (프로덕션)
```

## 🚀 사용 방법

### 자동 배포 플로우

#### 1. Feature 개발
```bash
git checkout -b feature/new-feature
# 코드 작성
git commit -m "feat: Add new feature"
git push origin feature/new-feature
```
- PR 생성 시 자동으로 CI 테스트 실행
- 테스트 통과 후 develop에 머지

#### 2. 개발 환경 배포
```bash
git checkout develop
git merge feature/new-feature
git push origin develop
```
- 자동으로 `deploy-dev.yml` 워크플로우 실행
- Dev 환경에 배포

#### 3. 프로덕션 배포
```bash
git checkout main
git merge develop
git push origin main
```
- 자동으로 `deploy-prod.yml` 워크플로우 실행
- 프로덕션 배포 후 릴리스 태그 자동 생성

### 수동 배포 (GitHub UI)

1. GitHub 저장소 → **Actions** 탭
2. 원하는 워크플로우 선택 (Deploy to Dev/Prod)
3. **Run workflow** 버튼 클릭
4. 브랜치 선택 및 옵션 설정
5. **Run workflow** 실행

#### 프로덕션 수동 배포 시 확인
- Confirmation 입력란에 **"DEPLOY"** 입력 필수

## 📊 워크플로우 상태 확인

### 배지 추가 (README.md)
```markdown
![CI Tests](https://github.com/kimdogyeom/profile-photo-ai/actions/workflows/ci-test.yml/badge.svg)
![Deploy Dev](https://github.com/kimdogyeom/profile-photo-ai/actions/workflows/deploy-dev.yml/badge.svg)
![Deploy Prod](https://github.com/kimdogyeom/profile-photo-ai/actions/workflows/deploy-prod.yml/badge.svg)
```

## 🔧 IAM 권한 설정

GitHub Actions에서 사용할 IAM 사용자에 필요한 권한:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "lambda:*",
        "apigateway:*",
        "iam:*",
        "cognito-idp:*",
        "dynamodb:*",
        "sqs:*",
        "logs:*",
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "*"
    }
  ]
}
```

**보안 권장사항**:
- 프로덕션과 개발 환경에 별도 IAM 사용자 사용
- 최소 권한 원칙 적용
- MFA 활성화

## 🧪 로컬 테스트

GitHub Actions 실행 전 로컬 테스트:

```bash
# Python 테스트
cd backend
pytest tests/test_lambda_direct.py -v

# Frontend 빌드 테스트
cd frontend
npm install
npm run build

# SAM 템플릿 검증
sam validate --lint

# SAM 빌드
sam build --parallel
```

## 🔄 워크플로우 커스터마이징

### 테스트 건너뛰기 (긴급 배포 시)
```bash
# GitHub Actions UI에서 수동 실행 시
# "Skip tests" 옵션 체크
```

### Discord 알림 활성화
1. Discord 서버 → 서버 설정 → 연동
2. Webhook 생성 및 URL 복사
3. GitHub Secrets에 `DISCORD_WEBHOOK_URL` 추가

### S3 Frontend 배포 활성화
`deploy-dev.yml` 및 `deploy-prod.yml`에서 주석 해제:
```yaml
# Uncomment when S3 frontend hosting is configured:
run: |
  aws s3 sync frontend/build/ s3://${{ secrets.S3_BUCKET_DEV }}/ --delete
  aws cloudfront create-invalidation --distribution-id ${{ secrets.CLOUDFRONT_ID_DEV }} --paths "/*"
```

## 📝 체크리스트

### 초기 설정
- [ ] GitHub Secrets 추가 (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- [ ] IAM 권한 설정
- [ ] Secrets Manager에 Gemini API 키 저장
- [ ] (선택) Discord Webhook 설정

### 배포 전
- [ ] 로컬 테스트 통과
- [ ] PR 리뷰 완료
- [ ] CI 테스트 통과
- [ ] Breaking changes 확인

### 프로덕션 배포 전
- [ ] Dev 환경에서 충분히 테스트
- [ ] 데이터베이스 마이그레이션 계획
- [ ] 롤백 계획 수립
- [ ] 사용자 공지 (필요 시)

## 🚨 트러블슈팅

### 배포 실패 시
1. GitHub Actions 로그 확인
2. AWS CloudFormation 이벤트 확인
3. Lambda 로그 확인: `sam logs -n FunctionName --tail`

### 권한 오류
```
Error: User is not authorized to perform: cloudformation:CreateStack
```
→ IAM 권한 재확인

### 테스트 실패
```
pytest: command not found
```
→ `requirements.txt`에 pytest 추가

## 📚 참고 자료

- [GitHub Actions 문서](https://docs.github.com/actions)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- [GitHub Secrets 관리](https://docs.github.com/actions/security-guides/encrypted-secrets)
