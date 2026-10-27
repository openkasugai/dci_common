# manager_software_deploy/README.md

## 概要
このディレクトリは、構築済みのKubernetesクラスタに対して、DCI管理基盤に必要な各種ソフトウェアコンポーネントを配備するためのAnsibleスクリプト群です。

---

## ソース構成
```
manager_software_deploy/
├── README.md                                # 本ドキュメント
├── manager_software_deploy.sh               # メイン実行スクリプト
├── ansible/
│   ├── ansible.cfg                          # Ansible設定
│   ├── .vault_pass                          # Vaultパスワードファイル（git管理外）
│   ├── callback_plugins/
│   │   └── custom_logger.py                 # ログ出力用プラグイン
│   ├── inventory/
│   │   ├── hosts                            # インベントリ（ノード数可変）
│   │   └── group_vars/                      # グループ変数
│   │       ├── all/
│   │       │   ├── vars.yaml                # バージョン情報、環境設定等
│   │       │   └── vault.yaml               # 機密情報（マスク済みサンプル／平文）
│   │       └── dci_mgmt_k8s_control_plane/
│   │           ├── vars.yaml
│   │           └── vault.yaml
│   ├── logs/                                # 実行ログ（playbookごとにディレクトリ作成）
│   ├── utility/                             # ユーティリティスクリプト配置先
│   └── playbooks/                           # 各種Playbook（01〜28）
│       ├── 01-pre_setup_all_node.yaml
│       ├── 02-pre_setup_cp_only.yaml
│       ├── ...
│       ├── 27-dci_manager_backup_setup.yaml
│       └── 28-velero_cli_setup.yaml
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
1. **manager_cluster_setup** の使用の前提条件を満たしていて、 Kubernetes クラスタ構築が完了していること
2. クラスタが正常動作していること（`kubectl get nodes` で全ノードReady状態）
3. 外部NFSサーバが利用可能（DCI管理クラスタ用およびテナント論理インフラ用）
4. バックアップストレージ（Minio等）が利用可能

---

## 使用前準備

### 1. インベントリファイルの確認
manager_cluster_setupと同じインベントリファイルを使用します。
```bash
ansible/inventory/hosts
```

### 2. 管理DB登録用プログラムの配置
管理DB（PostgreSQL）にリソースプール情報を登録するためのGoプログラムを作成し、設定ファイルに絶対パスを記載します。

**配置先：**
```bash
/path/to/work/dci_common/script/support_tools/pre_setup_tools/configuration_management_database/main.go
```

**設定ファイル：**
```yaml
# ansible/inventory/group_vars/all/vars.yaml
db_init_file: "/path/to/work/dci_common/script/support_tools/pre_setup_tools/configuration_management_database/main.go"
```

### 3. バージョン設定の確認・変更
`ansible/inventory/group_vars/all/vars.yaml` で以下のバージョンを確認・必要に応じて変更：

**OSSコンポーネント：**
- Helm、Go、NFS Provisioner、cert-manager、Gateway API/Fabric
- Harbor、CloudNativePG、Cluster API、Prometheus、Loki、Vector
- Node Problem Detector、IPMI Exporter、Velero、Velero CLI、Temporal

**DCIコンポーネント：**
```yaml
# リポジトリバージョン（ブランチ/タグ）
dci_common_version: v1.0.0
dci_manager_version: v1.0.0
dci_physical_infrastructure_version: v1.0.0
dci_tenant_infrastructure_version: v1.0.0

# 各コンポーネントのイメージバージョン
tag_manager_version: 1.0.0
tag_physical_version: 1.0.0
tag_tenant_version: 1.0.0

# 再ビルドフラグ（資材更新時にtrue、不要時はfalse）
resource_pool_manager_rebuild: false
rpm_alert_receiver_rebuild: false
physical_infrastructure_rebuild: false
cluster_api_provider_dci_rebuild: false
# ... その他のコンポーネント
```

### 4. 環境固有設定の編集
`ansible/inventory/group_vars/all/vars.yaml` で以下を実環境に合わせて編集：

**拠点設定：**
```yaml
locations:
  - dc1  # 拠点名（複数指定可）
```

**MAASサーバ設定：**
```yaml
maas_server_ip: "192.0.2.10"
```

**DNSサーバ設定：**
```yaml
nameservers:
  - 8.8.8.8
  - 1.1.1.1
```

**NTPサーバ設定：**
```yaml
ntp_servers:
  - ntp.example.com
```

**NFSサーバ設定（DCI管理クラスタ用）：**
```yaml
nfs_server_ip: "203.0.113.1"
nfs_server_export_path: "/export/nfs"
```

**バックアップストレージ設定（DCI管理クラスタ用）：**
```yaml
velero_bucket: "minio/test-velero-bucket01"
velero_storage_ip: "192.0.2.30"
velero_storage_port: "9000"
velero_minio_user: "minio"
```

**Grafana ポートフォワード設定：**
```yaml
grafana_port_forward_enabled: true
grafana_port_forwards:
  - service: "svc/prometheus-grafana"
    src_port: 3000
    dest_port: 80
  - service: "svc/prometheus-b-grafana"
    src_port: 3001
    dest_port: 80
```

### 5. プロキシ設定の確認
プロキシ経由でインターネットに接続する環境の場合は `group_vars/all/vars.yaml` の以下の項目を設定
- `proxy_setup_enabled: true` に変更（デフォルト: `false`）
- `proxy_url` にプロキシURLを設定（例: `"http://192.168.1.1:8080/"`）
- プロキシが不要な環境では `proxy_setup_enabled: false` に設定

### 6. Vault機密情報の設定
`ansible/inventory/group_vars/all/vault.yaml` に以下の機密情報を設定：

- 初期状態では、パスワード項目は `*****` のマスク値で登録されています。
- 実運用時は、各環境の実値に置き換えてください。

- GitHubアクセストークン（リポジトリクローン用）
- RHELサブスクリプション情報（username、password）
- Minioパスワード（DCI管理クラスタ用）
- SMTPサーバ認証情報（監視アラート通知用、使用する場合）
- Harbor管理者パスワード
- IPMI Exporter用認証情報（使用する場合）

### 7. DCI関連リポジトリのアクセス確認
以下のリポジトリへのアクセス権限があることを確認：
- dci_common
- dci_manager
- dci_physical_infrastructure
- dci_tenant_infrastructure

### 8. Vault設定（機密情報の暗号化管理）

   本プロジェクトでは、Git にはマスク済み（平文）の `vault.yaml` を登録しています。利用時は環境に合わせて実値を設定し、Ansible Vault で暗号化してから実行してください。

   **対象ファイル:**
   - `ansible/inventory/group_vars/all/vault.yaml`
   - `ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vault.yaml`

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

   **c. 2ファイルをまとめて暗号化**
   ```bash
   ansible-vault encrypt \
     ansible/inventory/group_vars/*/vault.yaml \
     --vault-password-file ansible/.vault_pass
   ```

   **d. 暗号化ファイルを再編集する場合**
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
cd manager_software_deploy
bash ./manager_software_deploy.sh
```

### 2. Playbook実行順序
Playbookは以下の順で自動実行されます：

| #  | Playbook名                                      | 対象                          | 主な処理内容                                  |
|----|-------------------------------------------------|-------------------------------|-----------------------------------------------|
| 1  | 01-pre_setup_all_node.yaml                      | all                           | Go/yq/buildah等のツール導入、DHRCリポジトリクローン |
| 2  | 02-pre_setup_cp_only.yaml                       | CP                            | CP専用の事前セットアップ                      |
| 3  | 03-kubectl_confirmation_plugin_setup.yaml       | CP[0]                         | kubectl確認プラグイン設定                     |
| 4  | 04-etcd_encryption_prepare.yaml                 | CP[0]                         | etcd暗号化設定ファイル準備                    |
| 5  | 05-etcd_encryption_apply.yaml                   | CP                            | etcd暗号化の全CPへの適用                      |
| 6  | 06-etcd_encryption_reencrypt.yaml               | CP[0]                         | 既存Secretの再暗号化                          |
| 7  | 07-kube_apiserver_audit_setup.yaml              | CP                            | kube-apiserver監査ログ設定                    |
| 8  | 08-auditd_custom_rules_setup.yaml               | all                           | auditdカスタムルール設定                      |
| 9  | 09-kyverno_install.yaml                         | CP[0]                         | Kyvernoの配備とプロキシ設定ポリシーの作成     |
| 10 | 10-nfs_client_install.yaml                      | all                           | NFSクライアント導入                           |
| 11 | 11-nfs_subdir_external_provisioner_setup.yaml   | CP[0]                         | NFS動的Provisioner配備                        |
| 12 | 12-cert_manager_install.yaml                    | CP[0]                         | cert-manager配備                              |
| 13 | 13-nginx_gateway_fabric_apply.yaml              | CP[0]                         | Gateway API配備                               |
| 14 | 14-harbor_install.yaml                          | CP[0]                         | Harborインストール                            |
| 15 | 15-harbor_certificate_setup.yaml                | all                           | Harbor証明書認証設定（全ノード）              |
| 16 | 16-harbor_provisioning.yaml                     | CP[0]                         | Harborプロビジョニング                        |
| 17 | 17-monitoring_stack_apply.yaml                  | CP[0]                         | 監視スタック（Prometheus/Grafana/Loki等）配備 |
| 18 | 18-worker_rsyslog_setup.yaml                    | Worker[0]                     | workerノードrsyslog設定（ネットワークSWログ受信） |
| 19 | 19-monitoring_stack_vector_apply.yaml           | CP[0]                         | 監視スタック（Vector/NPD/IPMI Exporter等）配備 |
| 20 | 20-cnpg_postgresql_install.yaml                 | CP[0]                         | PostgreSQLクラスタ構築                        |
| 21 | 21-resource_pool_manager_deploy.yaml            | CP[0]                         | リソースプール管理配備                        |
| 22 | 22-postgrest_api_setup.yaml                     | CP[0]                         | PostgREST API設定                             |
| 23 | 23-physical_infrastructure_install.yaml         | CP[0]                         | 物理インフラ管理配備                          |
| 24 | 24-dci_capdci_build_apply.yaml                  | CP[0]                         | CAPDCI（Cluster API Provider）配備            |
| 25 | 25-cluster_api_install.yaml                     | CP[0]                         | Cluster API配備                               |
| 26 | 26-scale_controller_logicalserver_role_setup.yaml| CP[0]                        | Scaling Controller用Role設定                  |
| 27 | 27-dci_manager_backup_setup.yaml                | CP[0]                         | DCI管理クラスタバックアップ設定（Velero）     |
| 28 | 28-velero_cli_setup.yaml                        | CP                            | Velero CLIセットアップ                        |

### 配備されるコンポーネント一覧

| カテゴリ           | コンポーネント名                        | 説明                                          |
|--------------------|----------------------------------------|-----------------------------------------------|
| セキュリティ       | etcd暗号化                             | Secret情報の暗号化保存                        |
|                    | kube-apiserver監査ログ                 | API操作の監査記録                             |
|                    | auditdカスタムルール                   | サーバ操作の監査                              |
|                    | Kyverno                                | プロキシ設定ポリシーの管理（オプション）      |
| 開発環境・ツール   | Go言語                                 | コンポーネントビルド用                        |
|                    | yq                                     | YAML処理ツール                                |
|                    | kubectl確認プラグイン                  | 操作確認機能                                  |
| ストレージ         | NFSクライアント                        | 全ノードにnfs-utilsをインストール             |
|                    | NFS Subdir External Provisioner        | 動的PV作成                                    |
| 証明書管理         | cert-manager                           | TLS証明書の自動管理                           |
| ネットワーク       | nginx-gateway-fabric                   | Gateway API実装（Ingress制御）                |
| コンテナレジストリ | Harbor                                 | プライベートコンテナレジストリ                |
| データベース       | CloudNativePG (CNPG)                   | PostgreSQLクラスタ                            |
| DCI管理基盤        | Resource Pool Manager                  | リソースプール管理                            |
|                    | PostgREST API                          | PostgreSQL REST APIインターフェース           |
|                    | Physical Infrastructure                | 物理インフラ管理                              |
|                    | CAPDCI                                 | DCI用Cluster API Provider                     |
|                    | Cluster API                            | Kubernetesクラスタ管理基盤                    |
| 監視・ログ         | Prometheus/Grafana                     | メトリクス収集・可視化                        |
|                    | Loki                                   | ログ集約                                      |
|                    | Vector                                 | ログ収集エージェント（アプリケーション＋監査ログ）|
|                    | rsyslog                                | ネットワークSWログ受信・監査ログルーティング  |
|                    | Node Problem Detector                  | ノード異常検知                                |
|                    | IPMI Exporter                          | ハードウェアメトリクス収集                    |
| テナント向け機能   | Scaling Controller Role設定            | LogicalServerアクセス権限                     |
|                    | Veleroバックアップ                     | DCI管理クラスタ自体のバックアップ             |

---

### 3. ログ確認
実行ログは `ansible/logs/` 配下にタイムスタンプ付きディレクトリが作成され、各playbookごとに `playbook名.log` 形式で保存されます。
```bash
tail -f ansible/logs/YYYYMMDD_HHMMSS_manager_software_deploy/01-pre_setup_all_node.yaml.log
```

---

## 配備後の確認

### 1. 各コンポーネントの確認
```bash
# Pod状態確認
kubectl get pods -A

# Harbor確認
kubectl get pods -n harbor

# cert-manager確認
kubectl get pods -n cert-manager

# NFS Provisioner確認
kubectl get pods -n nfs-provisioner

# PostgreSQL確認
kubectl get pods -n database

# 監視スタック確認
kubectl get pods -n monitoring
```

### 2. サービスエンドポイント確認
```bash
# Gateway/Service確認
kubectl get gateway -A
kubectl get httproute -A

# Harbor UIアクセス
https://<kube_vip_address>/

# Grafanaアクセス（ポートフォワード経由）
# ポートフォワード用スクリプトが自動実行されます
```

### 3. ストレージ確認
```bash
# StorageClass確認
kubectl get storageclass

# PVC動作確認
kubectl create -f test-pvc.yaml  # テスト用PVC作成
kubectl get pvc
```

---

## トラブルシューティング
- **Playbook失敗時**：`ansible/logs/` のログを参照し、エラー内容を確認
- **Harbor証明書エラー**：全ノードでCA証明書更新が完了しているか確認（`update-ca-trust`）
- **Helm配備失敗**：Helmリポジトリの接続性確認、バージョン互換性確認
- **NFS接続エラー**：NFSサーバのアクセス権限・ネットワーク到達性を確認
- **監視アラート未送信**：SMTP設定の確認（`group_vars/all/vars.yaml`）

---

## 参考
- 主要な設定ファイル：
  - `ansible/inventory/hosts` … ノード一覧
  - `ansible/inventory/group_vars/all/vars.yaml` … 各種バージョン情報
  - `ansible/playbooks/*.yaml` … 各コンポーネントの配備定義
- このスクリプトは冪等性を持つため、実行中に失敗した場合でも再実行可能です。
---

