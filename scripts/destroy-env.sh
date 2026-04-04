#!/usr/bin/env bash

set -euo pipefail

ENVIRONMENT="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

shift || true

"$ROOT_DIR/scripts/tf.sh" destroy "$ENVIRONMENT" "$@"
