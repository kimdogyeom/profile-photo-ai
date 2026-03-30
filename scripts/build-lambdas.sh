#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist/lambda"
COMMON_DIR="$ROOT_DIR/backend/common"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

build_function() {
  local name="$1"
  local source_dir="$2"
  local artifact_name="$3"
  local staging_dir

  staging_dir="$(mktemp -d)"
  cp -R "$source_dir"/. "$staging_dir"/
  cp -R "$COMMON_DIR" "$staging_dir/common"

  find "$staging_dir" -type d -name "__pycache__" -prune -exec rm -rf {} +
  find "$staging_dir" -type f -name "*.pyc" -delete

  if [[ -f "$source_dir/requirements.txt" ]]; then
    python3 -m pip install --quiet -r "$source_dir/requirements.txt" -t "$staging_dir"
  fi

  find "$staging_dir" -type d -name "__pycache__" -prune -exec rm -rf {} +
  find "$staging_dir" -type f -name "*.pyc" -delete

  (
    cd "$staging_dir"
    zip -qr "$DIST_DIR/$artifact_name.zip" .
  )

  rm -rf "$staging_dir"
  echo "Built $name -> dist/lambda/$artifact_name.zip"
}

build_function "file-transfer" "$ROOT_DIR/backend/lambda/file_transfer" "file-transfer"
build_function "api-manager" "$ROOT_DIR/backend/lambda/api" "api-manager"
build_function "image-process" "$ROOT_DIR/backend/lambda/process" "image-process"
build_function "stats-aggregator" "$ROOT_DIR/backend/lambda/monitoring/stats_aggregator" "stats-aggregator"
build_function "webhook-notifier" "$ROOT_DIR/backend/lambda/monitoring/webhook_notifier" "webhook-notifier"
