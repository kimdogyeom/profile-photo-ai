#!/bin/bash

# ProfilePhotoAI Git Secrets 설정 스크립트
# AWS 키, Cognito ID, API 키 등 민감 정보 커밋 방지

set -e

echo "🔒 Git Secrets 설정 시작..."

# git-secrets가 설치되어 있는지 확인
if ! command -v git secrets &> /dev/null; then
    echo "❌ git-secrets가 설치되어 있지 않습니다."
    echo "설치 방법:"
    echo "  git clone https://github.com/awslabs/git-secrets.git"
    echo "  cd git-secrets"
    echo "  sudo make install"
    exit 1
fi

# 현재 레포에 git-secrets hook 설치
echo "📦 Git hooks 설치 중..."
git secrets --install -f

# AWS 기본 패턴 등록
echo "🔍 AWS 패턴 등록 중..."
git secrets --register-aws

# 프로젝트별 커스텀 패턴 추가
echo "🎯 커스텀 패턴 등록 중..."

# Cognito User Pool ID 패턴
git secrets --add 'ap-northeast-1_[a-zA-Z0-9]{9}'

# Cognito Client ID 패턴 (26자 소문자+숫자)
git secrets --add '[a-z0-9]{26}'

# API Gateway ID 패턴
git secrets --add '[a-z0-9]{10}\.execute-api\.ap-northeast-1\.amazonaws\.com'

# 환경 변수 값 패턴 (따옴표 안의 실제 값)
git secrets --add '(REACT_APP_|AWS_|BEDROCK_)[A-Z_]+=["\x27][^"\x27]+["\x27]'

# 허용 패턴 추가 (false positive 방지)
echo "✅ 허용 패턴 등록 중..."

# AWS 예제 키 (공식 문서)
git secrets --add --allowed 'AKIAIOSFODNN7EXAMPLE'
git secrets --add --allowed 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'

# 테스트용 더미 Account ID (명백한 테스트 값)
git secrets --add --allowed '000000000000'

# 예제 플레이스홀더
git secrets --add --allowed 'xxxxxxxxxxxxxxxxxxxxxxxxxx'
git secrets --add --allowed 'your-api-id'
git secrets --add --allowed 'ap-northeast-1_xxxxxxxxx'

# 환경 변수 파일 샘플은 허용
git secrets --add --allowed '\.env\.example'

echo ""
echo "✅ Git Secrets 설정 완료!"
echo ""
echo "📋 다음 단계:"
echo "  1. 기존 히스토리 스캔: git secrets --scan-history"
echo "  2. 현재 작업 디렉토리 스캔: git secrets --scan"
echo "  3. 커밋 시도: git commit (자동으로 스캔됨)"
echo ""
echo "⚠️  참고: 이제부터 커밋 시 자동으로 민감 정보를 검사합니다."

# 선택: 현재 작업 디렉토리 스캔
read -p "지금 현재 파일들을 스캔하시겠습니까? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔍 현재 파일 스캔 중..."
    git secrets --scan -r .
fi
