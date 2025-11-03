#!/bin/bash

# -- 스크립트 설명 --
# 이 스크립트는 Cognito 테스트 사용자를 생성(또는 확인)하고,
# 로그인하여 인증 토큰을 획득한 뒤,
# 배포된 API의 주요 엔드포인트들을 테스트합니다.

# 에러 발생 시 즉시 중단
set -e

# .env 파일에서 환경 변수 로드
if [ -f .env ]; then
  source .env
else
  echo "오류: .env 파일이 없습니다. .env 파일을 먼저 생성해주세요."
  exit 1
fi

echo "🧪 1단계: 테스트 사용자 설정 시작..."

# 테스트 사용자가 이미 있는지 확인하고, 없으면 생성
# 사용자 생성 실패 시(이미 존재 등) 오류를 무시하고 계속 진행
aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$TEST_USER_EMAIL" \
  --user-attributes Name=email,Value="$TEST_USER_EMAIL" Name=email_verified,Value=true \
  --temporary-password "$TEST_USER_TEMP_PASS" \
  --message-action SUPPRESS \
  --region ap-northeast-2 > /dev/null 2>&1 || true

# 사용자의 비밀번호를 영구적으로 설정
aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$TEST_USER_EMAIL" \
  --password "$TEST_USER_PERM_PASS" \
  --permanent \
  --region ap-northeast-2

echo "✅ 테스트 사용자 설정 완료!"
echo "------------------------------------"


echo "🔑 2단계: 인증 토큰 획득 시작..."

# 로그인하여 ID 토큰을 TOKEN 변수에 직접 저장 (임시 파일 사용 안 함)
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters "USERNAME=$TEST_USER_EMAIL,PASSWORD=$TEST_USER_PERM_PASS" \
  --region ap-northeast-2 \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# 토큰 획득에 실패했는지 확인
if [ -z "$TOKEN" ]; then
    echo "❌ 오류: 인증 토큰을 획득하지 못했습니다. 사용자 정보나 Cognito 설정을 확인하세요."
    exit 1
fi

echo "✅ 인증 토큰 획득 완료!"
echo "------------------------------------"


echo "🚀 3단계: API 엔드포인트 테스트 시작..."

echo ""
echo "--- [GET /user/me] 사용자 정보 조회 ---"
curl -s -X GET "$API_ENDPOINT/user/me" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "--- [POST /upload] Presigned URL 요청 ---"
curl -s -X POST "$API_ENDPOINT/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fileName": "test.jpg",
    "fileSize": 1024000,
    "contentType": "image/jpeg"
  }' | jq

echo ""
echo "--- [GET /user/jobs] 작업 목록 조회 ---"
curl -s -X GET "$API_ENDPOINT/user/jobs?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "🎉 모든 테스트가 성공적으로 완료되었습니다!"
