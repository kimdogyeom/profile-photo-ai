#!/bin/bash
# AWS Secrets Manager에 Gemini API 키 저장
# 사용법: ./scripts/setup-secrets.sh <api-key> <environment>

set -e

ENVIRONMENT=${2:-dev}
SECRET_NAME="/profile-photo-ai/${ENVIRONMENT}/gemini-api-key"
REGION="ap-northeast-2"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 사용법 출력
usage() {
    echo "사용법: $0 <api-key> [environment]"
    echo ""
    echo "Arguments:"
    echo "  api-key      Gemini API 키 (필수)"
    echo "  environment  배포 환경 (dev|prod, 기본값: dev)"
    echo ""
    echo "Examples:"
    echo "  $0 'your-gemini-api-key' dev"
    echo "  $0 'your-gemini-api-key' prod"
    exit 1
}

# API 키 검증
if [ -z "$1" ]; then
    echo -e "${RED}❌ 에러: API 키가 제공되지 않았습니다.${NC}"
    usage
fi

API_KEY="$1"

# 환경 검증
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    echo -e "${RED}❌ 에러: 환경은 'dev' 또는 'prod'여야 합니다.${NC}"
    usage
fi

echo -e "${GREEN}🔐 Secrets Manager 설정 시작...${NC}"
echo "  - 시크릿 이름: ${SECRET_NAME}"
echo "  - 리전: ${REGION}"
echo "  - 환경: ${ENVIRONMENT}"
echo ""

# AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ 에러: AWS CLI가 설치되어 있지 않습니다.${NC}"
    echo "AWS CLI 설치: https://aws.amazon.com/cli/"
    exit 1
fi

# AWS 자격증명 확인
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ 에러: AWS 자격증명이 설정되어 있지 않습니다.${NC}"
    echo "AWS 설정: aws configure"
    exit 1
fi

# 시크릿 존재 여부 확인
SECRET_EXISTS=$(aws secretsmanager list-secrets \
    --region ${REGION} \
    --filters Key=name,Values=${SECRET_NAME} \
    --query 'SecretList[0].Name' \
    --output text 2>/dev/null || echo "None")

if [ "$SECRET_EXISTS" != "None" ] && [ "$SECRET_EXISTS" != "" ]; then
    echo -e "${YELLOW}⚠️  시크릿이 이미 존재합니다.${NC}"
    read -p "기존 시크릿을 업데이트하시겠습니까? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" = "yes" ]; then
        echo "🔄 시크릿 업데이트 중..."
        aws secretsmanager update-secret \
            --secret-id "${SECRET_NAME}" \
            --secret-string "${API_KEY}" \
            --region ${REGION}
        
        echo -e "${GREEN}✅ 시크릿이 성공적으로 업데이트되었습니다!${NC}"
    else
        echo "❌ 작업이 취소되었습니다."
        exit 0
    fi
else
    echo "📝 새 시크릿 생성 중..."
    aws secretsmanager create-secret \
        --name "${SECRET_NAME}" \
        --description "Gemini API Key for ProfilePhotoAI ${ENVIRONMENT}" \
        --secret-string "${API_KEY}" \
        --region ${REGION} \
        --tags Key=Environment,Value=${ENVIRONMENT} Key=Project,Value=ProfilePhotoAI
    
    echo -e "${GREEN}✅ 시크릿이 성공적으로 생성되었습니다!${NC}"
fi

echo ""
echo "📋 시크릿 정보:"
aws secretsmanager describe-secret \
    --secret-id "${SECRET_NAME}" \
    --region ${REGION} \
    --query '{Name:Name, ARN:ARN, CreatedDate:CreatedDate, LastAccessedDate:LastAccessedDate}' \
    --output table

echo ""
echo -e "${GREEN}🎉 완료!${NC}"
echo ""
echo "다음 단계:"
echo "1. template.yaml에서 Lambda 함수가 이 시크릿을 읽을 수 있는 IAM 권한 확인"
echo "2. Lambda 코드에서 시크릿 읽기 로직 구현"
echo "3. 배포 후 Lambda 함수에서 시크릿 접근 테스트"
