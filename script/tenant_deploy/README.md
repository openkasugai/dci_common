# tenant_deploy/README.md

## 概要
このディレクトリは、構築済みのテナント用Kubernetesクラスタに対して、DCI管理基盤との連携設定および各種ソフトウェアコンポーネントを配備するためのAnsibleスクリプト群です。

---

## ソース構成
```
tenant_deploy/
├── README.md                                     # 本ドキュメント
├── tenant_deploy.sh                              # メイン実行スクリプト
├── ansible/
│   ├── ansible.cfg                               # Ansible設定
│   ├── .vault_pass                               # Vaultパスワードファイル（git管理外）
│   ├── callback_plugins/
│   │   └── custom_logger.py                      # ログ出力用プラグイン
│   ├── inventory/
│   │   ├── hosts                                 # インベントリ（管理CP + テナントCP/WK）
│   │   └── group_vars/                           # グループ変数
│   │       ├── all/
│   │       │   ├── vars.yaml                     # OSS バージョン情報、VIP設定
│   │       │   └── vault.yaml                    # 機密情報（マスク済みサンプル／平文）
│   │       └── dci_mgmt_k8s_control_plane/
│   │           ├── vars.yaml                     # tenants[] リスト（複数テナント対応）
│   │           └── vault.yaml                    # Harbor パスワード
│   ├── logs/                                     # 実行ログ（playbookごとにディレクトリ作成）
│   └── playbooks/                                # 各種Playbook（01〜06）
│       ├── 01-add_firewall_rules_on_manager.yaml
│       ├── 02-complete_check.yaml
│       ├── 03-restart_coreDNS_on_tenant.yaml
│       ├── 04-prep_of_components_on_manager.yaml
│       ├── 05-deploy_prep_on_manager.yaml
│       ├── 06-create_service_acount.yaml
│       ├── roles/                                # 配備用ロール
│       └── *.j2, *.sh, *.py                      # テンプレート・スクリプト
└── ...
```

---

## 構築対象マシン構成図

ノード数やIPアドレスは環境・インベントリ設定により可変です。以下は論理構成例です。

### 物理構成図
```
+---------------------------+
|  管理クラスタ              |
|  (Manager Cluster)        |
|  mgr-cp-1                 |
|  (Control Plane)          |
+---------------------------+
  |
  | （DCI管理経由での連携）
  |
  +-------------------------------+-----------------------+
  |                               |                       |
+---------------------------+ +-----------------+ +-----------------+
|  tenant-1-cp-1 (Primary)  | | tenant-1-cp-2   | | tenant-1-cp-3   |
|  (Control Plane)          | | (Control Plane) | | (Control Plane) |
+---------------------------+ +-----------------+ +-----------------+
  |                               |                       |
  +-------------------------------+-----------------------+
          |
  +---------------+---------------+
  |                               |
+---------------------------+ +----------------------------+
|  tenant-1-wk-1 (Worker)   | |  tenant-1-wk-2 (Worker)    |
+---------------------------+ +----------------------------+
```

### インベントリグループ構造

| グループ名 | 役割 | 包含するノード/グループ | 備考 |
|-----------|------|---------------------|------|
| **dci_mgmt_k8s_control_plane** | 管理クラスタのCP | mgr-cp-1 | 管理クラスタのControl Planeノード |
| **dci_tenants** | 全テナントを包含 | tenant_1 (将来的にtenant_2等も包含) | 複数テナント対応の親グループ |
| **tenant_1** | テナント1の全ノード | tenant_1_k8s_control_plane<br>tenant_1_k8s_node | テナント1を構成する全ノード |
| **tenant_1_k8s_control_plane** | テナント1のCP全台 | tenant-1-cp-1<br>tenant-1-cp-2<br>tenant-1-cp-3 | テナント1のControl Planeノード |
| **tenant_1_k8s_node** | テナント1のWorker全台 | tenant-1-wk-1<br>tenant-1-wk-2 | テナント1のWorkerノード |
| **dci_tenant_k8s_control_plane_primary** | 全テナントのプライマリCP | tenant-1-cp-1<br>(tenant-2-cp-1)※将来 | 各テナントのCP[0]を横断的に包含 |

**グループ階層構造：**
```
dci_tenants (全テナント包含グループ)
└── tenant_1 (テナント1)
    ├── tenant_1_k8s_control_plane (CP全台)
    │   ├── tenant-1-cp-1 ← dci_tenant_k8s_control_plane_primaryにも所属
    │   ├── tenant-1-cp-2
    │   └── tenant-1-cp-3
    └── tenant_1_k8s_node (Worker全台)
        ├── tenant-1-wk-1
        └── tenant-1-wk-2
```
※ 各ノードのホスト名や台数は `ansible/inventory/hosts` で設定します。


## 使用の前提条件
1. **tenant_provisioning** の使用の前提条件を満たしていて、テナントクラスタ構築が完了し、テナントクラスタが**Ready状態**であること（`kubectl get cluster -A` で確認）
   - ※ Ready状態でない場合、`02-complete_check.yaml` でエラーとなります

---

## 使用前準備

### 1. インベントリファイルの編集
`ansible/inventory/hosts` でテナントCP/WKノードのIPアドレスおよびホスト名を実環境に合わせて編集します。管理クラスタのCP-1も正しく設定されていることを確認してください。

### 2. テナント情報の設定
`ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vars.yaml` の `tenants[]` リストで以下を編集：

**テナント定義例：**
```yaml
tenants:
  - tenant_name: tenant-1
    tenant_namespace: tenant-1
    kubeconfig_file: tenant-1.kubeconfig
    sa_config_for_tenant: /home/{{ ansible_user }}/tenant-1_provided.kubeconfig
    gateway_loadbalancer_vip: 198.51.100.140  # テナントCNIネットワーク側の空きIPアドレス
    tenant_cni_cidr: 192.168.20.0/24          # 構築したテナント論理インフラのCNI用CIDR
    harbor_private_key_file: tenant-1.key
    harbor_ca_file: tenant-1.crt
    tenant_harbor_url: 192.168.1.1
    tenant_harbor_port: 30003
    tenant_harbor_user: "{{ tenant_1_harbor_user }}"      # vault.yamlで定義
    tenant_harbor_password: "{{ tenant_1_harbor_password }}"  # vault.yamlで定義
    alert_email: "changeme@example.com"
  # 複数テナント対応: リストにエントリを追加（自動的にループ処理されます）
```

**設定項目の説明：**
- `tenant_name`: テナント名（例: tenant-1）
- `tenant_namespace`: テナント用ネームスペース（例: tenant-1）
- `kubeconfig_file`: テナント用kubeconfigファイル名
- `sa_config_for_tenant`: テナント運用者に提供するkubeconfig配置パス
- `gateway_loadbalancer_vip`: Gateway LoadBalancer用VIP（テナントCNIネットワーク側の空きIPアドレス）
- `tenant_cni_cidr`: 構築したテナント論理インフラのCNI用CIDR（firewalldルール追加に使用）
- `harbor_private_key_file`: Harbor証明書用秘密鍵ファイル名
- `harbor_ca_file`: Harbor自己署名証明書ファイル名
- `tenant_harbor_url`: Harbor接続先IPアドレス
- `tenant_harbor_port`: Harbor接続先ポート
- `tenant_harbor_user`: Harborユーザー名（**vault.yamlで定義した変数を参照**）
- `tenant_harbor_password`: Harborパスワード（**vault.yamlで定義した変数を参照**）
- `alert_email`:アラート送信先E-Mailアドレス

**Harbor認証情報のvault設定：**

`ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vault.yaml` に以下を設定：

```yaml
# テナント1用Harbor認証情報
tenant_1_harbor_user: admin
tenant_1_harbor_password: "*****"

# テナント2用Harbor認証情報（複数テナントの場合）
# tenant_2_harbor_user: admin
# tenant_2_harbor_password: AnotherPassword
```

上記のvault変数を `vars.yaml` の `tenant_harbor_user` と `tenant_harbor_password` で参照することで、機密情報を安全に管理します。

### 3. マネージャ側VIP設定
`ansible/inventory/group_vars/all/vars.yaml` で以下を確認・編集：

```yaml
# manager_software_deployの変数と同一値にすること
manager_harbor_url: 192.168.2.30 # マネージャ用HarborサーバIPアドレス
manager_harbor_port: 30003        # マネージャ用Harborサーバポート
mgr_gateway_loadbalancer_vip: 10.244.10.100  # 管理クラスタCNIネットワーク側の空きIPアドレス
smtp_server: smtp.example.com # SMTPサーバーのIPアドレス
smtp_port: 25                 # SMTPサーバーのポート番号
```

### 4. OSSバージョン設定の確認
`ansible/inventory/group_vars/all/vars.yaml` で以下のバージョンを確認・必要に応じて変更：

```yaml
# Prometheus
prometheus_version_major: 81.2
prometheus_version_minor: 0
```

### 5. プロキシ設定の確認
プロキシ経由でインターネットに接続する環境の場合は `group_vars/all/vars.yaml` の以下の項目を設定
- `proxy_setup_enabled: true` に変更（デフォルト: `false`）
- `proxy_url` にプロキシURLを設定（例: `"http://192.168.1.1:8080/"`）
- プロキシが不要な環境では `proxy_setup_enabled: false` に設定

### 6. Vault機密情報の設定
`ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vault.yaml` に以下の機密情報を設定：

- 初期状態では、パスワード項目は `*****` のマスク値で登録されています。
- 実運用時は、各環境の実値に置き換えてください。

**Harbor認証情報（各テナント用）：**
```yaml
# テナント1用Harbor認証情報
tenant_1_harbor_user: admin
tenant_1_harbor_password: "*****"

# テナント2用Harbor認証情報（複数テナントの場合）
# tenant_2_harbor_user: admin
# tenant_2_harbor_password: AnotherPassword
```

これらの変数は、使用前準備の「2. テナント情報の設定」で `tenant_harbor_user` および `tenant_harbor_password` から参照されます。

**その他の機密情報：**
- テナント認証情報
- その他の機密パラメータ

### 7. Vault設定（機密情報の暗号化管理）

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
   vi ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vault.yaml

   # 2. 暗号化
   ansible-vault encrypt ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vault.yaml \
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
   ansible-vault edit ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vault.yaml \
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
cd tenant_deploy
bash ./tenant_deploy.sh
```

### 2. Playbook実行順序
Playbookは以下の順で自動実行されます：

| #  | Playbook名                                    | 対象グループ                          | 主な処理内容                                  |
|----|-----------------------------------------------|---------------------------------------|-----------------------------------------------|
| 1  | 01-add_firewall_rules_on_manager.yaml         | dci_mgmt_k8s_control_plane（全CP）    | DCIマネージャCP全台へのfirewalldルール追加（テナントCNI→kube-apiserver/LB VIP許可）|
| 2  | 02-complete_check.yaml                        | dci_tenants（全テナントノード）       | cloud-init完了確認                            |
| 3  | 03-restart_coreDNS_on_tenant.yaml             | dci_tenant_k8s_control_plane_primary  | テナント側CoreDNS再起動・rollout完了待機      |
| 4  | 04-prep_of_components_on_manager.yaml         | dci_mgmt_k8s_control_plane[0]         | Harbor証明書配置、クラスタラベル付与（複数テナント対応）|
| 5  | 05-deploy_prep_on_manager.yaml                | dci_mgmt_k8s_control_plane[0]         | Gateway LB設定、HTTPRoute作成、CoreDNS更新、Vector/Loki連携設定（vector・vector-audit）、Prometheus設定（複数テナント対応）|
| 6  | 06-create_service_acount.yaml                 | dci_mgmt_k8s_control_plane[0]         | ServiceAccount作成、テナント運用者用kubeconfig生成（複数テナント対応）|

### 配備されるコンポーネント一覧

| カテゴリ           | コンポーネント名                        | 説明                                          |
|--------------------|----------------------------------------|-----------------------------------------------|
| クラスタ初期化     | cloud-init完了確認                     | テナントノードの初期化完了確認                |
|                    | CoreDNS再起動                          | テナント側DNS設定の反映                       |
| セキュリティ       | Harbor証明書配置                       | テナントクラスタへのHarbor CA証明書配布       |
| ロギング           | kubelet verbosity設定                  | ワーカーノードのkubeletログ詳細化             |
| 監視・イベント処理 | Argo Events                            | イベント駆動型ワークフロー基盤（v2.4.20）     |
|                    | Vector設定                             | アプリケーションログ・監査ログ収集・転送（Loki連携）|
| ネットワーク       | Gateway LoadBalancer                   | テナント外部公開用VIP設定                     |
|                    | HTTPRoute                              | Prometheus endpoint公開                       |
|                    | CoreDNS更新                            | 管理クラスタからテナントPrometheusへの名前解決|
| アクセス制御       | ServiceAccount                         | テナント運用者用kubeconfig生成                |

### 3. ログ確認
実行ログは `ansible/logs/` 配下にタイムスタンプ付きディレクトリが作成され、各playbookごとに `playbook名.log` 形式で保存されます。
```bash
tail -f ansible/logs/YYYYMMDD_HHMMSS_tenant_deploy/02-complete_check.yaml.log
```

---

## 配備後の確認

### 1. テナントクラスタの確認
```bash
# テナント用kubeconfigでノード状態確認
kubectl --kubeconfig=ansible/tenant-1.kubeconfig get nodes

# Argo Events配備確認
kubectl --kubeconfig=ansible/tenant-1.kubeconfig get pods -n argo-events

# CoreDNS動作確認
kubectl --kubeconfig=ansible/tenant-1.kubeconfig get pods -n kube-system -l k8s-app=kube-dns
```

### 2. 管理クラスタ側の確認
```bash
# ServiceAccount作成確認
kubectl get sa -n sa-tenant-1

# Gateway LoadBalancer設定確認
kubectl get svc -A | grep gateway

# HTTPRoute設定確認
kubectl get httproute -A
```

### 3. 監視連携の確認
```bash
# CoreDNS更新確認（管理クラスタ側）
kubectl get configmap coredns -n kube-system -o yaml | grep -A 5 "hosts custom"

# Prometheus疎通確認（管理クラスタから）
curl http://<gateway_loadbalancer_vip>:<port>/metrics
```

### 4. テナント運用者用kubeconfigの確認
```bash
# 提供用kubeconfigファイルの確認
ls -la /home/$(whoami)/tenant-1_provided.kubeconfig

# テナント運用者として接続テスト
kubectl --kubeconfig=/home/$(whoami)/tenant-1_provided.kubeconfig get nodes
```

---

## トラブルシューティング
- **Playbook失敗時**：`ansible/logs/` のログを参照し、エラー内容を確認
- **cloud-init未完了エラー**：テナントノードで `cloud-init status` を実行し、完了まで待機
- **Harbor証明書エラー**：Harbor CA証明書が管理クラスタで正しく配置されているか確認（manager_software_deploy の14番プレイブック完了確認）
- **Argo Events配備失敗**：Helmリポジトリの接続性確認、バージョン互換性確認
- **Gateway LB VIP疎通不可**：`gateway_loadbalancer_vip` がテナントCNIネットワークの空きIPアドレスであることを確認
- **ServiceAccount作成失敗**：テナント用kubeconfigが正しく取得されているか確認（`ansible/tenant-1.kubeconfig` の存在確認）
- **複数テナント実行時のエラー**：`tenants[]` リストの各エントリで `tenant_name` と `tenant_namespace` が一意であることを確認

---

## 参考
- 主要な設定ファイル：
  - `ansible/inventory/hosts` … 管理CP + テナントCP/WKノード一覧
  - `ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vars.yaml` … tenants[] リスト（複数テナント定義）
  - `ansible/inventory/group_vars/all/vars.yaml` … OSSバージョン情報、マネージャー側VIP設定
  - `ansible/playbooks/*.yaml` … 各コンポーネントの配備定義
- このスクリプトは冪等性を持つため、実行中に失敗した場合でも再実行可能です。
- **次のステップ**: tenant_deploy完了後、テナント運用者に提供用kubeconfigを配布し、テナントクラスタの運用を開始します。
- **複数テナント対応**: `tenants[]` リストに複数エントリを追加することで、複数テナントの一括配備が可能です。各テナントは独立したネームスペースとServiceAccountを持ちます。
---
