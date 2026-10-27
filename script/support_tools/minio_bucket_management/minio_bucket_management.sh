#!/bin/bash
set -e

# MinIOサーバのバケットをAnsible SSH経由で作成・削除する
# 作業者用端末からAnsible SSH経由でMinIOサーバに接続して実行する

CURRENT_DIR="$(dirname "$0")"
INVENTORY="${CURRENT_DIR}/inventory.ini"
VARS_FILE="${CURRENT_DIR}/vars.yaml"

MODE="$1"

if [[ "$MODE" != "create" && "$MODE" != "delete" ]]; then
  echo "Usage: $0 {create|delete}"
  echo ""
  echo "  create  MinIOにバケットを作成します"
  echo "  delete  MinIOからバケットを削除します"
  exit 1
fi

PLAYBOOK="${CURRENT_DIR}/minio_bucket_${MODE}.yaml"

echo "[INFO] MinIOバケットの${MODE}を実行します"
ansible-playbook \
  -i "${INVENTORY}" "${PLAYBOOK}" \
  -e "@${VARS_FILE}"
echo "[SUCCESS] ${MODE}が完了しました"
