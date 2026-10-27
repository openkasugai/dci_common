#!/bin/bash
set -e

# NFSサーバ上のテナントPVデータをAnsible SSH経由で削除する
# テナント削除前（ステップ0）に実行すること

CURRENT_DIR="$(dirname "$0")"
INVENTORY="${CURRENT_DIR}/inventory.ini"
VARS_FILE="${CURRENT_DIR}/vars.yaml"
PLAYBOOK="${CURRENT_DIR}/nfs_pv_cleanup.yaml"

echo "[INFO] NFSサーバのテナントPVデータを削除します"
ansible-playbook \
  -i "${INVENTORY}" "${PLAYBOOK}" \
  -e "@${VARS_FILE}"
echo "[SUCCESS] NFSサーバのテナントPVデータ削除が完了しました"
