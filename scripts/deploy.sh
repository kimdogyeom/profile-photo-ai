#!/bin/bash
# SAM 배포 자동화 스크립트
# 사용법: ./scripts/deploy.sh [dev|prod] [options]

set -e

ENVIRONMENT=${1:-dev}
STACK_NAME="profile-photo-ai-${ENVIRONMENT}"
REGION="ap-northeast-2"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 사용법 출력
usage() {
    echo "사용법: $0 [environment] [options]"
    echo ""
    echo "Arguments:"
    echo "  environment  배포 환경 (dev|prod, 기본값: dev)"
    echo ""
    echo "Options:"
    echo "  --guided     대화형 배포 (첫 배포 시 사용)"
    echo "  --skip-test  배포 후 테스트 건너뛰기"
    echo "  --rollback   이전 버전으로 롤백"
    echo ""
    echo "Examples:"
    echo "  $0 dev"
    echo "  $0 prod --guided"
    echo "  $0 dev --rollback"
    exit 1
}

# 환경 검증
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    echo -e "${RED}❌ 에러: 환경은 'dev' 또는 'prod'여야 합니다.${NC}"
    usage
fi

# 옵션 파싱
GUIDED=false
SKIP_TEST=false
ROLLBACK=false

for arg in "$@"; do
    case $arg in
        --guided)
            GUIDED=true
            shift
            ;;
        --skip-test)
            SKIP_TEST=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --help)
            usage
            ;;
    esac
done

echo -e "${BLUE}🚀 ProfilePhotoAI ${ENVIRONMENT} 환경 배포 시작...${NC}"
echo "  - 스택 이름: ${STACK_NAME}"
echo "  - 리전: ${REGION}"
echo ""

# AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ 에러: AWS CLI가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# SAM CLI 설치 확인
if ! command -v sam &> /dev/null; then
    echo -e "${RED}❌ 에러: SAM CLI가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# AWS 자격증명 확인
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ 에러: AWS 자격증명이 설정되어 있지 않습니다.${NC}"
    exit 1
fi

# 롤백 모드
if [ "$ROLLBACK" = true ]; then
    echo -e "${YELLOW}⚠️  롤백 모드: 이전 버전으로 되돌립니다.${NC}"
    read -p "정말 롤백하시겠습니까? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" = "yes" ]; then
        echo "🔄 롤백 중..."
        aws cloudformation cancel-update-stack \
            --stack-name ${STACK_NAME} \
            --region ${REGION} 2>/dev/null || true
        
        aws cloudformation rollback-stack \
            --stack-name ${STACK_NAME} \
            --region ${REGION} 2>/dev/null || echo "롤백 가능한 변경이 없습니다."
        
        echo -e "${GREEN}✅ 롤백 요청이 완료되었습니다.${NC}"
        echo "CloudFormation 콘솔에서 진행 상황을 확인하세요."
    else
        echo "❌ 작업이 취소되었습니다."
        exit 0
    fi
    exit 0
fi

# 1. 배포 전 검증
echo -e "${BLUE}📋 1단계: 배포 전 검증${NC}"
echo "  - template.yaml 검증 중..."

# SAM validate with lint
if ! sam validate --lint; then
    echo -e "${RED}❌ template.yaml 검증 실패${NC}"
    exit 1
fi

echo -e "${GREEN}  ✅ template.yaml 검증 통과${NC}"

# 환경 설정 파일 확인
CONFIG_FILE="config/${ENVIRONMENT}.json"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}  ✅ 환경 설정 파일 확인: ${CONFIG_FILE}${NC}"
else
    echo -e "${YELLOW}  ⚠️  환경 설정 파일이 없습니다: ${CONFIG_FILE}${NC}"
fi

# Secrets Manager 확인 - Gemini API Key
SECRET_NAME="/profile-photo-ai/${ENVIRONMENT}/gemini-api-key"
SECRET_CHECK=$(aws secretsmanager list-secrets \
    --region ${REGION} \
    --filters Key=name,Values=${SECRET_NAME} \
    --query 'SecretList[0].Name' \
    --output text 2>/dev/null || echo "None")

if [ "$SECRET_CHECK" = "None" ] || [ "$SECRET_CHECK" = "" ]; then
    echo -e "${YELLOW}  ⚠️  Secrets Manager에 Gemini API 키가 없습니다: ${SECRET_NAME}${NC}"
    echo "  먼저 ./scripts/setup-secrets.sh를 실행하세요."
    read -p "계속하시겠습니까? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ]; then
        exit 1
    fi
else
    echo -e "${GREEN}  ✅ Gemini API Key 확인: ${SECRET_NAME}${NC}"
fi

# Google OAuth 확인
OAUTH_SECRET_NAME="/profile-photo-ai/${ENVIRONMENT}/google-oauth"
OAUTH_CHECK=$(aws secretsmanager list-secrets \
    --region ${REGION} \
    --filters Key=name,Values=${OAUTH_SECRET_NAME} \
    --query 'SecretList[0].Name' \
    --output text 2>/dev/null || echo "None")

if [ "$OAUTH_CHECK" = "None" ] || [ "$OAUTH_CHECK" = "" ]; then
    echo -e "${YELLOW}  ⚠️  Google OAuth 정보가 없습니다: ${OAUTH_SECRET_NAME}${NC}"
    echo "  ./scripts/setup-google-oauth.sh create ${ENVIRONMENT} 또는"
    echo "  python scripts/manage-google-oauth.py create ${ENVIRONMENT}"
    read -p "계속하시겠습니까? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ]; then
        exit 1
    fi
else
    echo -e "${GREEN}  ✅ Google OAuth 확인: ${OAUTH_SECRET_NAME}${NC}"
fi

echo ""

# 2. 빌드
echo -e "${BLUE}🔨 2단계: 빌드${NC}"
echo "  - SAM 빌드 시작..."

if ! sam build --parallel; then
    echo -e "${RED}❌ 빌드 실패${NC}"
    exit 1
fi

echo -e "${GREEN}  ✅ 빌드 완료${NC}"
echo ""

# 3. 배포
echo -e "${BLUE}🚀 3단계: 배포${NC}"

# Google OAuth 정보 가져오기
if [ "$OAUTH_CHECK" != "None" ] && [ "$OAUTH_CHECK" != "" ]; then
    echo "  - Google OAuth 정보 가져오는 중..."
    GOOGLE_OAUTH=$(aws secretsmanager get-secret-value \
        --secret-id "${OAUTH_SECRET_NAME}" \
        --region ${REGION} \
        --query SecretString \
        --output text 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        GOOGLE_CLIENT_ID=$(echo $GOOGLE_OAUTH | jq -r '.client_id')
        GOOGLE_CLIENT_SECRET=$(echo $GOOGLE_OAUTH | jq -r '.client_secret')
        echo -e "${GREEN}  ✅ OAuth 정보 로드 완료${NC}"
    else
        echo -e "${YELLOW}  ⚠️  OAuth 정보를 가져올 수 없습니다. 기본값 사용${NC}"
        GOOGLE_CLIENT_ID=""
        GOOGLE_CLIENT_SECRET=""
    fi
else
    echo -e "${YELLOW}  ⚠️  OAuth 정보 없음 - 빈 값 사용${NC}"
    GOOGLE_CLIENT_ID=""
    GOOGLE_CLIENT_SECRET=""
fi

if [ "$GUIDED" = true ]; then
    echo "  - 대화형 배포 시작..."
    sam deploy --guided --config-env ${ENVIRONMENT}
else
    echo "  - 자동 배포 시작..."
    
    if [ -f "samconfig.toml" ]; then
        # samconfig.toml의 parameter_overrides를 정확하게 추출 (해당 섹션만)
        BASE_PARAMS=$(grep -A 10 "\[${ENVIRONMENT}.deploy.parameters\]" samconfig.toml | grep "parameter_overrides" | sed 's/parameter_overrides = "\(.*\)"/\1/')
        
        # OAuth 파라미터를 기존 파라미터에 추가
        FULL_PARAMS="${BASE_PARAMS} GoogleOAuthClientId=\"${GOOGLE_CLIENT_ID}\" GoogleOAuthClientSecret=\"${GOOGLE_CLIENT_SECRET}\""
        
        echo "  - 배포 파라미터: ${FULL_PARAMS}"
        
        # OAuth 파라미터 포함하여 배포
        sam deploy \
            --config-env ${ENVIRONMENT} \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset \
            --parameter-overrides "${FULL_PARAMS}"
    else
        echo -e "${YELLOW}  ⚠️  samconfig.toml이 없습니다. 대화형 배포를 실행합니다.${NC}"
        sam deploy --guided --config-env ${ENVIRONMENT}
    fi
fi

echo -e "${GREEN}  ✅ 배포 완료${NC}"
echo ""

# 4. 배포 결과 확인
echo -e "${BLUE}📊 4단계: 배포 결과 확인${NC}"

echo ""
echo "📋 CloudFormation 스택 정보:"
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].{Status:StackStatus, CreatedTime:CreationTime, LastUpdated:LastUpdatedTime}' \
    --output table

echo ""
echo "🔗 API 엔드포인트:"
sam list endpoints \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --output table || echo "엔드포인트 정보를 가져올 수 없습니다."

echo ""
echo "📦 리소스 목록:"
sam list resources \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --output table || echo "리소스 정보를 가져올 수 없습니다."

# CloudFormation 출력 확인
echo ""
echo "📤 CloudFormation Outputs:"
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs' \
    --output table 2>/dev/null || echo "출력 정보가 없습니다."

echo ""

# 5. Google OAuth 리디렉션 URI 업데이트
echo -e "${BLUE}🔄 5단계: Google OAuth 리디렉션 URI 확인${NC}"

# Cognito User Pool Domain 가져오기
COGNITO_DOMAIN=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`UserPoolDomain`].OutputValue' \
    --output text 2>/dev/null)

if [ -n "$COGNITO_DOMAIN" ] && [ "$COGNITO_DOMAIN" != "None" ]; then
    echo "  - Cognito Domain: ${COGNITO_DOMAIN}"
    COGNITO_REDIRECT_URI="${COGNITO_DOMAIN}/oauth2/idpresponse"
    echo "  - Cognito Redirect URI: ${COGNITO_REDIRECT_URI}"
    echo ""
    
    # Google OAuth Client ID 가져오기
    OAUTH_INFO=$(aws secretsmanager get-secret-value \
        --secret-id "/profile-photo-ai/${ENVIRONMENT}/google-oauth" \
        --region ${REGION} \
        --query SecretString --output text 2>/dev/null)
    
    if [ -n "$OAUTH_INFO" ]; then
        CLIENT_ID=$(echo $OAUTH_INFO | jq -r '.client_id' 2>/dev/null)
        
        if [ -n "$CLIENT_ID" ] && [ "$CLIENT_ID" != "null" ]; then
            echo -e "${YELLOW}  ⚠️  Google OAuth 리디렉션 URI를 수동으로 업데이트해야 합니다.${NC}"
            echo ""
            echo "  다음 URI를 Google Cloud Console에 추가하세요:"
            echo "  https://console.cloud.google.com/apis/credentials"
            echo ""
            echo "  필수 리디렉션 URI:"
            echo "    - ${COGNITO_REDIRECT_URI}"
            
            if [ "$ENVIRONMENT" = "dev" ]; then
                echo "    - http://localhost:3000/callback"
                echo "    - http://localhost:3000"
                echo "    - https://dev.aigyeom.com/callback"
                echo "    - https://dev.aigyeom.com"
            else
                echo "    - https://aigyeom.com/callback"
                echo "    - https://aigyeom.com"
            fi
            
            echo ""
            echo "  또는 자동 업데이트 스크립트 실행:"
            echo "    python scripts/manage-google-oauth.py update-uris ${ENVIRONMENT}"
        fi
    else
        echo -e "${YELLOW}  ⚠️  Google OAuth 정보를 찾을 수 없습니다.${NC}"
        echo "  ./scripts/setup-google-oauth.sh create ${ENVIRONMENT}"
    fi
else
    echo -e "${YELLOW}  ⚠️  Cognito Domain을 찾을 수 없습니다.${NC}"
fi

echo ""

# 6. 배포 후 테스트
if [ "$SKIP_TEST" = false ]; then
    echo -e "${BLUE}🧪 6단계: 배포 후 기본 테스트${NC}"
    
    # API Gateway 엔드포인트 추출
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
        --output text 2>/dev/null)
    
    if [ -n "$API_ENDPOINT" ] && [ "$API_ENDPOINT" != "None" ]; then
        echo "  - API 엔드포인트: ${API_ENDPOINT}"
        echo ""
        echo "  - Health Check 테스트..."
        
        # 간단한 health check (OPTIONS 요청)
        if curl -f -X OPTIONS "${API_ENDPOINT}/upload" -H "Content-Type: application/json" &> /dev/null; then
            echo -e "${GREEN}    ✅ API Gateway 접근 가능${NC}"
        else
            echo -e "${YELLOW}    ⚠️  API Gateway 접근 실패 (정상일 수 있음)${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠️  API 엔드포인트를 찾을 수 없습니다.${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  테스트 건너뜀 (--skip-test 옵션)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 배포 완료!${NC}"
echo ""
echo "다음 단계:"
echo "1. CloudWatch Logs에서 Lambda 함수 로그 확인"
echo "2. API Gateway 엔드포인트로 기능 테스트"
echo "3. DynamoDB 테이블에 데이터 확인"
echo "4. CloudWatch Alarms 설정"
echo ""
echo "유용한 명령어:"
echo "  - 로그 확인: sam logs --stack-name ${STACK_NAME} --tail"
echo "  - 리소스 확인: sam list resources --stack-name ${STACK_NAME}"
echo "  - 스택 삭제: ./scripts/cleanup.sh ${ENVIRONMENT}"
