#!/bin/bash

# LocalStack 초기화 스크립트
# LocalStack이 준비되면 자동으로 실행됩니다.

set -e

echo "=========================================="
echo "ProfilePhotoAI LocalStack 초기화 시작"
echo "=========================================="

ENDPOINT="http://localhost:4566"
REGION="ap-northeast-2"

# AWS CLI 설정 (LocalStack용)
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=$REGION

echo ""
echo "📦 S3 버킷 생성 중..."
echo "------------------------------------------"

# S3 버킷 생성
aws --endpoint-url=$ENDPOINT s3 mb s3://profile-photo-ai-uploads-raw-dev --region $REGION 2>/dev/null || echo "✓ 버킷 이미 존재: profile-photo-ai-uploads-raw-dev"
aws --endpoint-url=$ENDPOINT s3 mb s3://profile-photo-ai-results-final-dev --region $REGION 2>/dev/null || echo "✓ 버킷 이미 존재: profile-photo-ai-results-final-dev"

# CORS 설정
cat > /tmp/cors-config.json <<EOF
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws --endpoint-url=$ENDPOINT s3api put-bucket-cors \
  --bucket profile-photo-ai-uploads-raw-dev \
  --cors-configuration file:///tmp/cors-config.json \
  --region $REGION

aws --endpoint-url=$ENDPOINT s3api put-bucket-cors \
  --bucket profile-photo-ai-results-final-dev \
  --cors-configuration file:///tmp/cors-config.json \
  --region $REGION

echo "✅ S3 버킷 생성 완료"

echo ""
echo "🗄️  DynamoDB 테이블 생성 중..."
echo "------------------------------------------"

# 1. Users 테이블
echo "생성 중: Profile-Photo-AI-Users-dev"
awscli dynamodb create-table \
  --table-name Profile-Photo-AI-Users-dev \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=email,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes \
    "[{
      \"IndexName\": \"EmailIndex\",
      \"KeySchema\": [{\"AttributeName\":\"email\",\"KeyType\":\"HASH\"}],
      \"Projection\": {\"ProjectionType\":\"ALL\"}
    }]" \
  --region $REGION \
  2>/dev/null || echo "✓ 테이블 이미 존재: Profile-Photo-AI-Users-dev"

# 2. UsageLog 테이블
echo "생성 중: Profile-Photo-AI-UsageLog-dev"
awscli dynamodb create-table \
  --table-name Profile-Photo-AI-UsageLog-dev \
  --attribute-definitions \
    AttributeName=userIdDate,AttributeType=S \
  --key-schema \
    AttributeName=userIdDate,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION \
  2>/dev/null || echo "✓ 테이블 이미 존재: Profile-Photo-AI-UsageLog-dev"

# 3. ImageJobs 테이블
echo "생성 중: Profile-Photo-AI-ImageJobs-dev"
awscli dynamodb create-table \
  --table-name Profile-Photo-AI-ImageJobs-dev \
  --attribute-definitions \
    AttributeName=jobId,AttributeType=S \
    AttributeName=userId,AttributeType=S \
    AttributeName=createdAt,AttributeType=N \
    AttributeName=status,AttributeType=S \
  --key-schema \
    AttributeName=jobId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --global-secondary-indexes \
    "[{
      \"IndexName\": \"UserIdCreatedAtIndex\",
      \"KeySchema\": [
        {\"AttributeName\":\"userId\",\"KeyType\":\"HASH\"},
        {\"AttributeName\":\"createdAt\",\"KeyType\":\"RANGE\"}
      ],
      \"Projection\": {\"ProjectionType\":\"ALL\"}
    },{
      \"IndexName\": \"StatusIndex\",
      \"KeySchema\": [
        {\"AttributeName\":\"status\",\"KeyType\":\"HASH\"},
        {\"AttributeName\":\"createdAt\",\"KeyType\":\"RANGE\"}
      ],
      \"Projection\": {\"ProjectionType\":\"ALL\"}
    }]" \
  --region $REGION \
  2>/dev/null || echo "✓ 테이블 이미 존재: Profile-Photo-AI-ImageJobs-dev"

echo "✅ DynamoDB 테이블 생성 완료"

echo ""
echo "📨 SQS 큐 생성 중..."
echo "------------------------------------------"

# DLQ 먼저 생성
echo "생성 중: Profile-Photo-AI-ImageProcess-DLQ-dev"
DLQ_URL=$(awscli sqs create-queue \
  --queue-name Profile-Photo-AI-ImageProcess-DLQ-dev \
  --region $REGION \
  --output text \
  --query 'QueueUrl' 2>/dev/null) || echo "✓ 큐 이미 존재"

# DLQ ARN 가져오기
if [ -z "$DLQ_URL" ]; then
  DLQ_URL=$(aws --endpoint-url=$ENDPOINT sqs get-queue-url \
    --queue-name Profile-Photo-AI-ImageProcess-DLQ-dev \
    --region $REGION \
    --output text \
    --query 'QueueUrl')
fi

DLQ_ARN=$(aws --endpoint-url=$ENDPOINT sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names QueueArn \
  --region $REGION \
  --output text \
  --query 'Attributes.QueueArn')

echo "DLQ ARN: $DLQ_ARN"

# 메인 큐 생성 (DLQ 연결)
echo "생성 중: Profile-Photo-AI-ImageProcess-dev"
awscli sqs create-queue \
  --queue-name Profile-Photo-AI-ImageProcess-dev \
  --attributes "{
    \"VisibilityTimeout\": \"900\",
    \"MessageRetentionPeriod\": \"1209600\",
    \"ReceiveMessageWaitTimeSeconds\": \"20\",
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"
  }" \
  --region $REGION \
  2>/dev/null || echo "✓ 큐 이미 존재: Profile-Photo-AI-ImageProcess-dev"

echo "✅ SQS 큐 생성 완료"

echo ""
echo "🎉 LocalStack 초기화 완료!"
echo "=========================================="
echo ""
echo "📋 생성된 리소스:"
echo "  S3 Buckets:"
echo "    - s3://profile-photo-ai-uploads-raw-dev"
echo "    - s3://profile-photo-ai-results-final-dev"
echo ""
echo "  DynamoDB Tables:"
echo "    - Profile-Photo-AI-Users-dev"
echo "    - Profile-Photo-AI-UsageLog-dev"
echo "    - Profile-Photo-AI-ImageJobs-dev"
echo ""
echo "  SQS Queues:"
echo "    - Profile-Photo-AI-ImageProcess-dev"
echo "    - Profile-Photo-AI-ImageProcess-DLQ-dev"
echo ""
echo "🔗 LocalStack Endpoint: http://localhost:4566"
echo "=========================================="
