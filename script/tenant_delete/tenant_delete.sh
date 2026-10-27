#!/bin/bash
set -e

# DCI管理用クラスタの各グループに対してPlaybookを順次実行
CURRENT_DIR="$(dirname "$0")"
INVENTORY="${CURRENT_DIR}/ansible/inventory/hosts"
PLAYBOOKS_BASE_DIR="${CURRENT_DIR}/ansible/playbooks"
LOG_DIR="${CURRENT_DIR}/ansible/logs"
VAULT_PASSWORD_FILE="${CURRENT_DIR}/ansible/.vault_pass"

# ansible.cfgのパスを環境変数で指定
export ANSIBLE_CONFIG="${CURRENT_DIR}/ansible/ansible.cfg"

# ログディレクトリの作成
SHELL_SCRIPT_NAME=$(basename "$0" .sh)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SHELL_LOG_NAME="${TIMESTAMP}_${SHELL_SCRIPT_NAME}"
FULL_SHELL_LOG_PATH="${LOG_DIR}/${SHELL_LOG_NAME}"
mkdir -p "${FULL_SHELL_LOG_PATH}"

# Playbookとそのターゲットグループの定義
# 実行順序を保証するため、配列でPlaybook名を管理し、連想配列でターゲットグループを管理
PLAYBOOK_ORDER=(
    "01-tenant_logical_infra_delete.yaml"
    "02-cleanup_k8s_resources.yaml"
    "03-cleanup_certs_and_crio.yaml"
    "04-cleanup_coredns.yaml"
    "05-remove_firewall_rules_on_manager.yaml"
    "06-cleanup_harbor_replication.yaml"
)

declare -A PLAYBOOK_TARGETS
PLAYBOOK_TARGETS["01-tenant_logical_infra_delete.yaml"]="dci_mgmt_k8s_control_plane[0]" # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["02-cleanup_k8s_resources.yaml"]="dci_mgmt_k8s_control_plane[0]"     # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["03-cleanup_certs_and_crio.yaml"]="dci_mgmt_k8s_control_plane"        # 全コントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["04-cleanup_coredns.yaml"]="dci_mgmt_k8s_control_plane[0]"            # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["05-remove_firewall_rules_on_manager.yaml"]="dci_mgmt_k8s_control_plane" # 全コントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["06-cleanup_harbor_replication.yaml"]="dci_mgmt_k8s_control_plane[0]" # 1台目のコントロールプレーンノードに対して実行

# 定義されたPlaybookを順番に実行（配列の順序を使用）
for playbook_name in "${PLAYBOOK_ORDER[@]}"; do
    # 各Playbookのターゲットグループに対して実行
    for group in ${PLAYBOOK_TARGETS[$playbook_name]}; do
        # 対象グループに実行可能なホストが存在するかチェック
        set +e
        HOST_LIST=$(ansible-playbook --vault-password-file "${VAULT_PASSWORD_FILE}" "${PLAYBOOKS_BASE_DIR}/${playbook_name}" -i "$INVENTORY" -l "$group" --list-hosts 2>&1 >/dev/null | grep "ERROR! ")
        set -e

        if [ -n "$HOST_LIST" ]; then
            echo "[WARN] ${playbook_name} の $group グループには実行可能なホストが定義されていないため、スキップします"
            continue
        fi

        echo "[INFO] ${playbook_name} を $group グループに対して実行します"
        set +e  # 一時的にset -eを無効化
        ansible-playbook --vault-password-file "${VAULT_PASSWORD_FILE}" "${PLAYBOOKS_BASE_DIR}/${playbook_name}" \
            -i "$INVENTORY" \
            -l "$group" \
            -e "playbook_log_base_path=${FULL_SHELL_LOG_PATH}"
        ANSIBLE_EXIT_CODE=$?
        set -e  # set -eを再有効化
        if [ $ANSIBLE_EXIT_CODE -ne 0 ]; then
            echo "[ERROR] ${playbook_name} の $group 実行に失敗しました" >&2
            exit 1
        fi
        echo "[INFO] ${playbook_name} の $group 実行が完了しました"
    done
    echo "[SUCCESS] ${playbook_name} 実行が完了しました"
done

echo "[SUCCESS] 全Playbook実行が完了しました"
