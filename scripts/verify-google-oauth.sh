#!/bin/bash

# Google OAuth 설정 자동 검증 스크립트
# 이 스크립트는 Google OAuth 설정이 올바른지 확인합니다

set -e

echo "🔍 Google OAuth 설정 검증 시작..."
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Cognito 정보 가져오기
STACK_NAME="profile-photo-ai-dev"
REGION="ap-northeast-2"

echo "📋 1. CloudFormation 스택 확인..."
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" = "NOT_FOUND" ]; then
  echo -e "${RED}✗ 스택을 찾을 수 없습니다. 먼저 배포를 실행하세요:${NC}"
  echo "  ./scripts/deploy.sh dev"
  exit 1
fi

echo -e "${GREEN}✓ 스택 상태: $STACK_STATUS${NC}"
echo ""

# Cognito User Pool ID 가져오기
echo "📋 2. Cognito User Pool 정보 확인..."
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text)

if [ -z "$USER_POOL_ID" ]; then
  echo -e "${RED}✗ Cognito User Pool ID를 찾을 수 없습니다${NC}"
  exit 1
fi

echo -e "${GREEN}✓ User Pool ID: $USER_POOL_ID${NC}"

# Cognito Domain 가져오기
COGNITO_DOMAIN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoHostedUIUrl`].OutputValue' \
  --output text)

if [ -z "$COGNITO_DOMAIN" ]; then
  echo -e "${RED}✗ Cognito Domain을 찾을 수 없습니다${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Cognito Domain: $COGNITO_DOMAIN${NC}"

# 도메인에서 프리픽스 추출
DOMAIN_PREFIX=$(echo $COGNITO_DOMAIN | sed 's/https:\/\/\(.*\)\.auth\..*/\1/')
echo -e "${GREEN}✓ Domain Prefix: $DOMAIN_PREFIX${NC}"
echo ""

# Google Identity Provider 확인
echo "📋 3. Google Identity Provider 확인..."
GOOGLE_IDP=$(aws cognito-idp list-identity-providers \
  --user-pool-id $USER_POOL_ID \
  --region $REGION \
  --query 'Providers[?ProviderName==`Google`]' \
  --output json 2>/dev/null || echo "[]")

if [ "$GOOGLE_IDP" = "[]" ]; then
  echo -e "${YELLOW}⚠ Google Identity Provider가 설정되지 않았습니다${NC}"
  echo "  다음 명령으로 배포하세요:"
  echo "  ./scripts/deploy.sh dev"
else
  echo -e "${GREEN}✓ Google Identity Provider 설정됨${NC}"
fi
echo ""

# 필수 리디렉션 URI 생성
COGNITO_REDIRECT_URI="https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/idpresponse"

echo "📋 4. 필요한 리디렉션 URI..."
echo ""
echo -e "${YELLOW}Google Cloud Console에서 다음 URI를 추가해야 합니다:${NC}"
echo ""
echo "  $COGNITO_REDIRECT_URI"
echo ""
echo "추가 방법:"
echo "  1. https://console.cloud.google.com/ 접속"
echo "  2. 프로젝트 선택"
echo "  3. 'API 및 서비스' > '사용자 인증 정보'"
echo "  4. OAuth 2.0 클라이언트 ID 선택"
echo "  5. '승인된 리디렉션 URI'에 위 URL 추가"
echo ""

# User Pool Client 확인
echo "📋 5. User Pool Client 확인..."
CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolClientId`].OutputValue' \
  --output text)

if [ -z "$CLIENT_ID" ]; then
  echo -e "${RED}✗ User Pool Client ID를 찾을 수 없습니다${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Client ID: $CLIENT_ID${NC}"

# Callback URLs 확인
CALLBACK_URLS=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --region $REGION \
  --query 'UserPoolClient.CallbackURLs' \
  --output json)

echo -e "${GREEN}✓ Callback URLs:${NC}"
echo "$CALLBACK_URLS" | jq -r '.[]' | sed 's/^/  - /'
echo ""

# Identity Providers 확인
SUPPORTED_IDPS=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --region $REGION \
  --query 'UserPoolClient.SupportedIdentityProviders' \
  --output json)

echo "📋 6. 지원되는 Identity Providers..."
if echo "$SUPPORTED_IDPS" | grep -q "Google"; then
  echo -e "${GREEN}✓ Google IdP가 활성화되어 있습니다${NC}"
else
  echo -e "${YELLOW}⚠ Google IdP가 비활성화되어 있습니다${NC}"
  echo "  ./scripts/deploy.sh dev 명령으로 배포하세요"
fi
echo "$SUPPORTED_IDPS" | jq -r '.[]' | sed 's/^/  - /'
echo ""

# 요약
echo "═══════════════════════════════════════════════════════════"
echo "📊 설정 요약"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo -e "${YELLOW}Google Cloud Console에 등록할 리디렉션 URI:${NC}"
echo "  $COGNITO_REDIRECT_URI"
echo ""
echo -e "${YELLOW}프론트엔드 환경 변수 (.env.production):${NC}"
echo "  REACT_APP_COGNITO_DOMAIN=$DOMAIN_PREFIX"
echo "  REACT_APP_CLIENT_ID=$CLIENT_ID"
echo "  REACT_APP_REDIRECT_URI=https://aigyeom.com/callback"
echo ""
echo -e "${GREEN}✅ 검증 완료!${NC}"
echo ""
echo "다음 단계:"
echo "  1. Google Cloud Console에서 리디렉션 URI 추가"
echo "  2. 프론트엔드 환경 변수 확인"
echo "  3. 프론트엔드 빌드 및 배포"
echo "  4. https://aigyeom.com에서 Google 로그인 테스트"
echo ""
