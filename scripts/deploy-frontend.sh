#!/usr/bin/env bash

set -euo pipefail

ENVIRONMENT="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
FRONTEND_BUILD_DIR="$FRONTEND_DIR/build"

command -v npm >/dev/null || {
  echo "npm is required to build and deploy the frontend"
  exit 1
}

command -v aws >/dev/null || {
  echo "aws cli is required to deploy the frontend"
  exit 1
}

"$ROOT_DIR/scripts/tf.sh" init "$ENVIRONMENT" >/dev/null

get_output() {
  local key="$1"
  local value

  value="$("$ROOT_DIR/scripts/tf.sh" output "$ENVIRONMENT" -raw "$key")"
  if [[ -z "$value" || "$value" == "null" ]]; then
    echo "Required Terraform output not available: $key"
    exit 1
  fi
  echo "$value"
}

API_BASE_URL="$(get_output api_base_url)"
AWS_REGION="$(get_output aws_region)"
USER_POOL_ID="$(get_output cognito_user_pool_id)"
CLIENT_ID="$(get_output cognito_user_pool_client_id)"
FRONTEND_BUCKET="$(get_output frontend_bucket_name)"
DIST_ID="$(get_output frontend_distribution_id)"

cd "$FRONTEND_DIR"
npm ci --no-audit --no-fund
REACT_APP_API_BASE_URL="$API_BASE_URL" \
REACT_APP_AWS_REGION="$AWS_REGION" \
REACT_APP_COGNITO_USER_POOL_ID="$USER_POOL_ID" \
REACT_APP_COGNITO_CLIENT_ID="$CLIENT_ID" \
  npm run build

if [[ ! -f "$FRONTEND_BUILD_DIR/index.html" ]]; then
  echo "Frontend build artifact not found: $FRONTEND_BUILD_DIR/index.html"
  exit 1
fi

aws s3 sync "$FRONTEND_BUILD_DIR/" "s3://${FRONTEND_BUCKET}/" --delete
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null

echo "Frontend deployed to ${ENVIRONMENT}"
