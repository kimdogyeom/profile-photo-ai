#!/bin/bash

# ACM 인증서 생성 및 검증 스크립트
# CloudFront용 인증서는 반드시 us-east-1 리전에 생성되어야 함

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 인자 확인
if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    echo -e "${RED}Usage: $0 <domain> <hosted-zone-id> [additional-domains]${NC}"
    echo ""
    echo "Examples:"
    echo "  # 단일 도메인"
    echo "  $0 aigyeom.com Z04120473BUOE0AZ1WEE1"
    echo ""
    echo "  # Wildcard 도메인 (추천 - 모든 서브도메인 지원)"
    echo "  $0 '*.aigyeom.com' Z04120473BUOE0AZ1WEE1 aigyeom.com"
    echo ""
    echo "  # 여러 도메인 (SAN - Subject Alternative Names)"
    echo "  $0 aigyeom.com Z04120473BUOE0AZ1WEE1 'dev.aigyeom.com,www.aigyeom.com'"
    exit 1
fi

DOMAIN=$1
HOSTED_ZONE_ID=$2
ADDITIONAL_DOMAINS=$3
REGION="us-east-1"  # CloudFront requires us-east-1

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}  ACM 인증서 생성 및 검증${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo "Domain: ${DOMAIN}"
echo "Hosted Zone ID: ${HOSTED_ZONE_ID}"
echo "Region: ${REGION} (CloudFront requirement)"
echo ""

# 1. 기존 인증서 확인
echo -e "${YELLOW}📡 기존 인증서 확인 중...${NC}"
EXISTING_CERT=$(aws acm list-certificates \
    --region ${REGION} \
    --query "CertificateSummaryList[?DomainName=='${DOMAIN}'].CertificateArn" \
    --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_CERT" ]; then
    echo -e "${GREEN}✓ 이미 인증서가 존재합니다: ${EXISTING_CERT}${NC}"
    
    # 인증서 상태 확인
    CERT_STATUS=$(aws acm describe-certificate \
        --certificate-arn ${EXISTING_CERT} \
        --region ${REGION} \
        --query 'Certificate.Status' \
        --output text)
    
    echo "  상태: ${CERT_STATUS}"
    
    if [ "$CERT_STATUS" = "ISSUED" ]; then
        echo -e "${GREEN}  ✅ 인증서가 이미 발급되어 사용 가능합니다.${NC}"
        echo ""
        echo "Certificate ARN:"
        echo "${EXISTING_CERT}"
        exit 0
    else
        echo -e "${YELLOW}  ⚠️  인증서가 아직 검증되지 않았습니다.${NC}"
        echo "  계속하려면 아래 검증 단계를 따르세요."
        CERTIFICATE_ARN=${EXISTING_CERT}
    fi
else
    # 2. 새 인증서 요청
    echo -e "${YELLOW}🔧 새 ACM 인증서 요청 중...${NC}"
    
    # 추가 도메인 파라미터 구성
    SAN_OPTION=""
    if [ -n "$ADDITIONAL_DOMAINS" ]; then
        # 쉼표로 구분된 도메인을 공백으로 변환
        SAN_DOMAINS=$(echo $ADDITIONAL_DOMAINS | tr ',' ' ')
        SAN_OPTION="--subject-alternative-names ${DOMAIN} ${SAN_DOMAINS}"
        echo "  추가 도메인: ${SAN_DOMAINS}"
    fi
    
    CERTIFICATE_ARN=$(aws acm request-certificate \
        --domain-name ${DOMAIN} \
        ${SAN_OPTION} \
        --validation-method DNS \
        --region ${REGION} \
        --query 'CertificateArn' \
        --output text)
    
    echo -e "${GREEN}✓ 인증서 요청 완료: ${CERTIFICATE_ARN}${NC}"
    
    # 잠시 대기 (AWS가 검증 레코드를 생성하는 시간)
    echo "  검증 레코드 생성 대기 중... (5초)"
    sleep 5
fi

# 3. DNS 검증 레코드 가져오기
echo ""
echo -e "${YELLOW}📋 DNS 검증 레코드 가져오는 중...${NC}"

# 모든 도메인의 검증 레코드 가져오기
VALIDATION_OPTIONS=$(aws acm describe-certificate \
    --certificate-arn ${CERTIFICATE_ARN} \
    --region ${REGION} \
    --query 'Certificate.DomainValidationOptions' \
    --output json)

if [ -z "$VALIDATION_OPTIONS" ] || [ "$VALIDATION_OPTIONS" = "null" ] || [ "$VALIDATION_OPTIONS" = "[]" ]; then
    echo -e "${YELLOW}  ⚠️  검증 레코드가 아직 준비되지 않았습니다. 잠시 후 다시 시도하세요.${NC}"
    echo ""
    echo "다음 명령어로 확인하세요:"
    echo "  aws acm describe-certificate --certificate-arn ${CERTIFICATE_ARN} --region ${REGION}"
    exit 1
fi

echo -e "${GREEN}✓ 검증 레코드 정보:${NC}"

# 각 도메인의 검증 레코드 처리
DOMAIN_COUNT=$(echo $VALIDATION_OPTIONS | jq '. | length')
echo "  총 ${DOMAIN_COUNT}개 도메인 검증 필요"

# Route53 Change Batch 시작
CHANGE_BATCH_CHANGES="[]"

# 중복 레코드 방지를 위한 배열
declare -A SEEN_RECORDS

for i in $(seq 0 $((DOMAIN_COUNT - 1))); do
    VALIDATION_RECORD=$(echo $VALIDATION_OPTIONS | jq -r ".[$i].ResourceRecord")
    DOMAIN_NAME=$(echo $VALIDATION_OPTIONS | jq -r ".[$i].DomainName")
    
    if [ "$VALIDATION_RECORD" = "null" ] || [ -z "$VALIDATION_RECORD" ]; then
        echo "  ⚠️  ${DOMAIN_NAME}: 검증 레코드 대기 중..."
        continue
    fi
    
    RECORD_NAME=$(echo $VALIDATION_RECORD | jq -r '.Name')
    RECORD_TYPE=$(echo $VALIDATION_RECORD | jq -r '.Type')
    RECORD_VALUE=$(echo $VALIDATION_RECORD | jq -r '.Value')
    
    # 중복 체크: 같은 Name의 레코드는 한 번만 추가
    RECORD_KEY="${RECORD_NAME}:${RECORD_TYPE}"
    if [ -n "${SEEN_RECORDS[$RECORD_KEY]}" ]; then
        echo "  ${DOMAIN_NAME}: (중복, 건너뜀 - 같은 검증 레코드 사용)"
        continue
    fi
    SEEN_RECORDS[$RECORD_KEY]=1
    
    echo "  ${DOMAIN_NAME}:"
    echo "    Name: ${RECORD_NAME}"
    echo "    Type: ${RECORD_TYPE}"
    echo "    Value: ${RECORD_VALUE}"
    
    # Change Batch에 추가
    CHANGE_ITEM=$(cat <<EOF
{
  "Action": "UPSERT",
  "ResourceRecordSet": {
    "Name": "${RECORD_NAME}",
    "Type": "${RECORD_TYPE}",
    "TTL": 300,
    "ResourceRecords": [
      {
        "Value": "${RECORD_VALUE}"
      }
    ]
  }
}
EOF
)
    
    CHANGE_BATCH_CHANGES=$(echo $CHANGE_BATCH_CHANGES | jq ". += [$CHANGE_ITEM]")
done

if [ "$CHANGE_BATCH_CHANGES" = "[]" ]; then
    echo -e "${YELLOW}⚠️  검증 레코드가 아직 준비되지 않았습니다. 잠시 후 다시 실행하세요.${NC}"
    exit 1
fi

# 4. Route53에 검증 레코드 자동 생성
echo ""
echo -e "${YELLOW}🔧 Route53에 검증 레코드 생성 중...${NC}"

# Change batch 구성
CHANGE_BATCH=$(cat <<EOF
{
  "Changes": ${CHANGE_BATCH_CHANGES}
}
EOF
)

# Route53에 레코드 생성
CHANGE_ID=$(aws route53 change-resource-record-sets \
    --hosted-zone-id ${HOSTED_ZONE_ID} \
    --change-batch "${CHANGE_BATCH}" \
    --query 'ChangeInfo.Id' \
    --output text)

echo -e "${GREEN}✓ Route53 레코드 생성 완료: ${CHANGE_ID}${NC}"

# 5. DNS 전파 대기
echo ""
echo -e "${YELLOW}⏳ DNS 전파 대기 중... (최대 5분)${NC}"

aws route53 wait resource-record-sets-changed --id ${CHANGE_ID}

echo -e "${GREEN}✓ DNS 전파 완료${NC}"

# 6. ACM 검증 대기
echo ""
echo -e "${YELLOW}⏳ ACM 인증서 검증 대기 중... (최대 30분)${NC}"
echo "  참고: DNS 검증은 보통 5-10분 소요됩니다."

# 타임아웃 30분
TIMEOUT=1800
ELAPSED=0
INTERVAL=30

while [ $ELAPSED -lt $TIMEOUT ]; do
    CERT_STATUS=$(aws acm describe-certificate \
        --certificate-arn ${CERTIFICATE_ARN} \
        --region ${REGION} \
        --query 'Certificate.Status' \
        --output text)
    
    if [ "$CERT_STATUS" = "ISSUED" ]; then
        echo -e "${GREEN}✅ 인증서 검증 완료!${NC}"
        break
    elif [ "$CERT_STATUS" = "FAILED" ]; then
        echo -e "${RED}❌ 인증서 검증 실패${NC}"
        exit 1
    fi
    
    echo "  상태: ${CERT_STATUS} (${ELAPSED}초 경과)"
    sleep ${INTERVAL}
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${YELLOW}⚠️  타임아웃: 인증서 검증이 30분 내에 완료되지 않았습니다.${NC}"
    echo "수동으로 확인하세요:"
    echo "  aws acm describe-certificate --certificate-arn ${CERTIFICATE_ARN} --region ${REGION}"
    exit 1
fi

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  ACM 인증서 생성 및 검증 완료!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo "Certificate ARN (samconfig.toml에 추가하세요):"
echo "${CERTIFICATE_ARN}"
echo ""
echo "다음 단계:"
echo "1. samconfig.toml의 CertificateArn 파라미터에 위 ARN 추가"
echo "2. ./scripts/deploy.sh prod 실행"
echo ""
