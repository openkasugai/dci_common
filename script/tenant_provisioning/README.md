# tenant_provisioning/README.md

## 概要
このディレクトリは、構築済みのDCI管理クラスタ上で、テナント論理インフラの準備とプロビジョニングを行うためのAnsibleスクリプト群です。  
テナント用Kubernetesクラスタを構築する前の準備段階（ネームスペース作成、リソース準備、Harbor証明書設定、予備ノード作成等）を自動化します。

---

## ソース構成
```
tenant_provisioning/
├── README.md                                               # 本ドキュメント
├── tenant_provisioning.sh                                  # メイン実行スクリプト
├── ansible/
│   ├── ansible.cfg                                         # Ansible設定
│   ├── callback_plugins/
│   │   └── custom_logger.py                                # ログ出力用プラグイン
│   ├── inventory/
│   │   ├── hosts                                           # インベントリ（ノード数可変）
│   │   └── group_vars/                                     # グループ変数
│   │       └── all/
│   │           ├── vars.yaml                               # テナント情報、ネットワーク設定等
│   │           └── vault.yaml                              # 機密情報（マスク済みサンプル／平文）
│   ├── logs/                                               # 実行ログ（playbookごとにディレクトリ作成）
│   ├── utility/                                            # テナント構築yamlファイルなどの配置先（任意）
│   └── playbooks/                                          # 各種Playbook（01〜02）
│       ├── 01-tenant_logical_infra_components_prepare.yaml
│       ├── 02-tenant_logical_infra_provisioning.yaml
│       ├── edit_tenant_yaml_for_harbor.py                 # テナント構築yaml編集スクリプト
│       ├── roles/                                          # テナントセットアップロール
│       ├── vmhost-tli.j2                                   # VMホスト論理インフラテンプレート
│       ├── spare-tli.j2                                    # 予備ノード論理インフラテンプレート
│       └── spare-node.j2                                   # 予備ノードテンプレート
└── ...
```

---

## 構築対象マシン構成図

manager_cluster_setup で構築されたクラスタと同じ構成を使用します。
ノード数やIPアドレスは環境・インベントリ設定により可変です。以下は論理構成例です。

```
  +-------------------------------+
  |        VIP (kube-vip)         |
  +-------------------------------+
          |
  +-------+-------+-------+-------+
  |               |               |
+-----------+ +-----------+ +-----------+ 
|CP-1       | |CP-2       | |CP-3       | ...  ← コントロールプレーン（dci_mgmt_k8s_control_plane）
+-----------+ +-----------+ +-----------+
  |               |               |
  +-------+-------+-------+-------+
  |               |
+-----------+ +-----------+ 
|Worker-1   | |Worker-2   | ...  ← ワーカーノード（dci_mgmt_k8s_node）
+-----------+ +-----------+
```

※ 各ノードのホスト名や台数は `ansible/inventory/hosts` で設定します。

---

## 使用の前提条件
1. **manager_software_deploy** の使用の前提条件を満たしていて、以下のコンポーネント配備が完了していること
   - Harbor（コンテナレジストリ）
   - Resource Pool Manager（リソースプール管理）
   - Cluster API + CAPDCI（クラスタ管理基盤）
   - PostgreSQL + PostgREST API
   - Physical Infrastructure（物理インフラ管理）
   - cert-manager、NFS Provisioner
   - 監視スタック（Prometheus/Grafana/Loki）

---

## 使用前準備

### 1. インベントリファイルの確認
manager_cluster_setupと同じインベントリファイルを使用します。
```bash
ansible/inventory/hosts
```

### 2. テナント構築YAMLファイルの準備
Cluster APIマニフェスト（Cluster、KubeadmControlPlane、MachineDeployment等）を作成し、任意の場所に配置します。`ansible/inventory/group_vars/all/vars.yaml` の `tenant_yaml_path` に絶対パスを記載して参照します。

**配置例（絶対パス）：**
```bash
/path/to/work/dci_common/script/support_tools/pre_setup_tools/dci-tenant-infra-chart/tenant-a.yaml
```

**設定ファイル：**
```yaml
# ansible/inventory/group_vars/all/vars.yaml
tenant_yaml_path: "/path/to/work/dci_common/script/support_tools/pre_setup_tools/dci-tenant-infra-chart/tenant-a.yaml"
```

### 3. テナント情報の設定
`ansible/inventory/group_vars/all/vars.yaml` で以下を編集：

**tenants リスト：**
```yaml
tenants:
  - tenant_name: tenant-1
    tenant_namespace: tenant-1
    tenant_yaml_file: tenant-1.yaml
    tenant_yaml_path: "/path/to/work/dci_common/script/support_tools/pre_setup_tools/dci-tenant-infra-chart/tenant-a.yaml"
    tenant_harbor_url: 192.168.2.32
    tenant_harbor_port: 30003
    harbor_private_key_file: tenant-1.key
    harbor_ca_file: tenant-1.crt
    harbor_ca_name: tenant-1
    harbor_ca_expiration: 3650
    nfs_server_ip: "192.168.2.105"
    nfs_server_export_path: "/export/nfs"
    velero_bucket: "minio/test-velero-bucket01"
    velero_storage_ip: "192.168.2.105"
    velero_storage_port: "9000"
    velero_minio_user: "minio"
    velero_minio_password: "{{ tenant_1_velero_minio_password }}"
    disable_machine_health_check: false
    disable_kyverno_proxy_settings: false
    loki_storage_ip: "192.168.2.105"
    loki_storage_port: "9000"
    loki_storage_minio_user: "minio"
    loki_storage_minio_password: "{{ tenant_1_loki_storage_minio_password }}"
    loki_storage_bucket_chunks: "loki-tenant-1"
    loki_storage_bucket_ruler:  "loki-tenant-1-ruler"
    loki_storage_bucket_admin:  "loki-tenant-1-admin"
    # 複数テナントに対応する場合はリストに追加
```

### 4. ネットワーク設定の確認・編集
`ansible/inventory/group_vars/all/vars.yaml` で以下を確認・編集：

**マネージャーネットワーク設定：**
```yaml
manager_nw:
  cidr: 198.51.100.64/26
  ip_range:
    start: 198.51.100.70
    end: 198.51.100.78
  vid: 1193
```

**テナントCNIネットワーク設定（テナント構築yamlと一致させる）：**
```yaml
cni_nw:
  cidr: 198.51.100.128/26
  ip_range:
    start: 198.51.100.130
    end: 198.51.100.190
  vid: 1166
```

**テナントホストネットワーク設定（テナント構築yamlと一致させる）：**
```yaml
host_nw:
  cidr: 198.51.100.192/26
  ip_range:
    start: 198.51.100.194
    end: 198.51.100.250
  vid: 1163
```

⚠️ **重要**: `cni_nw` と `host_nw` は、`tenant_yaml_path` で指定したテナント構築yamlファイル内のネットワーク設定と完全に一致させる必要があります。不一致の場合、テナントクラスタのネットワークが正常に機能しません。

### 5. 予備ノード情報の設定
`ansible/inventory/group_vars/all/vars.yaml` の `spare_nodes` リストで以下を設定：

```yaml
spare_nodes:
# 対象の接続先がない場合は、項目ごと削除し、spare_nodes: []とする。
  - node_name: spare-node01            # 予備ノード名
    node_yaml_file: spare-node01.yaml  # 予備ノードマニフェストファイル名
    location: dc1                      # 所属する拠点名
    server_type: COTSServer            # サーバタイプ(ComposedServer/COTSServer/VM/ComposedServerOrCOTSServer)
    os:                                # OS情報(MAASに登録済みカスタムイメージ)
      distribution: rhel               # ディストリビューション
      version: 9.6-custom              # バージョン
    gpu:                               # GPU情報
      model: NVIDIA-BLACKWELL          # GPUモデル
      num: 1                           # GPU搭載数
    nic:                               # NIC情報
      model: NVIDIA-CONNECTX-6-DX      # NICモデル
      num: 1                           # NIC搭載数
  # 追加の予備ノードがあればリストに追加
```

### 6. Vault設定（機密情報の暗号化管理）

本プロジェクトでは、Git にはマスク済み（平文）の `vault.yaml` を登録しています。利用時は環境に合わせて実値を設定し、Ansible Vault で暗号化してから実行してください。

**対象ファイル:**
- `ansible/inventory/group_vars/all/vault.yaml`

**事前編集:**
- 初期状態では、パスワード項目は `*****` のマスク値で登録されています。
- 実運用時は、各環境の実値に置き換えてください。

**a. Vaultパスワードファイルの準備**
```bash
# .vault_pass ファイルを作成（利用者自身でパスワードを決める）
echo "YOUR_VAULT_PASSWORD" > ansible/.vault_pass
chmod 600 ansible/.vault_pass
```

**b. 利用開始時の手順（編集→暗号化）**
```bash
# 1. 平文のマスク値を環境実値に編集
vi ansible/inventory/group_vars/all/vault.yaml

# 2. 暗号化
ansible-vault encrypt ansible/inventory/group_vars/all/vault.yaml \
  --vault-password-file ansible/.vault_pass
```

**c. 暗号化ファイルを再編集する場合**
```bash
ansible-vault edit ansible/inventory/group_vars/all/vault.yaml \
  --vault-password-file ansible/.vault_pass
```

**セキュリティ上の注意:**
- マスク値 `*****` のままでは正常動作しないため、必ず実値に変更してから暗号化する
- 暗号化後の `vault.yaml` を Git にコミットしない
- `.vault_pass` のパーミッションは600に設定
- `.vault_pass` は `.gitignore` に登録済み（コミット防止）

---

## 使用方法

### 1. スクリプト実行
```bash
cd tenant_provisioning
bash ./tenant_provisioning.sh
```

### 2. Playbook実行順序
Playbookは以下の順で自動実行されます：

| #  | Playbook名                                      | 対象グループ                | 主な処理内容                                  |
|----|-------------------------------------------------|-------------------------------|-----------------------------------------------|
| 1  | 01-tenant_logical_infra_components_prepare.yaml | dci_mgmt_k8s_control_plane[0] | テナント論理インフラコンポーネント準備        |
| 2  | 02-tenant_logical_infra_provisioning.yaml       | dci_mgmt_k8s_control_plane[0] | テナント論理インフラプロビジョニング          |

### Playbook詳細

#### **01-tenant_logical_infra_components_prepare.yaml**
テナントごとに以下の処理を実行：
- **ネームスペース作成**: テナント専用のネームスペース（例: `tenant-1`）
- **テナント構築用リソース作成**: make-components-configuration.sh でテナント固有の設定ファイル生成・適用
- **Scale Controller用認証設定**: management-api-kubeconfig Secret作成（テナントクラスタからマネージャクラスタへのアクセス用）
- **Harbor証明書準備**: 秘密鍵・自己署名CA証明書生成、システム信頼ストアへの追加、CRIOサービス再起動
- **テナント構築YAML編集**: Harbor CA証明書をKubeadmControlPlane/KubeadmConfigTemplateに注入

全体の処理：
- **VMホスト論理インフラ作成**: vmhost-tli.yaml 生成（dcirpm/spare-cluster）
- **予備ノード論理インフラ作成**: spare-tli.yaml 生成（dcirpm/spare-node-cluster）
- **予備ノード作成**: 各予備ノードのLogicalServerリソース生成・適用

#### **02-tenant_logical_infra_provisioning.yaml**
- 編集済みのテナント構築YAML（Cluster APIマニフェスト）を適用
- Cluster APIがテナントKubernetesクラスタの構築を開始

### 3. ログ確認
実行ログは `ansible/logs/` 配下にタイムスタンプ付きディレクトリが作成され、各playbookごとに `playbook名.log` 形式で保存されます。
```bash
tail -f ansible/logs/YYYYMMDD_HHMMSS_tenant_provisioning/01-tenant_logical_infra_components_prepare.yaml.log
```

---

## 構築後の確認

### 1. ネームスペースの確認
```bash
kubectl get namespaces
# 例: テナント用ネームスペース（tenant-1等）が作成されていることを確認
```

### 2. テナント論理インフラリソースの確認
```bash
kubectl get tenantlogicalinfra -n dcirpm
# 例: spare-cluster（VMホスト用）、spare-node-cluster（予備ノード用）が存在することを確認
```

### 3. 予備ノードの確認
```bash
kubectl get logicalserver -n dcirpm
# 例: 設定した予備ノード（spare-node01等）が作成されていることを確認
```

### 4. Secretの確認
```bash
kubectl get secret -n <tenant-namespace>
# 例: scale-controller-for-<tenant-name>-secret、management-api-kubeconfig-for-<tenant-name> が存在することを確認
```

### 5. 証明書の確認
```bash
ls -la /etc/pki/ca-trust/source/anchors/
cat /etc/pki/ca-trust/source/anchors/<tenant-name>.crt
# 例: Harbor CA証明書が配置されていることを確認
```

### 6. Cluster APIリソースの確認
```bash
kubectl get cluster -A
kubectl get kubeadmcontrolplane -A
kubectl get machinedeployment -A
# 例: テナントクラスタのリソースが作成され、Provisioningが進行していることを確認
```

---

## トラブルシューティング
- **Playbook失敗時**：`ansible/logs/` のログを参照し、エラー内容を確認
- **ネットワーク設定の不一致**：`cni_nw` と `host_nw` がテナント構築yamlファイルと一致しているか確認
- **Harbor証明書エラー**：CA証明書が `/etc/pki/ca-trust/source/anchors/` に配置され、`update-ca-trust` が実行されているか確認
- **Cluster APIリソース未作成**：テナント構築yamlファイルの構文が正しいか確認、Cluster APIコントローラのログを確認（`kubectl logs -n capi-system deployment/capi-controller-manager`）
- **予備ノード作成失敗**：`spare_nodes` リストの設定値（サーバタイプ、OS、GPU/NIC要件等）が正しいか確認
- **dcirpmネームスペース未作成**：manager_software_deploy（Resource Pool Manager配備）が完了しているか確認

---

## 参考
- 主要な設定ファイル：
  - `ansible/inventory/hosts` … ノード一覧
  - `ansible/inventory/group_vars/all/vars.yaml` … テナント情報、ネットワーク設定、予備ノード情報
  - `ansible/inventory/group_vars/all/vault.yaml` … テナント機密情報（暗号化対象）
  - `tenant_yaml_path` で指定したファイル … テナント構築用Cluster APIマニフェスト
- このスクリプトは冪等性を持つため、実行中に失敗した場合でも再実行可能です。
- **次のステップ**: tenant_provisioning完了後、`tenant_deploy` を実行してテナントクラスタへのコンポーネント配備を行います。
- **ネットワーク設定の重要性**: `cni_nw` と `host_nw` は、`tenant_yaml_path` で指定したテナント構築yamlファイル内のネットワーク設定と完全に一致させる必要があります。不一致の場合、テナントクラスタのネットワークが正常に機能しません。
- **複数テナント対応**: `tenants` リストに複数エントリを追加することで、複数テナントの一括プロビジョニングが可能です。各テナントは独立したネームスペースとリソースを持ちます。

---
