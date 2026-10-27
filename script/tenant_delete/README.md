# tenant_delete/README.md

## 概要
このディレクトリは、テナント論理インフラ削除から後作業まで、テナント解体処理を自動化するAnsibleスクリプト群です。

---

## ソース構成
```
tenant_delete/
├── README.md                                           # 本ドキュメント
├── NOTICE
├── tenant_delete.sh                                    # メイン実行スクリプト
└── ansible/
    ├── ansible.cfg                                     # Ansible設定
    ├── .vault_pass                                     # Vaultパスワードファイル（git管理外）
    ├── callback_plugins/
    │   └── custom_logger.py                            # ログ出力用プラグイン
    ├── inventory/
    │   ├── hosts                                       # インベントリ（DCI管理用クラスタ）
    │   └── group_vars/                                 # グループ変数
    │       ├── all/
    │       │   ├── vars.yaml                           # マネージャHarbor設定・共通変数
    │       │   └── vault.yaml                          # 機密情報（マスク済みサンプル／平文）
    │       └── dci_mgmt_k8s_control_plane/
    │           ├── vars.yaml                           # 削除対象テナント情報
    │           └── vault.yaml                          # テナントHarborパスワード（マスク済みサンプル／平文）
    ├── logs/                                           # 実行ログ（実行ごとにディレクトリ作成）
    └── playbooks/                                      # 各種Playbook（01〜06）
        ├── 01-tenant_logical_infra_delete.yaml
        ├── 02-cleanup_k8s_resources.yaml
        ├── 03-cleanup_certs_and_crio.yaml
        ├── 04-cleanup_coredns.yaml
        ├── 05-remove_firewall_rules_on_manager.yaml
        ├── 06-cleanup_harbor_replication.yaml
        ├── remove_corefile_hosts.sh                    # CoreDNSエントリ削除補助スクリプト
        └── roles/                                      # 配備用ロール
```

---

## 使用の前提条件
1. **tenant_provisioning** の使用の前提条件を満たしていて、テナントクラスタ構築を実施済みであること（構築完了・失敗途中を問わず使用可能）

---

## 使用前準備

### 1. インベントリファイルの編集

`ansible/inventory/hosts` で管理クラスタCPのIPアドレスとユーザ名を実環境に合わせて編集します。

`03-cleanup_certs_and_crio.yaml` は全CPに対して実行されます。

```ini
[dci_mgmt_k8s_control_plane]
mgr-cp-1 ansible_host=192.168.1.1 ansible_user=admin
mgr-cp-2 ansible_host=192.168.1.2 ansible_user=admin  # 管理クラスタ冗長化なし構成時は削除
mgr-cp-3 ansible_host=192.168.1.3 ansible_user=admin  # 管理クラスタ冗長化なし構成時は削除
```

### 2. 削除対象テナント情報の設定

`ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vars.yaml` の `tenants` リストを編集します。
複数テナントを一括削除する場合はリストにエントリを追加してください。

```yaml
tenants:
  - tenant_name: tenant-1                           # テナント用のクラスタ名
    tenant_namespace: tenant-1                      # テナント用のネームスペース
    kubeconfig_file: tenant-1.kubeconfig            # ※1 kubeconfigファイル名
    harbor_ca_file: harbor-tenant-1-ca.crt          # ※2 crtファイル名
    harbor_private_key_file: harbor-tenant-1-ca.key # ※3 keyファイル名
    tenant_harbor_url: 192.168.2.32                # テナント用HarborサーバIPアドレス
    tenant_harbor_port: 30003                       # テナント用Harborサーバポート
    tenant_harbor_user: "{{ tenant_1_harbor_user }}"
    tenant_harbor_password: "{{ tenant_1_harbor_password }}"
    gateway_loadbalancer_vip: 192.168.2.31         # CoreDNS静的エントリ照合用VIP
    tenant_cni_cidr: 192.168.20.0/24                # ※4 削除したテナント論理インフラのCNI用CIDR
```

- ※1) `~/dci_manager/others/tenant-infrastructure-management/resources/accounts/tenant-manager/` 配下に作成したkubeconfigファイル名
- ※2) `/etc/pki/ca-trust/source/anchors/` 配下にコピーしたcrtファイル名（例: `harbor-tenant-1-ca.crt`）
- ※3) `/etc/pki/CA/private/` 配下にコピーしたkeyファイル名（例: `harbor-tenant-1-ca.key`）
- ※4) テナント論理インフラのCNIに割り当てたCIDR（テナントデプロイ時に設定した値と一致させること）

### 3. マネージャ側VIP設定の確認
`ansible/inventory/group_vars/all/vars.yaml` で以下を確認・編集：

```yaml
manager_harbor_url: 192.168.2.30        # マネージャ用HarborサーバIPアドレス
manager_harbor_port: 30003               # マネージャ用Harborサーバポート
mgr_gateway_loadbalancer_vip: 192.168.2.31  # DCIManager側LoadBalancer VIP
                                             # 「事前準備(システム構築)シート」でgateway-lb.yamlに設定したVIPと同一値にすること
```

### 4. Harbor認証情報の設定
* 初期状態では、パスワード項目は ***** のマスク値で登録されています。
* 実運用時は、各環境の実値に置き換えてください。

`ansible/inventory/group_vars/all/vault.yaml` にマネージャHarbor認証情報を設定します。

```yaml
manager_harbor_user: admin
manager_harbor_password: "*****"
```

`ansible/inventory/group_vars/dci_mgmt_k8s_control_plane/vault.yaml` にテナントHarbor認証情報を設定します。
テナントを追加した場合は対応するエントリを追記してください。

```yaml
tenant_1_harbor_user: admin
tenant_1_harbor_password: "*****"
```

### 5. Vault設定（機密情報の暗号化管理）

   本プロジェクトでは、Git にはマスク済み（平文）の vault.yaml を登録しています。利用時は環境に合わせて実値を設定し、Ansible Vault で暗号化してから実行してください。

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
cd tenant_delete
bash ./tenant_delete.sh
```

### 2. Playbook実行順序
Playbookは以下の順で自動実行されます：

| #  | Playbook名                              | 対象グループ                          | 主な処理内容                                                        |
|----|-----------------------------------------|---------------------------------------|---------------------------------------------------------------------|
| 1  | 01-tenant_logical_infra_delete.yaml     | dci_mgmt_k8s_control_plane[0]         | テナント削除、削除完了待機（タイムアウト1800s）                      |
| 2  | 02-cleanup_k8s_resources.yaml           | dci_mgmt_k8s_control_plane[0]         | `cleanup_components.sh` 実行、ScrapeConfig/namespace/ファイル削除   |
| 3  | 03-cleanup_certs_and_crio.yaml          | all                                   | 証明書削除、`update-ca-trust extract`、CRI-O再起動                  |
| 4  | 04-cleanup_coredns.yaml                 | dci_mgmt_k8s_control_plane[0]         | CoreDNS ConfigMapからPrometheus静的エントリを削除                   |
| 5  | 05-remove_firewall_rules_on_manager.yaml | all                                   | テナントCNIのfirewalldルールをマネージャCPノードから削除             |
| 6  | 06-cleanup_harbor_replication.yaml      | dci_mgmt_k8s_control_plane[0]         | マネージャHarborのReplicationポリシー・Registryを削除（API経由）    |

> **注意**: MinIOのLoki/Veleroバケット削除は本スクリプトの対象外です。[`support_tools/minio_bucket_management`](../support_tools/minio_bucket_management/README.md) の `./minio_bucket_management.sh delete` を使って削除してください。

### 3. ログ確認
実行ログは `ansible/logs/` 配下にタイムスタンプ付きディレクトリが作成され、各playbookごとに `playbook名.log` 形式で保存されます。
```bash
tail -f ansible/logs/YYYYMMDD_HHMMSS_tenant_delete/01-tenant_logical_infra_delete.yaml.log
```

---

## 削除後の確認

### 1. テナントリソースの削除確認
```bash
# Cluster APIリソースの削除確認（Cluster、KubeadmControlPlane、MachineDeployment等が存在しないこと）
kubectl get cluster -A
kubectl get kubeadmcontrolplane -A
kubectl get machinedeployment -A

# テナント用ネームスペースの削除確認（対象ネームスペースが存在しないこと）
kubectl get namespace <tenant-namespace>
```

### 2. テナント論理インフラリソースの削除確認
```bash
# dcirpmネームスペース内のテナント論理インフラが削除されていることを確認
kubectl get tenantlogicalinfra -n dcirpm
# 例: spare-cluster（VMホスト用）、spare-node-cluster（予備ノード用）が存在しないことを確認
```

### 3. 管理クラスタ側リソースの削除確認
```bash
# ServiceAccount削除確認（sa-<tenant-name>ネームスペースが存在しないことを確認）
kubectl get namespace sa-<tenant-name>

# HTTPRoute削除確認（対象テナントのエントリが存在しないことを確認）
kubectl get httproute -A

# ScrapeConfig削除確認（対象テナントのエントリが存在しないことを確認）
kubectl get scrapeconfig -A
```

### 4. 証明書削除の確認
```bash
# 管理クラスタの全CPノードで、テナント証明書が削除されていることを確認
ls -la /etc/pki/ca-trust/source/anchors/
# 例: harbor-tenant-1-ca.crt が存在しないことを確認
```

### 5. CoreDNSエントリの削除確認
```bash
# CoreDNS ConfigMapからテナントのPrometheus静的エントリが削除されていることを確認
kubectl get configmap coredns -n kube-system -o yaml
# 例: 削除対象テナントのgateway_loadbalancer_vipに関するhostsエントリが存在しないことを確認
```

### 6. Harbor Replicationの削除確認
```bash
# Harbor管理画面（GUI）でReplicationポリシーおよびRegistryが削除されていることを確認
# https://<manager_harbor_url>/
# [Administration] > [Registries] … 対象テナントのRegistryが存在しないこと
# [Administration] > [Replications] … 対象テナントのReplicationルールが存在しないこと
```

### 7. firewalldルール削除の確認
```bash
# 管理クラスタの全CPノードで、テナントCNIのfirewalldルールが削除されていることを確認
sudo firewall-cmd --zone=k8s-node --list-sources
# 例: 削除対象テナントの tenant_cni_cidr が k8s-nodeゾーンのソースに存在しないことを確認
sudo firewall-cmd --direct --get-all-rules
# 例: 削除対象テナントの tenant_cni_cidr に関するdirectルールが存在しないことを確認
```
