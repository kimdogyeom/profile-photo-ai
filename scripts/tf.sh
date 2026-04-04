#!/usr/bin/env bash

set -euo pipefail

ACTION="${1:-}"
ENVIRONMENT="${2:-}"

if [[ -z "$ACTION" || -z "$ENVIRONMENT" ]]; then
  echo "Usage: $0 <init|plan|apply|destroy|output|validate> <dev|prod> [extra terraform args...]"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/terraform/envs/$ENVIRONMENT"
BACKEND_FILE="$TF_DIR/backend.hcl"
BACKEND_BUCKET="${TF_STATE_BUCKET:-profile-photo-ai-terraform-state}"
BACKEND_KEY="${TF_STATE_KEY:-profile-photo-ai/${ENVIRONMENT}/terraform.tfstate}"
BACKEND_REGION="${TF_STATE_REGION:-ap-northeast-1}"
BACKEND_DYNAMODB_TABLE="${TF_STATE_DYNAMODB_TABLE:-profile-photo-ai-terraform-locks}"
BACKEND_ENCRYPT="${TF_STATE_ENCRYPT:-true}"

if [[ ! -d "$TF_DIR" ]]; then
  echo "Terraform directory not found: $TF_DIR"
  exit 1
fi

shift 2

get_backend_args() {
  local args=()

  if [[ -f "$BACKEND_FILE" ]]; then
    args+=("-backend-config=$BACKEND_FILE")
    return 0
  fi

  args+=(
    "-backend-config=bucket=$BACKEND_BUCKET"
    "-backend-config=key=$BACKEND_KEY"
    "-backend-config=region=$BACKEND_REGION"
    "-backend-config=dynamodb_table=$BACKEND_DYNAMODB_TABLE"
    "-backend-config=encrypt=$BACKEND_ENCRYPT"
  )

  echo "⚠️ ${BACKEND_FILE} not found. Falling back to Terraform backend env defaults." >&2
  echo "   Set TF_STATE_BUCKET / TF_STATE_KEY / TF_STATE_REGION / TF_STATE_DYNAMODB_TABLE as needed." >&2

  printf '%s\0' "${args[@]}"
}

BACKEND_ARGS=()
while IFS= read -r -d '' arg; do
  BACKEND_ARGS+=("$arg")
done < <(get_backend_args)

case "$ACTION" in
  init)
    terraform -chdir="$TF_DIR" init -reconfigure "${BACKEND_ARGS[@]}" "$@"
    ;;
  plan|apply|destroy|output|validate)
    terraform -chdir="$TF_DIR" "$ACTION" "$@"
    ;;
  *)
    echo "Unsupported action: $ACTION"
    exit 1
    ;;
esac
