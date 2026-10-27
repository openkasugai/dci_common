#!/bin/bash
set -e

# DCI管理用クラスタの各グループに対してPlaybookを順次実行
CURRENT_DIR="$(dirname "$0")"
INVENTORY="${CURRENT_DIR}/ansible/inventory/hosts"
PLAYBOOKS_BASE_DIR="${CURRENT_DIR}/ansible/playbooks"
LOG_DIR="${CURRENT_DIR}/ansible/logs"

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
    "01-pre_setup_proxy.yaml"
    "02-k8s_install.yaml"
    "03-crio_install.yaml"
    "04-crio_config.yaml"
    "05-k8s_cluster_pre_setup_1.yaml"
    "06-k8s_cluster_pre_setup_2.yaml"
    "07-k8s_cluster_init.yaml"
    "08-k8s_cluster_join_cp.yaml"
    "09-k8s_cluster_join_wk.yaml"
)

declare -A PLAYBOOK_TARGETS
PLAYBOOK_TARGETS["01-pre_setup_proxy.yaml"]="all"
PLAYBOOK_TARGETS["02-k8s_install.yaml"]="all"
PLAYBOOK_TARGETS["03-crio_install.yaml"]="all"
PLAYBOOK_TARGETS["04-crio_config.yaml"]="all"
PLAYBOOK_TARGETS["05-k8s_cluster_pre_setup_1.yaml"]="all"
PLAYBOOK_TARGETS["06-k8s_cluster_pre_setup_2.yaml"]="dci_mgmt_k8s_control_plane[0]"     # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["07-k8s_cluster_init.yaml"]="dci_mgmt_k8s_control_plane[0]"            # 1台目のコントロールプレーンノードに対して実行     
PLAYBOOK_TARGETS["08-k8s_cluster_join_cp.yaml"]="dci_mgmt_k8s_control_plane[1:]"        # 2台目以降のコントロールプレーンノードに対して実行   
PLAYBOOK_TARGETS["09-k8s_cluster_join_wk.yaml"]="dci_mgmt_k8s_node"                     # ワーカーノードに対して実行

# 定義されたPlaybookを順番に実行（配列の順序を使用）
for playbook_name in "${PLAYBOOK_ORDER[@]}"; do
    # 各Playbookのターゲットグループに対して実行
    for group in ${PLAYBOOK_TARGETS[$playbook_name]}; do
        # 対象グループに実行可能なホストが存在するかチェック
        set +e
        HOST_LIST=$(ansible-playbook "${PLAYBOOKS_BASE_DIR}/${playbook_name}" -i "$INVENTORY" -l "$group" --list-hosts 2>&1 >/dev/null | grep "ERROR! ")
        set -e
        
        if [ -n "$HOST_LIST" ]; then
            echo "[WARN] ${playbook_name} の $group グループには実行可能なホストが定義されていないため、スキップします"
            continue
        fi
        
        echo "[INFO] ${playbook_name} を $group グループに対して実行します"
        set +e  # 一時的にset -eを無効化
        ansible-playbook "${PLAYBOOKS_BASE_DIR}/${playbook_name}" \
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
