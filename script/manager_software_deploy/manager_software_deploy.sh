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
    "01-pre_setup_all_node.yaml"
    "02-pre_setup_cp_only.yaml"
    "03-kubectl_confirmation_plugin_setup.yaml"
    "04-etcd_encryption_prepare.yaml"
    "05-etcd_encryption_apply.yaml"
    "06-etcd_encryption_reencrypt.yaml"
    "07-kube_apiserver_audit_setup.yaml"
    "08-auditd_custom_rules_setup.yaml"
    "09-kyverno_install.yaml"
    "10-nfs_client_install.yaml"
    "11-nfs_subdir_external_provisioner_setup.yaml"
    "12-cert_manager_install.yaml"
    "13-nginx_gateway_fabric_apply.yaml"
    "14-harbor_install.yaml"
    "15-harbor_certificate_setup.yaml"
    "16-harbor_provisioning.yaml"
    "17-monitoring_stack_apply.yaml"
    "18-worker_rsyslog_setup.yaml"
    "19-monitoring_stack_vector_apply.yaml"
    "20-cnpg_postgresql_install.yaml"
    "21-resource_pool_manager_deploy.yaml"
    "22-postgrest_api_setup.yaml"
    "23-physical_infrastructure_install.yaml"
    "24-dci_capdci_build_apply.yaml"
    "25-cluster_api_install.yaml"
    "26-scale_controller_logicalserver_role_setup.yaml"
    "27-dci_manager_backup_setup.yaml"
    "28-velero_cli_setup.yaml"
)

declare -A PLAYBOOK_TARGETS
PLAYBOOK_TARGETS["01-pre_setup_all_node.yaml"]="all"
PLAYBOOK_TARGETS["02-pre_setup_cp_only.yaml"]="dci_mgmt_k8s_control_plane"
PLAYBOOK_TARGETS["03-kubectl_confirmation_plugin_setup.yaml"]="dci_mgmt_k8s_control_plane[0]"     # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["04-etcd_encryption_prepare.yaml"]="dci_mgmt_k8s_control_plane[0]"               # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["05-etcd_encryption_apply.yaml"]="dci_mgmt_k8s_control_plane"
PLAYBOOK_TARGETS["06-etcd_encryption_reencrypt.yaml"]="dci_mgmt_k8s_control_plane[0]"             # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["07-kube_apiserver_audit_setup.yaml"]="dci_mgmt_k8s_control_plane"
PLAYBOOK_TARGETS["08-auditd_custom_rules_setup.yaml"]="all"
PLAYBOOK_TARGETS["09-kyverno_install.yaml"]="dci_mgmt_k8s_control_plane[0]"                       # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["10-nfs_client_install.yaml"]="all"
PLAYBOOK_TARGETS["11-nfs_subdir_external_provisioner_setup.yaml"]="dci_mgmt_k8s_control_plane[0]" # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["12-cert_manager_install.yaml"]="dci_mgmt_k8s_control_plane[0]"                  # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["13-nginx_gateway_fabric_apply.yaml"]="dci_mgmt_k8s_control_plane[0]"            # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["14-harbor_install.yaml"]="dci_mgmt_k8s_control_plane[0]"                        # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["15-harbor_certificate_setup.yaml"]="all"
PLAYBOOK_TARGETS["16-harbor_provisioning.yaml"]="dci_mgmt_k8s_control_plane[0]"                   # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["17-monitoring_stack_apply.yaml"]="dci_mgmt_k8s_control_plane[0]"                # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["18-worker_rsyslog_setup.yaml"]="dci_mgmt_k8s_node[0]"                           # 1台目のワーカーノードに対して実行
PLAYBOOK_TARGETS["19-monitoring_stack_vector_apply.yaml"]="dci_mgmt_k8s_control_plane[0]"         # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["20-cnpg_postgresql_install.yaml"]="dci_mgmt_k8s_control_plane[0]"               # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["21-resource_pool_manager_deploy.yaml"]="dci_mgmt_k8s_control_plane[0]"          # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["22-postgrest_api_setup.yaml"]="dci_mgmt_k8s_control_plane[0]"                   # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["23-physical_infrastructure_install.yaml"]="dci_mgmt_k8s_control_plane[0]"       # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["24-dci_capdci_build_apply.yaml"]="dci_mgmt_k8s_control_plane[0]"                # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["25-cluster_api_install.yaml"]="dci_mgmt_k8s_control_plane[0]"                   # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["26-scale_controller_logicalserver_role_setup.yaml"]="dci_mgmt_k8s_control_plane[0]" # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["27-dci_manager_backup_setup.yaml"]="dci_mgmt_k8s_control_plane[0]"              # 1台目のコントロールプレーンノードに対して実行
PLAYBOOK_TARGETS["28-velero_cli_setup.yaml"]="dci_mgmt_k8s_control_plane"

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
