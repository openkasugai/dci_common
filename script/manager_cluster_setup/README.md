# manager_cluster_setup/README.md

## 概要
このディレクトリは、DHRC (Dynamic Hardware Resource Control) 管理用の高可用性KubernetesクラスタをAnsibleで自動構築するためのスクリプト群です。  
コントロールプレーン・ワーカーノードの台数はインベントリ設定で変更可能です。kube-vipによる仮想IPを用いたHA構成、CRI-Oコンテナランタイム、Calicoネットワークを採用しています。

---

## ソース構成
```
manager_cluster_setup/
├── README.md                           # 本ドキュメント
├── manager_cluster_setup.sh            # メイン実行スクリプト
├── ansible/
│   ├── ansible.cfg                     # Ansible設定
│   ├── callback_plugins/
│   │   └── custom_logger.py            # ログ出力用プラグイン
│   ├── inventory/
│   │   ├── hosts                       # インベントリ（ノード数可変）
│   │   ├── group_vars/                 # グループ変数
│   │   │   ├── all/
│   │   │   │   └── vars.yaml           # バージョン情報等
│   │   │   └── dci_mgmt_k8s_control_plane/
│   │   │       └── vars.yaml
│   │   └── host_vars/                  # ホスト変数
│   │       └── <ホスト名>/
│   │           └── vars.yaml
│   ├── logs/                           # 実行ログ
│   └── playbooks/                      # 各種Playbook（01〜09）
│       ├── 01-pre_setup_proxy.yaml
│       ├── 02-k8s_install.yaml
│       ├── 03-crio_install.yaml
│       ├── 04-crio_config.yaml
│       ├── 05-k8s_cluster_pre_setup_1.yaml
│       ├── 06-k8s_cluster_pre_setup_2.yaml
│       ├── 07-k8s_cluster_init.yaml
│       ├── 08-k8s_cluster_join_cp.yaml
│       ├── 09-k8s_cluster_join_wk.yaml
│       ├── kube-vip.yaml.j2
│       └── kubeadm-config.yaml.j2
└── ...
```

---

## 構築対象マシン構成図

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
1. 制御ノードにAnsible 2.14.18以上がインストール済み
    ```bash
    # インストール確認
    $ ansible --version
    ```
2. 制御ノードから対象とする全Kubernetesノードに対しSSH接続（ユーザー名はインベントリ設定による）が可能であり、SSH鍵認証が設定済み
    ```bash
    # パスワードなしでの接続確認
    $ ssh <ansible_user>@<ansible_host>
    ```
3. 制御ノードおよび全Kubernetesノードにて、sudoをパスワードなしで実行できる権限が設定済みであること
    ```bash
    $ sudo visudo
    # 以下の行のコメント（#）を外す
    %wheel        ALL=(ALL)       NOPASSWD: ALL
    ```
4. RHEL/CentOS系のOSが全ノードにインストール済み
    ```bash
    # インストール確認
    $ cat /etc/os-release
    ```
5. RHELのサブスクリプションが登録済みであること
    ```bash
    # サブスクリプション登録確認
    $ sudo subscription-manager status
    ```
6. 全Kubernetesノードにて、firewalldが無効化（停止・自動起動無効）されていること
    ```bash
    # 状態確認
    $ sudo systemctl status firewalld
    # Loaded行に "disabled"、Active行に "inactive (dead)" と表示されていることを確認
    ```
    ※ firewalldが有効な場合は、以下のコマンドで無効化してください。
    ```bash
    $ sudo systemctl disable firewalld
    $ sudo systemctl stop firewalld
    ```
---

## 使用前準備
1. **インベントリファイルの編集**
    インベントリファイル（`ansible/inventory/hosts`）のIPアドレスおよびホスト名を実環境に合わせて編集

2. **バージョン設定の確認**
    `group_vars/all/vars.yaml` で、Kubernetes、CRI-O、Calicoなどのバージョンを必要に応じて変更

3. **プロキシ設定の確認**
    プロキシ経由でインターネットに接続する環境の場合は `group_vars/all/vars.yaml` の以下の項目を設定
    - `proxy_setup_enabled: true` に変更（デフォルト: `false`）
    - `proxy_url` にプロキシURLを設定（例: `"http://192.168.1.1:8080/"`）
    - プロキシが不要な環境では `proxy_setup_enabled: false` に設定

4. **ネットワーク設定の調整**
    `group_vars/dci_mgmt_k8s_control_plane/vars.yaml` で、VIPやPod/Service CIDRなどのネットワーク関連の設定を調整

5. **ホスト固有設定の編集**
    `host_vars/` 配下（例: `host_vars/node1/vars.yaml`）で各ノードのCNIアドレスを設定

6. **SSH鍵配布**
    制御ノードから対象とする全Kubernetesノードに対し、SSH公開鍵が配布済みであることを確認

---

## 使用方法

### 1. スクリプト実行
```bash
cd manager_cluster_setup
bash ./manager_cluster_setup.sh
```

### 2. Playbook実行順序
Playbookは以下の順で自動実行されます：

| #  | Playbook名                       | 対象グループ                 | 主な処理内容                       |
|----|-----------------------------------|------------------------------|------------------------------------|
| 1  | 01-pre_setup_proxy.yaml           | all                          | プロキシ事前設定（dnf.conf/CRI-O） |
| 2  | 02-k8s_install.yaml               | all                          | K8sパッケージ導入                  |
| 3  | 03-crio_install.yaml              | all                          | CRI-O導入                          |
| 4  | 04-crio_config.yaml               | all                          | CRI-O設定                          |
| 5  | 05-k8s_cluster_pre_setup_1.yaml   | all                          | 基本OS/ネットワーク設定            |
| 6  | 06-k8s_cluster_pre_setup_2.yaml   | dci_mgmt_k8s_control_plane[0]| Calico等ネットワーク前準備         |
| 7  | 07-k8s_cluster_init.yaml          | dci_mgmt_k8s_control_plane[0]| クラスタ初期化（kubeadm init）     |
| 8  | 08-k8s_cluster_join_cp.yaml       | dci_mgmt_k8s_control_plane[1:]| 追加CPノードのクラスタ参加        |
| 9  | 09-k8s_cluster_join_wk.yaml       | dci_mgmt_k8s_node            | ワーカーノードのクラスタ参加       |

### 3. ログ確認
実行ログは `ansible/logs/` 配下にタイムスタンプ付きディレクトリが作成され、各playbookごとに `playbook名.log` 形式で保存されます。
```bash
tail -f ansible/logs/YYYYMMDD_HHMMSS_manager_cluster_setup/02-k8s_install.yaml.log
```

---

## 構築後の確認

### 1. ノードの状態確認
```bash
kubectl get nodes
# 例: すべてのノードが 'Ready' 状態であることを確認
```

### 2. システムPodの確認
```bash
kubectl get pods -A
# 例: kube-systemやcalico-system内のPodがすべて 'Running' 状態であることを確認
```

### 3. クラスタ情報の確認
```bash
kubectl cluster-info
# 例: Kubernetes control planeとCoreDNSが正常に動作していることを確認
```

### 4. VIPの疎通確認
```bash
curl -k https://192.0.2.30:6443/version
# 例: APIサーバーのバージョン情報がJSON形式で返されることを確認
```

### 5. CRI-Oの動作確認（任意のノードで実行）
```bash
sudo systemctl status crio
sudo crictl ps
# 例: CRI-Oサービスが 'active (running)' 状態であることを確認
```

---

## トラブルシューティング
- **Playbook失敗時**：`ansible/logs/` のログを参照し、エラー内容を確認
- **SSH接続不可**：インベントリや鍵設定を再確認
- **VIPやPodネットワークの競合**：CIDRやインターフェース設定を見直し

---

## 参考
- 主要な設定ファイル：
  - `inventory/hosts` … ノード一覧
  - `inventory/group_vars/all/vars.yaml` … 各種バージョン情報
  - `group_vars/dci_mgmt_k8s_control_plane/vars.yaml` … VIPやネットワーク
  - `host_vars/各ノード/vars.yaml` … CNIアドレス
- このスクリプトは冪等性を持つため、実行中に失敗した場合でも再実行可能です。
---

