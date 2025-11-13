#!/bin/bash
# CloudFormation 스택 삭제 스크립트
# 사용법: ./scripts/cleanup.sh [dev|prod] [options]

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
    echo "  --keep-secrets  Secrets Manager 보존"
    echo "  --keep-data     S3 및 DynamoDB 데이터 백업"
    echo "  --force         확인 없이 즉시 삭제"
    echo ""
    echo "Examples:"
    echo "  $0 dev"
    echo "  $0 prod --keep-secrets --keep-data"
    exit 1
}

# 환경 검증
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    echo -e "${RED}❌ 에러: 환경은 'dev' 또는 'prod'여야 합니다.${NC}"
    usage
fi

# 옵션 파싱
KEEP_SECRETS=false
KEEP_DATA=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --keep-secrets)
            KEEP_SECRETS=true
            shift
            ;;
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            usage
            ;;
    esac
done

echo -e "${RED}⚠️  ProfilePhotoAI ${ENVIRONMENT} 환경 삭제${NC}"
echo "  - 스택 이름: ${STACK_NAME}"
echo "  - 리전: ${REGION}"
echo ""

# AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ 에러: AWS CLI가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# 스택 존재 여부 확인
STACK_EXISTS=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].StackName' \
    --output text 2>/dev/null || echo "None")

if [ "$STACK_EXISTS" = "None" ] || [ "$STACK_EXISTS" = "" ]; then
    echo -e "${YELLOW}⚠️  스택이 존재하지 않습니다: ${STACK_NAME}${NC}"
    exit 0
fi

# 스택 정보 출력
echo "📋 현재 스택 정보:"
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].{Status:StackStatus, Created:CreationTime}' \
    --output table

echo ""
echo "📦 삭제될 리소스:"
aws cloudformation list-stack-resources \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'StackResourceSummaries[].{Type:ResourceType, LogicalId:LogicalResourceId, PhysicalId:PhysicalResourceId}' \
    --output table

echo ""

# 확인
if [ "$FORCE" = false ]; then
    echo -e "${RED}⚠️  경고: 이 작업은 되돌릴 수 없습니다!${NC}"
    echo ""
    read -p "정말 ${STACK_NAME} 스택을 삭제하시겠습니까? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "❌ 작업이 취소되었습니다."
        exit 0
    fi
fi

# 1. 데이터 백업 (선택적)
if [ "$KEEP_DATA" = true ]; then
    echo -e "${BLUE}💾 1단계: 데이터 백업${NC}"
    
    BACKUP_DIR="backup/${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S)"
    mkdir -p ${BACKUP_DIR}
    
    echo "  - 백업 디렉토리: ${BACKUP_DIR}"
    
    # S3 버킷 목록 가져오기
    UPLOAD_BUCKET=$(aws cloudformation describe-stack-resources \
        --stack-name ${STACK_NAME} \
        --region ${REGION} \
        --query 'StackResources[?ResourceType==`AWS::S3::Bucket` && LogicalResourceId==`UploadBucket`].PhysicalResourceId' \
        --output text 2>/dev/null)
    
    RESULT_BUCKET=$(aws cloudformation describe-stack-resources \
        --stack-name ${STACK_NAME} \
        --region ${REGION} \
        --query 'StackResources[?ResourceType==`AWS::S3::Bucket` && LogicalResourceId==`ResultBucket`].PhysicalResourceId' \
        --output text 2>/dev/null)
    
    # S3 데이터 백업
    if [ -n "$UPLOAD_BUCKET" ] && [ "$UPLOAD_BUCKET" != "None" ]; then
        echo "  - Upload 버킷 백업 중: ${UPLOAD_BUCKET}"
        aws s3 sync s3://${UPLOAD_BUCKET} ${BACKUP_DIR}/upload-bucket/ --region ${REGION} || true
    fi
    
    if [ -n "$RESULT_BUCKET" ] && [ "$RESULT_BUCKET" != "None" ]; then
        echo "  - Result 버킷 백업 중: ${RESULT_BUCKET}"
        aws s3 sync s3://${RESULT_BUCKET} ${BACKUP_DIR}/result-bucket/ --region ${REGION} || true
    fi
    
    # DynamoDB 테이블 백업 (스냅샷 생성)
    for table in "Users" "UsageLog" "ImageJobs"; do
        TABLE_NAME=$(aws cloudformation describe-stack-resources \
            --stack-name ${STACK_NAME} \
            --region ${REGION} \
            --query "StackResources[?ResourceType==\`AWS::DynamoDB::Table\` && LogicalResourceId==\`${table}Table\`].PhysicalResourceId" \
            --output text 2>/dev/null)
        
        if [ -n "$TABLE_NAME" ] && [ "$TABLE_NAME" != "None" ]; then
            echo "  - DynamoDB 테이블 백업 중: ${TABLE_NAME}"
            BACKUP_NAME="${TABLE_NAME}-backup-$(date +%Y%m%d-%H%M%S)"
            aws dynamodb create-backup \
                --table-name ${TABLE_NAME} \
                --backup-name ${BACKUP_NAME} \
                --region ${REGION} || true
        fi
    done
    
    echo -e "${GREEN}  ✅ 백업 완료: ${BACKUP_DIR}${NC}"
    echo ""
fi

# 2. S3 버킷 비우기
echo -e "${BLUE}🗑️  2단계: S3 버킷 비우기${NC}"

# CloudFormation 스택의 S3 버킷 목록
BUCKETS=$(aws cloudformation describe-stack-resources \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'StackResources[?ResourceType==`AWS::S3::Bucket`].PhysicalResourceId' \
    --output text 2>/dev/null)

if [ -n "$BUCKETS" ]; then
    for BUCKET in $BUCKETS; do
        if [ -n "$BUCKET" ] && [ "$BUCKET" != "None" ]; then
            echo "  - 버킷 비우는 중: ${BUCKET}"
            
            # 버킷 버전 관리 확인
            VERSIONED=$(aws s3api get-bucket-versioning \
                --bucket ${BUCKET} \
                --region ${REGION} \
                --query 'Status' \
                --output text 2>/dev/null || echo "None")
            
            if [ "$VERSIONED" = "Enabled" ]; then
                # 버전 관리된 버킷: 모든 버전 삭제
                aws s3api delete-objects \
                    --bucket ${BUCKET} \
                    --delete "$(aws s3api list-object-versions \
                        --bucket ${BUCKET} \
                        --region ${REGION} \
                        --output json \
                        --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')" \
                    --region ${REGION} 2>/dev/null || true
            else
                # 일반 버킷: aws s3 rm 사용
                aws s3 rm s3://${BUCKET} --recursive --region ${REGION} 2>/dev/null || true
            fi
            
            echo -e "${GREEN}    ✅ 버킷 비움: ${BUCKET}${NC}"
        fi
    done
else
    echo "  - S3 버킷이 없습니다."
fi

echo ""

# 3. 스택 삭제
echo -e "${BLUE}🗑️  3단계: CloudFormation 스택 삭제${NC}"
echo "  - 스택 삭제 중: ${STACK_NAME}"

sam delete \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --no-prompts

echo -e "${GREEN}  ✅ 스택 삭제 요청 완료${NC}"
echo ""

# 4. Secrets Manager 삭제 (선택적)
if [ "$KEEP_SECRETS" = false ]; then
    echo -e "${BLUE}🔐 4단계: Secrets Manager 삭제${NC}"
    
    SECRET_NAME="/profile-photo-ai/${ENVIRONMENT}/gemini-api-key"
    SECRET_EXISTS=$(aws secretsmanager list-secrets \
        --region ${REGION} \
        --filters Key=name,Values=${SECRET_NAME} \
        --query 'SecretList[0].Name' \
        --output text 2>/dev/null || echo "None")
    
    if [ "$SECRET_EXISTS" != "None" ] && [ "$SECRET_EXISTS" != "" ]; then
        echo "  - 시크릿 삭제 중: ${SECRET_NAME}"
        
        # 즉시 삭제 (복구 불가)
        aws secretsmanager delete-secret \
            --secret-id ${SECRET_NAME} \
            --force-delete-without-recovery \
            --region ${REGION}
        
        echo -e "${GREEN}  ✅ 시크릿 삭제 완료${NC}"
    else
        echo "  - 삭제할 시크릿이 없습니다."
    fi
else
    echo -e "${YELLOW}⏭️  Secrets Manager 보존 (--keep-secrets 옵션)${NC}"
fi

echo ""
echo -e "${GREEN}🎉 정리 완료!${NC}"
echo ""

if [ "$KEEP_DATA" = true ]; then
    echo "💾 백업 위치: ${BACKUP_DIR}"
    echo ""
fi

echo "📋 확인 사항:"
echo "1. CloudFormation 콘솔에서 스택 삭제 완료 확인"
echo "2. 백업된 데이터 확인 (필요한 경우)"
echo "3. DynamoDB 백업 목록 확인"
echo ""
echo "유용한 명령어:"
echo "  - 스택 상태 확인: aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION}"
echo "  - DynamoDB 백업 목록: aws dynamodb list-backups --region ${REGION}"
