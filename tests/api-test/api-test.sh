#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${API_TEST_ENV_FILE:-$SCRIPT_DIR/.env}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

AWS_REGION="${AWS_REGION:-ap-northeast-1}"
TEST_IMAGE_PATH="${TEST_IMAGE_PATH:-$ROOT_DIR/tests/test-data/test-image.jpg}"
TEST_CONTENT_TYPE="${TEST_CONTENT_TYPE:-image/jpeg}"
TEST_FILE_NAME="${TEST_FILE_NAME:-$(basename "$TEST_IMAGE_PATH")}"
TEST_PROMPT="${TEST_PROMPT:-Professional profile photo, natural lighting, neutral background}"
TEST_STYLE="${TEST_STYLE:-formal_interview}"
JOB_POLL_INTERVAL_SECONDS="${JOB_POLL_INTERVAL_SECONDS:-5}"
JOB_POLL_MAX_ATTEMPTS="${JOB_POLL_MAX_ATTEMPTS:-30}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
}

decode_json_value() {
  local encoded="$1"
  printf '%s' "$encoded" | base64 --decode
}

request_json() {
  local method="$1"
  local url="$2"
  local body_file="${3:-}"
  local auth_token="${4:-}"
  local response_file="$TMP_DIR/response.json"
  local status
  local curl_args=(
    --silent
    --show-error
    --output "$response_file"
    --write-out "%{http_code}"
    --request "$method"
    "$url"
  )

  if [[ -n "$auth_token" ]]; then
    curl_args+=(-H "Authorization: Bearer $auth_token")
  fi

  if [[ -n "$body_file" ]]; then
    curl_args+=(-H "Content-Type: application/json" --data "@$body_file")
  fi

  status="$(curl "${curl_args[@]}")"
  if [[ ! "$status" =~ ^2 ]]; then
    echo "HTTP ${status} for ${method} ${url}" >&2
    cat "$response_file" >&2
    exit 1
  fi

  cat "$response_file"
}

echo_step() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

require_command aws
require_command curl
require_command jq
require_command base64

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

require_var API_ENDPOINT
require_var USER_POOL_ID
require_var CLIENT_ID
require_var TEST_USER_EMAIL
require_var TEST_USER_TEMP_PASS
require_var TEST_USER_PERM_PASS

if [[ ! -f "$TEST_IMAGE_PATH" ]]; then
  echo "Missing test image: $TEST_IMAGE_PATH" >&2
  exit 1
fi

echo_step "Ensure Cognito test user exists"
aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$TEST_USER_EMAIL" \
  --user-attributes Name=email,Value="$TEST_USER_EMAIL" Name=email_verified,Value=true \
  --temporary-password "$TEST_USER_TEMP_PASS" \
  --message-action SUPPRESS \
  --region "$AWS_REGION" >/dev/null 2>&1 || true

aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$TEST_USER_EMAIL" \
  --password "$TEST_USER_PERM_PASS" \
  --permanent \
  --region "$AWS_REGION" >/dev/null

echo_step "Authenticate test user"
TOKEN="$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters "USERNAME=$TEST_USER_EMAIL,PASSWORD=$TEST_USER_PERM_PASS" \
  --region "$AWS_REGION" \
  --query 'AuthenticationResult.IdToken' \
  --output text)"

if [[ -z "$TOKEN" || "$TOKEN" == "None" ]]; then
  echo "Failed to obtain Cognito ID token" >&2
  exit 1
fi

echo_step "Verify /user/me"
USER_ME_JSON="$(request_json GET "$API_ENDPOINT/user/me" "" "$TOKEN")"
printf '%s\n' "$USER_ME_JSON" | jq .
USER_ID="$(printf '%s' "$USER_ME_JSON" | jq -r '.userId // empty')"
if [[ -z "$USER_ID" ]]; then
  echo "/user/me did not return userId" >&2
  exit 1
fi

echo_step "Request presigned upload"
TEST_FILE_SIZE="$(wc -c < "$TEST_IMAGE_PATH" | tr -d ' ')"
UPLOAD_PAYLOAD="$TMP_DIR/upload.json"
jq -n \
  --arg fileName "$TEST_FILE_NAME" \
  --arg contentType "$TEST_CONTENT_TYPE" \
  --argjson fileSize "$TEST_FILE_SIZE" \
  '{fileName: $fileName, fileSize: $fileSize, contentType: $contentType}' > "$UPLOAD_PAYLOAD"

UPLOAD_JSON="$(request_json POST "$API_ENDPOINT/upload" "$UPLOAD_PAYLOAD" "$TOKEN")"
printf '%s\n' "$UPLOAD_JSON" | jq .

UPLOAD_URL="$(printf '%s' "$UPLOAD_JSON" | jq -r '.uploadUrl // empty')"
UPLOAD_METHOD="$(printf '%s' "$UPLOAD_JSON" | jq -r '.uploadMethod // "POST"')"
FILE_KEY="$(printf '%s' "$UPLOAD_JSON" | jq -r '.fileKey // empty')"

if [[ -z "$UPLOAD_URL" || -z "$FILE_KEY" ]]; then
  echo "/upload response is missing uploadUrl or fileKey" >&2
  exit 1
fi

echo_step "Upload image bytes to S3"
if [[ "$UPLOAD_METHOD" == "POST" ]]; then
  upload_args=()
  while IFS= read -r entry; do
    key="$(decode_json_value "$entry" | jq -r '.key')"
    value="$(decode_json_value "$entry" | jq -r '.value')"
    upload_args+=(-F "${key}=${value}")
  done < <(printf '%s' "$UPLOAD_JSON" | jq -r '.uploadFields | to_entries[] | @base64')

  upload_args+=(-F "file=@${TEST_IMAGE_PATH};type=${TEST_CONTENT_TYPE}")
  upload_status="$(
    curl \
      --silent \
      --show-error \
      --output /dev/null \
      --write-out "%{http_code}" \
      --request POST \
      "${upload_args[@]}" \
      "$UPLOAD_URL"
  )"
else
  upload_status="$(
    curl \
      --silent \
      --show-error \
      --output /dev/null \
      --write-out "%{http_code}" \
      --request "$UPLOAD_METHOD" \
      --header "Content-Type: $TEST_CONTENT_TYPE" \
      --data-binary "@$TEST_IMAGE_PATH" \
      "$UPLOAD_URL"
  )"
fi

case "$upload_status" in
  200|201|204) ;;
  *)
    echo "S3 upload failed with status ${upload_status}" >&2
    exit 1
    ;;
esac

echo_step "Request image generation"
GENERATE_PAYLOAD="$TMP_DIR/generate.json"
jq -n \
  --arg fileKey "$FILE_KEY" \
  --arg prompt "$TEST_PROMPT" \
  --arg style "$TEST_STYLE" \
  '{fileKey: $fileKey, prompt: $prompt, style: $style}' > "$GENERATE_PAYLOAD"

GENERATE_JSON="$(request_json POST "$API_ENDPOINT/generate" "$GENERATE_PAYLOAD" "$TOKEN")"
printf '%s\n' "$GENERATE_JSON" | jq .

JOB_ID="$(printf '%s' "$GENERATE_JSON" | jq -r '.jobId // empty')"
if [[ -z "$JOB_ID" ]]; then
  echo "/generate response is missing jobId" >&2
  exit 1
fi

echo_step "Poll job status"
JOB_STATUS=""
JOB_JSON=""
for attempt in $(seq 1 "$JOB_POLL_MAX_ATTEMPTS"); do
  JOB_JSON="$(request_json GET "$API_ENDPOINT/jobs/$JOB_ID" "" "$TOKEN")"
  JOB_STATUS="$(printf '%s' "$JOB_JSON" | jq -r '.status // empty')"
  printf '[%s/%s] status=%s\n' "$attempt" "$JOB_POLL_MAX_ATTEMPTS" "$JOB_STATUS"

  case "$JOB_STATUS" in
    completed)
      break
      ;;
    failed)
      printf '%s\n' "$JOB_JSON" | jq .
      echo "Image generation job failed" >&2
      exit 1
      ;;
    queued|processing|pending)
      sleep "$JOB_POLL_INTERVAL_SECONDS"
      ;;
    *)
      printf '%s\n' "$JOB_JSON" | jq .
      echo "Unexpected job status: ${JOB_STATUS:-<empty>}" >&2
      exit 1
      ;;
  esac
done

if [[ "$JOB_STATUS" != "completed" ]]; then
  printf '%s\n' "$JOB_JSON" | jq .
  echo "Job did not complete within ${JOB_POLL_MAX_ATTEMPTS} attempts" >&2
  exit 1
fi

echo_step "Verify /user/jobs contains the new job"
USER_JOBS_JSON="$(request_json GET "$API_ENDPOINT/user/jobs?limit=10" "" "$TOKEN")"
printf '%s' "$USER_JOBS_JSON" | jq -e --arg jobId "$JOB_ID" 'any(.jobs[]?; .jobId == $jobId)' >/dev/null

echo_step "Fetch download URL"
DOWNLOAD_JSON="$(request_json GET "$API_ENDPOINT/jobs/$JOB_ID/download" "" "$TOKEN")"
printf '%s\n' "$DOWNLOAD_JSON" | jq .
DOWNLOAD_URL="$(printf '%s' "$DOWNLOAD_JSON" | jq -r '.downloadUrl // empty')"
if [[ -z "$DOWNLOAD_URL" ]]; then
  echo "Download URL missing from /jobs/$JOB_ID/download" >&2
  exit 1
fi

download_status="$(
  curl \
    --silent \
    --show-error \
    --output /dev/null \
    --write-out "%{http_code}" \
    "$DOWNLOAD_URL"
)"

if [[ "$download_status" != "200" ]]; then
  echo "Download URL returned unexpected status: $download_status" >&2
  exit 1
fi

echo_step "End-to-end API test completed successfully"
printf 'userId=%s\njobId=%s\nfileKey=%s\n' "$USER_ID" "$JOB_ID" "$FILE_KEY"
