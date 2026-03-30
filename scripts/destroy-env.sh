#!/usr/bin/env bash

set -euo pipefail

ENVIRONMENT="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

terraform -chdir="$ROOT_DIR/terraform/envs/$ENVIRONMENT" destroy "$@"
