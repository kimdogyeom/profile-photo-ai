#!/usr/bin/env bash

set -euo pipefail

ENVIRONMENT="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/terraform/envs/$ENVIRONMENT"
FRONTEND_DIR="$ROOT_DIR/frontend"

API_BASE_URL="$(terraform -chdir="$TF_DIR" output -raw api_base_url)"
AWS_REGION="$(terraform -chdir="$TF_DIR" output -raw aws_region)"
USER_POOL_ID="$(terraform -chdir="$TF_DIR" output -raw cognito_user_pool_id)"
CLIENT_ID="$(terraform -chdir="$TF_DIR" output -raw cognito_user_pool_client_id)"

FRONTEND_BUCKET="$(terraform -chdir="$TF_DIR" output -raw frontend_bucket_name)"
DIST_ID="$(terraform -chdir="$TF_DIR" output -raw frontend_distribution_id)"

cd "$FRONTEND_DIR"
npm ci
REACT_APP_API_BASE_URL="$API_BASE_URL" \
REACT_APP_AWS_REGION="$AWS_REGION" \
REACT_APP_COGNITO_USER_POOL_ID="$USER_POOL_ID" \
REACT_APP_COGNITO_CLIENT_ID="$CLIENT_ID" \
  npm run build

aws s3 sync "$FRONTEND_DIR/build/" "s3://${FRONTEND_BUCKET}/" --delete
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null

echo "Frontend deployed to ${ENVIRONMENT}"
