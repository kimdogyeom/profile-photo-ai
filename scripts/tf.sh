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

shift 2

case "$ACTION" in
  init)
    terraform -chdir="$TF_DIR" init -backend-config="$BACKEND_FILE" "$@"
    ;;
  plan|apply|destroy|output|validate)
    terraform -chdir="$TF_DIR" "$ACTION" "$@"
    ;;
  *)
    echo "Unsupported action: $ACTION"
    exit 1
    ;;
esac
