# インフラ情報自動収集ツール

## 概要

本ディレクトリは、DHRC (Dynamic Hardware Resource Control) の構成管理DB登録コード生成ツール（`configuration_management_database/`）が必要とする `config.yaml` を自動生成するための補助ツールです。

MAASでコミッションを実行し、サーバのハードウェア情報（スペック・NIC・GPU）およびCDI機器のリソース情報を収集します。収集した情報をもとに `config.yaml` を自動生成します。

**全体の流れ:**

```
nodes.csv      switch.csv      cdi.csv
（ノード情報）  （スイッチ情報）  （CDI接続情報）
      └──────────────┬──────────────┘
                     ↓ ./make_all.sh
               result.csv（MAASから収集したノード情報）
               cdi.yaml（CDI機器から収集したリソース情報）
                     ↓
               config.yaml（構成管理DB登録コード生成ツールのインプット）
```

> **⚠ 注意:** 本ツールは **MAASサーバ上** で実行してください。

---

## ソース構成

```
data_collect_tools/
├── README.md              # 本ドキュメント
├── nodes.csv              # MAASノード情報（ユーザ編集対象）
├── switch.csv             # ネットワークスイッチ情報（ユーザ編集対象）
├── cdi.csv                # CDI機器接続情報（ユーザ編集対象）
├── make_all.sh            # メインスクリプト（以下のスクリプトを順に実行する）
├── maas_commission.sh     # nodes.csv を読み込んで MAAS コミッションするスクリプト
├── maas_info.sh           # コミッション済みノードから情報を取得するスクリプト
├── server.sh              # maas_info.sh から呼ばれる、サーバスペック情報を収集するスクリプト
├── port.sh                # maas_info.sh から呼ばれる、NIC情報を収集するスクリプト
├── gpu.sh                 # maas_info.sh から呼ばれる、GPU情報を収集するスクリプト
├── run_cdi.sh             # CDIクライアントPCから CDI リソース情報を自動取得するスクリプト
├── generate_cdi_yaml.sh   # run_cdi.sh から呼ばれる、CDI API から情報を取得して YAML 生成するスクリプト
├── fetch_cdi_yaml.sh      # run_cdi.sh から呼ばれる、CDIクライアントPC からリモートファイルを取得するスクリプト
└── make_config_yaml.sh    # 収集した情報をもとに config.yaml を生成するスクリプト
```

**生成物:**

| ファイル | 説明 |
|---------|------|
| `result.csv` | `maas_info.sh` の実行により生成される、MAASから収集したノード情報（サーバスペック・NIC・GPU） |
| `config.yaml` | `make_all.sh` の実行により生成される、構成管理DB登録コード生成ツール（`configuration_management_database/`）のインプットとなる YAML |

### 各ファイルの説明

| ファイル | 説明 |
|---------|------|
| `nodes.csv` | ユーザが編集するノード情報ファイル。MAASに登録するサーバのホスト名・MAC・IPMI情報・サーバタイプ等を記述する |
| `switch.csv` | ユーザが編集するスイッチ情報ファイル。ネットワークスイッチの名前・拠点・IPアドレス・対象ポート範囲・タイプ等を記述する |
| `cdi.csv` | ユーザが編集するCDI接続情報ファイル。CDIクライアントPCへの接続情報・CDI認証情報等を記述する |
| `make_all.sh` | メインスクリプト。`maas_commission.sh` → `maas_info.sh` → `run_cdi.sh` → `make_config_yaml.sh` の順に実行し、`config.yaml` を生成する |
| `maas_commission.sh` | `nodes.csv` を読み込み、MAASへのノード登録とコミッション（ハードウェア情報収集）を並列実行する。コミッションは各ノードに対して2回実行する |
| `maas_info.sh` | `server.sh`・`port.sh`・`gpu.sh` を順に実行して `result.csv` を生成する |
| `server.sh` | MAASのコミッション済みノードからサーバスペック情報（ベンダー・製品名・CPU・メモリ・ストレージ）を取得して `result.csv` に書き込む |
| `port.sh` | コミッション済みノードにSSH接続し、`lldpctl`・`lspci`・`ethtool` を使ってNIC情報（インターフェース名・MACアドレス・NICタイプ・接続スイッチ・ポート）を取得して `result.csv` に書き込む |
| `gpu.sh` | コミッション済みノードにSSH接続し、`lspci` を使ってGPU情報（PCI IDからモデルを判別）を取得して `result.csv` に書き込む |
| `run_cdi.sh` | `cdi.csv` を読み込み、`generate_cdi_yaml.sh` でCDI APIからリソース情報を取得後、`fetch_cdi_yaml.sh` でリモートファイルをローカルに取得して `cdi.yaml` を生成する |
| `generate_cdi_yaml.sh` | CDIクライアントPCにSSH接続し、`cdictl` コマンドでCDI APIからNIC・GPU・SSD情報を取得して YAML 形式に変換する |
| `fetch_cdi_yaml.sh` | CDIクライアントPCの `/tmp/cdi.yaml` を `scp` でローカルに取得して `cdi.yaml` に追記する |
| `make_config_yaml.sh` | `result.csv`・`nodes.csv`・`switch.csv` を読み込み、スイッチのポート範囲とNICのLLDP情報を照合してネットワーク役割（host/cni/app）を判定し、`config.yaml` の `nw_switch`・`nw_port`・`compute_pool` 等のセクションを生成する |

---

## 使用の前提条件

以下のコマンドが **MAASサーバ** にインストールされていること

| コマンド | 用途 | 確認方法 |
|---------|------|---------|
| `maas` | MAAS CLIによるノード操作 | `maas --version` |
| `jq` | MAASのJSON応答の解析 | `jq --version` |
| `sshpass` | CDIクライアントPCへのパスワード認証SSH | `sshpass -V` |

また、各コミッション済みノードには以下のコマンドがインストールされていること
（これらは MAAS のコミッション処理によって自動的にインストールされます。手動でのインストールは不要です。）

| コマンド | 用途 |
|---------|------|
| `lldpd` / `lldpctl` | NICの接続スイッチ・ポート情報の取得 |
| `lspci` | NIC・GPU のPCIデバイス情報の取得 |
| `ethtool` | NICドライバ情報の取得 |

---

## 使用前準備

### 1. MAASサーバの公開鍵をMAAS GUIに登録する

コミッション済みノードへの SSH 接続に使用するため、MAASサーバの公開鍵を MAAS GUI に登録します。

```bash
# MAASサーバ自身の鍵を生成
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
# 生成された ~/.ssh/id_ed25519.pub の内容を MAAS GUI で登録する
```

また、生成した公開鍵を `switch.csv` に記述した各スイッチに登録してください。

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub <ユーザ>@<接続先スイッチ>
```

### 2. CSVファイルの編集

3つの CSVファイルを環境に合わせて編集します。

#### 2-1. `nodes.csv`

MAASに登録するサーバ情報を記述します。

```
HOSTNAME,MAC,IPMI_ADDR,IPMI_USER,IPMI_PASS,SERVER_TYPE,SERVER_ROLE,DEPLOYMENT_TYPE
d1-m01-cots-worker01,00:11:22:33:44:55,172.28.160.59,user,xxxx,COTS,1,1
d1-m01-cots-compute01,00:11:22:33:44:56,172.28.160.203,user,xxxx,COMPUTE,,
```

| フィールド | 説明 |
|-----------|------|
| `HOSTNAME` | サーバのホスト名 |
| `MAC` | マネージャ用NICのMACアドレス |
| `IPMI_ADDR` | BMC（IPMI）のIPアドレス |
| `IPMI_USER` | BMC（IPMI）のユーザ名 |
| `IPMI_PASS` | BMC（IPMI）のパスワード |
| `SERVER_TYPE` | サーバの種別。`COTS` または `COMPUTE` を指定する。 `COMPUTE`のサーバの場合は、CDIコマンド(例: `cdictl machine create -f 1 -g group0 -m machineXX -r pcpu0,ssd0`)で事前に論理サーバを作成しておくこと。 |
| `SERVER_ROLE` | `SERVER_TYPE` が `COTS` の場合に指定。`0`：K8S ControlPlane、`1`：K8S Node。`COMPUTE` の場合は省略可 |
| `DEPLOYMENT_TYPE` | `SERVER_TYPE` が `COTS` の場合に指定。`0`：VMホスト、`1`：ベアメタル。`COMPUTE` の場合は省略可 |

#### 2-2. `switch.csv`

ネットワークスイッチ情報を記述します。スイッチに接続されるポート範囲とネットワーク役割（TYPE）を定義します。

```
NW_SWITCH_NAME,LOCATION,NW_IP_ADDR,NW_USER,VENDOR,PRODUCT_NAME,OS,PORT_START,PORT_END,TYPE
d1-m01-l2-switch-host01,loc1.location,192.168.2.10,sw-user,edgecore networks,DCS208/AS5812-54X,Edgecore SONiC,Ethernet0,Ethernet32,host
d1-m01-l3-l2-switch-cni01,loc1.location,192.168.2.11,sw-user,edgecore networks,DCS208/AS5812-54X,Edgecore SONiC,Ethernet0,Ethernet32,cni
d1-m01-l2-switch-app01,loc2.location,192.168.2.12,sw-user,edgecore networks,DCS208/AS5812-54X,Edgecore SONiC,Ethernet0,Ethernet32,app
```

| フィールド | 説明 |
|-----------|------|
| `NW_SWITCH_NAME` | スイッチの識別名。スイッチのホスト名(`hostname`)を指定する |
| `LOCATION` | 拠点識別子。`loc1.location`、`loc2.location` のように `locX.location` 形式で指定する |
| `NW_IP_ADDR` | スイッチのIPアドレス |
| `NW_USER` | スイッチへのアクセスユーザ名 |
| `VENDOR` | スイッチのベンダー名 |
| `PRODUCT_NAME` | スイッチの製品名 |
| `OS` | スイッチのNOS（ネットワークOS）名 |
| `PORT_START` | このTYPEに該当するポート範囲の開始ポート名（例: `Ethernet0`） |
| `PORT_END` | このTYPEに該当するポート範囲の終了ポート名（例: `Ethernet32`） |
| `TYPE` | ネットワーク役割。`host`・`cni`・`app` のいずれかを指定する |

> **⚠ 注意:** `PORT_START`・`PORT_END` のポート番号と、各ノードの LLDP 情報から取得されるポート番号が照合されて、NICのネットワーク役割（`host_mac`・`cni_mac`・apldata `mac`）が自動的に判別されます。ポート番号の範囲が正しく設定されていないと、`config.yaml` の生成が失敗します。

#### 2-3. `cdi.csv`

CDI機器の接続情報を記述します。CDI機器を使用しない場合は、このファイルを空にしてください。

```
HOST,USER,PASS,LOCATION,CDI_VERSION,GROUP_NAME,CDI_GUEST,CDI_USER,CDI_PASSWORD,CDIMGR_GUEST_USER,CDIMGR_GUEST_PASSWORD,CDIMGR_HOST,CDIMGR_HOST_USER,CDIMGR_HOST_PASSWORD,DIRECTOR_PASSWORD,PCIE_BOX_IP
172.28.161.199,ubuntu,xxxx,dc1,2.0,group0,172.20.30.150,dhrcsystem,yyyy,fujitsu,aaaa,1.1.1.1,fujitsu,bbbb,cccc,172.20.30.160
```

| フィールド | 説明 |
|-----------|------|
| `HOST` | CDI管理サーバ（クライアントPC）のIPアドレス |
| `USER` | CDI管理サーバ（クライアントPC）のSSHユーザ名 |
| `PASS` | CDI管理サーバ（クライアントPC）のSSHパスワード |
| `LOCATION` | CDIが属する拠点名（`location` リストの値と一致させる。例: `dc1`） |
| `CDI_VERSION` | CDIのバージョン。`product_info.version` に設定される（例: `2.0`） |
| `GROUP_NAME` | CDIのグループ名 |
| `CDI_GUEST` | CDI管理ソフト（ゲスト）の接続先IPアドレス |
| `CDI_USER` | CDI管理ソフトのログインユーザ名（`cdictl auth login` 時の username） |
| `CDI_PASSWORD` | CDI管理ソフトのログインパスワード（`cdictl auth login` 時の password） |
| `CDIMGR_GUEST_USER` | CDI管理サーバ（ゲスト）のユーザ名 |
| `CDIMGR_GUEST_PASSWORD` | CDI管理サーバ（ゲスト）のパスワード |
| `CDIMGR_HOST` | CDI管理サーバ（ホスト）のIPアドレスまたはホスト名 |
| `CDIMGR_HOST_USER` | CDI管理サーバ（ホスト）のユーザ名 |
| `CDIMGR_HOST_PASSWORD` | CDI管理サーバ（ホスト）のパスワード |
| `DIRECTOR_PASSWORD` | Director のパスワード |
| `PCIE_BOX_IP` | PCIe BoxのIPアドレス |

---

## 使用方法

### 1. `make_all.sh` の実行

CSVファイルを編集後、メインスクリプトを実行します。

```bash
./make_all.sh
```

`maas_commission.sh` はノードごとにコミッションを並列で2回実行するため、完了まで **10分程度** かかります。

正常に完了すると `config.yaml` が生成されます。

```bash
# 実行例
$ ./make_all.sh
All nodes processed.
$ ls config.yaml
config.yaml
```

---

### 2. 生成物の確認

生成された `config.yaml` の内容を確認します。

```bash
cat config.yaml
```

`config.yaml` は、構成管理DB登録コード生成ツール（`configuration_management_database/`）の `config.yaml` として使用します。内容が正しいことを確認した後、`configuration_management_database/` の `config.yaml` に上書きしてください。

```bash
cp config.yaml ../../configuration_management_database/config.yaml
```

---

## 制限事項

本ツールが生成する `config.yaml` において、GPU の `uuid` はデータ収集スクリプトでは収集されないため、空欄で出力されます。
対象は `pcie_box.gpu[].uuid` および `cots_gpu[].uuid` の両方です。

`uuid` は `nvidia-smi` コマンドでのみ取得可能なため、手動で設定してください。もしくは、ユニークなダミーの文字列(例:`GPU-12345678-6e24-bc99-fd38-a02c368a5f1d`)を仮設定し、`nvidia-smi`を実行できるようになったタイミングで正しい`uuid`を確認して、構成管理DBを更新してください。

```yaml
pcie_box:
  gpu:
    - res_uuid: "123ac475-b3d4-4c44-ae56-f397a7c1926d"
      res_name: "gpu0"
      uuid: ""    # ← 空欄で出力される
      status: 0

cots_gpu:
  - worker: worker01
    uuid: ""    # ← 空欄で出力される
    model: "NVIDIA-H100-PCIE-80GB"
    status: 0
```
