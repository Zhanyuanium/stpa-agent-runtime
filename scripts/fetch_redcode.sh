#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-./benchmarks}"
DEST_DIR="${ROOT_DIR}/RedCode-Exec"

echo "Target directory: ${DEST_DIR}"
mkdir -p "${DEST_DIR}"

echo "Please download RedCode-Exec dataset manually from:"
echo "https://github.com/AI-secure/RedCode"
echo "Then place py2text_dataset_json under:"
echo "${DEST_DIR}/py2text_dataset_json"

echo "No data downloaded automatically to avoid license/compliance issues."
