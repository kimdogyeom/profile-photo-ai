#!/usr/bin/env bash

set -euo pipefail

ACTION="${1:-}"
TARGET="${2:-all}"

if [[ -z "$ACTION" ]]; then
  echo "Usage: $0 <apply|write-backend|all> [dev|prod|all]"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP_DIR="$ROOT_DIR/terraform/bootstrap"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"

init_bootstrap() {
  terraform -chdir="$BOOTSTRAP_DIR" init >/dev/null
}

apply_bootstrap() {
  if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "GITHUB_TOKEN is required to apply terraform/bootstrap because GitHub Environment resources are managed there."
    exit 1
  fi

  terraform -chdir="$BOOTSTRAP_DIR" apply -auto-approve
}

get_output() {
  local key="$1"

  terraform -chdir="$BOOTSTRAP_DIR" output -raw "$key" 2>/dev/null
}

write_backend_file() {
  local environment="$1"
  local bucket="$2"
  local lock_table="$3"
  local backend_file="$ROOT_DIR/terraform/envs/$environment/backend.hcl"

  cat >"$backend_file" <<EOF
bucket         = "$bucket"
key            = "profile-photo-ai/${environment}/terraform.tfstate"
region         = "$AWS_REGION"
dynamodb_table = "$lock_table"
encrypt        = true
EOF

  echo "Wrote $backend_file"
}

write_backends() {
  local bucket
  local lock_table

  bucket="$(get_output state_bucket_name)"
  lock_table="$(get_output lock_table_name)"

  if [[ -z "$bucket" || -z "$lock_table" ]]; then
    echo "Bootstrap outputs are unavailable. Run '$0 apply' first or apply terraform/bootstrap manually."
    exit 1
  fi

  case "$TARGET" in
    dev|prod)
      write_backend_file "$TARGET" "$bucket" "$lock_table"
      ;;
    all)
      write_backend_file "dev" "$bucket" "$lock_table"
      write_backend_file "prod" "$bucket" "$lock_table"
      ;;
    *)
      echo "Unsupported target: $TARGET"
      exit 1
      ;;
  esac
}

case "$ACTION" in
  apply)
    init_bootstrap
    apply_bootstrap
    ;;
  write-backend)
    init_bootstrap
    write_backends
    ;;
  all)
    init_bootstrap
    apply_bootstrap
    write_backends
    ;;
  *)
    echo "Unsupported action: $ACTION"
    exit 1
    ;;
esac
