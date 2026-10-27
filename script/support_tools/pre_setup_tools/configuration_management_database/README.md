# 構成管理DB登録コード生成ツール

## 概要

本ディレクトリは、DHRC (Dynamic Hardware Resource Control) の構成管理DB（PostgreSQL）へのリソースプール情報の初期登録に使用する Goコード（`main.go`）を生成するための補助ツールです。

ユーザが `config.yaml` に記述したインフラ設定（拠点・スイッチ・サーバ等）を読み込み、Goコードのひな形（`main_template.go`）を展開して `main.go` を自動生成します。

生成された `main.go` は、`init-mgmt-db`（`dci_manager/others/configuration-management-database/init-mgmt-db/`）に配置されるDB登録コードです。実際のDB登録は `init-mgmt-db/` 側で `make initdb` を実行することで行われます。

**全体の流れ:**

```
config.yaml                    main_template.go
（ユーザーが環境情報を記述）    （Goコードのひな形）
         └──────────┬──────────┘
                    ↓ go run main_tmp.go > main.go
              main.go（自動生成されたDB登録コード）
```

---

## ソース構成

```
configuration_management_database/
├── README.md           # 本ドキュメント
├── config.yaml         # インフラ設定ファイル（ユーザ編集対象）
├── main_template.go    # text/template 構文テンプレート（main.go の生成元）
├── main_tmp.go         # テンプレートエンジン（config.yaml × main_template.go → main.go）
├── go.mod              # Go モジュール定義
└── go.sum              # 依存関係チェックサム
```

**生成物:**

| ファイル | 説明 |
|---------|------|
| `main.go` | `main_tmp.go` の実行により生成されるDB登録コード。`init-mgmt-db/` に配置して使用する |

### 各ファイルの説明

| ファイル | 説明 |
|---------|------|
| `config.yaml` | ユーザが編集する環境設定ファイル。拠点・スイッチ・サーバ等のインフラ情報を記述する |
| `main_template.go` | Go の `text/template` 構文で書かれたテンプレートファイル。`{{range}}`/`{{if}}` によるループ・条件分岐を含む |
| `main_tmp.go` | コードジェネレーター。`config.yaml` を読み込み、`main_template.go` を展開して `init-mgmt-db` で使用する `main.go` を標準出力へ出力する |
| `main.go` | 自動生成される実行コード。`init-mgmt-db/` に配置後、`make initdb` でDB登録に使用する |
| `go.mod` | Goモジュール定義（`gorm.io/gorm`、`gorm.io/driver/postgres` 等の依存関係） |
| `go.sum` | 依存関係のチェックサム |

---

## 使用の前提条件

**Go 1.24 以上** がインストールされていること
   ```bash
   #バージョン確認
   go version
   ```

   ```bash
   #実行例
   $ go version
   go version go1.24.2 linux/amd64
   ```

---

## 使用前準備

### 1. `config.yaml` の編集

`config.yaml` を環境に合わせて編集します。以下の 9 セクションを設定します。

| セクション | 説明 |
|-----------|------|
| `location` | 拠点名リスト（dc1、dc2 等） |
| `nw_switch` | ネットワークスイッチ情報（機種、IPアドレス等） |
| `nw_port` | ネットワークポート情報（スイッチのインターフェース） |
| `maas` | MAAS（Metal-as-a-Service）の接続設定 |
| `cots` | COTSサーバ情報（ベアメタル・VMホスト） |
| `cdi` | FUJITSU CDI の接続設定 |
| `pcie_box` | PCIe Box のリソース情報（NIC、GPU、SSD） |
| `compute_pool` | コンピュートプール（物理サーバ）情報 |
| `cots_gpu` | COTSサーバに搭載されたGPU情報（UUID、モデル） |

**セクション別フィールド詳細**

#### 1-1. `location`

拠点名の文字列リスト。各要素が1拠点に対応し、リストの順序がインデックスになる。（1番目 → `dc1`、2番目 → `dc2`）

```yaml
location:
  - dc1   # 1番目 → loc1 に対応

nw_switch:
  - location: "loc1.Location"   # dc1 を指す
```

#### 1-2. `nw_switch`

| フィールド | 説明 |
|-----------|------|
| `nw_switch_name` | 任意の名前を設定する |
| `location` | 対応する拠点情報を指す。1番目の拠点なら `loc1.Location`、2番目なら `loc2.Location`。 |
| `nw_ip_address` | スイッチのIPアドレス |
| `nw_user` | スイッチへのアクセスユーザ名 |
| `status` | 通常 `0` で良い（`0` は正常の意味） |
| `product_info` | 物理インフラのネットワーク制御IFに設定するプロダクト識別情報 |

**`product_info` の設定方法:**

機種名を `product_name` に設定する。`vendor` / `os` は機種名から判別して設定する。`version`は基本的に `none` で良い。

ダミー設定の場合は以下の値を使用する。

```yaml
product_info:
  vendor: "dummy"
  product_name: "dummy"
  os: "dummy"
  version: "none"
```

#### 1-3. `nw_port`

| フィールド | 説明 |
|-----------|------|
| `nw_switch_id` | 対応する `nw_switch` のインデックスに基づいて設定する。1番目のスイッチなら `sw1.NwSwitchID`、2番目なら `sw2.NwSwitchID`。 |
| `interface_name` | スイッチのインターフェース名（例: `Ethernet1`） |

**`nw_switch_id` の記述形式:**

`swX.NwSwitchID` の形式で記述します（X は `nw_switch` リストの何番目かを表す 1-based インデックス）。

```yaml
nw_switch:
  - nw_switch_name: "10g-sw"   # 1番目 → sw1 に対応

nw_port:
  - nw_switch_id: "sw1.NwSwitchID"   # 1番目のスイッチを指す
    interface_name: Ethernet1
```

#### 1-4. `maas`

| フィールド | 説明 |
|-----------|------|
| `access_url` | MAASのAPIエンドポイントURL |
| `api_key` | MAAS GUI の `admin` → `API keys` に表示されている値を設定する |
| `status` | 通常 `0` で良い（`0` は正常の意味） |
| `product_info.vendor` | `canonical` |
| `product_info.product_name` | `MAAS` |
| `product_info.version` | MAASのバージョン。設定値はX.Xまで。（例: `3.6`） |

#### 1-5. `cdi`

CDI機器を使用しない場合は、このセクションに記述されているダミー設定は変更せずに維持してください。

| フィールド | 説明 |
|-----------|------|
| `name` | CDIの識別名（任意） |
| `location` | CDIが属する拠点名（`location` リストの値と一致させる） |
| `remote_host` | CDIのIPアドレス |
| `remote_user` | CDIへの接続ユーザ名 |
| `group_name` | CDIのグループ名 |
| `status` | 通常 `0` で良い（`0` は正常の意味） |
| `product_info.vendor` | `fujitsu` |
| `product_info.product_name` | `PRIMERGY CDI` |
| `product_info.version` | CDIのバージョン。設定値はX.Xまで。（例: `1.1`） |

**`extra_parameters` の各フィールド:**

| フィールド | 説明 |
|-----------|------|
| `cdi_guest` | CDIゲストのIPアドレス |
| `cdi_user` | CDIユーザ名 |
| `cdi_password` | CDIパスワード |
| `cdimgr_guest_user` | CDIマネージャーゲストのユーザ名 |
| `cdimgr_guest_password` | CDIマネージャーゲストのパスワード |
| `cdimgr_host` | CDIマネージャーホストのIPアドレスまたはホスト名 |
| `cdimgr_host_user` | CDIマネージャーホストのユーザ名 |
| `cdimgr_host_password` | CDIマネージャーホストのパスワード |
| `director_password` | Directorのパスワード |

#### 1-6. `pcie_box`

CDI機器を使用しない場合は、このセクションに記述されているダミー設定は変更せずに維持してください。

| フィールド | 説明 |
|-----------|------|
| `ip_address` | PCIe BoxのIPアドレス |
| `status` | 通常 `0` で良い（`0` は正常の意味） |

**`nic` の各フィールド:**

| フィールド | 説明 |
|-----------|------|
| `res_uuid` | NICリソースのUUID |
| `res_name` | NICリソース名（例: `nic0`） |
| `mac_address` | MACアドレス |
| `nw_port_id` | `nw_port` のインデックスに基づいて設定する（1番目なら `1`） |
| `status` | 通常 `0` で良い（`0` は正常の意味） |

**`gpu` の各フィールド:**

| フィールド | 説明 |
|-----------|------|
| `res_uuid` | GPUリソースのUUID |
| `res_name` | GPUリソース名（例: `gpu0`） |
| `uuid` | GPUのUUID（`nvidia-smi` コマンドで取得） |
| `status` | 通常 `0` で良い（`0` は正常の意味） |

**`ssd` の各フィールド:**

| フィールド | 説明 |
|-----------|------|
| `res_uuid` | SSDリソースのUUID |
| `res_name` | SSDリソース名（例: `ssd0`） |
| `storage_gb` | SSDの容量（GB） |
| `status` | 通常 `0` で良い（`0` は正常の意味） |

#### 1-7. `compute_pool`

CDI機器を使用しない場合は、このセクションに記述されているダミー設定は変更せずに維持してください。

| フィールド | 説明 |
|-----------|------|
| `host_name` | ホスト名 |
| `ipmi_address` | IPMIのIPアドレス |
| `ipmi_user` | IPMIユーザ名 |
| `ipmi_password` | IPMIパスワード |
| `mgr_mac_address` | 管理系NICのMACアドレス |
| `host_mac_address` | ホスト系NICのMACアドレス |
| `host_nw_port_id` | `nw_port` のインデックスに基づいて設定する（1番目なら `1`） |
| `cni_mac_address` | CNI用NICのMACアドレス |
| `cni_nw_port_id` | `nw_port` のインデックスに基づいて設定する（1番目なら `1`） |
| `res_name` | コンピュートリソース名（例: `pcpu0`） |
| `cpu_cores` | CPUコア数 |
| `memory_mb` | メモリ容量（MB） |
| `status` | 通常 `0` で良い（`0` は正常の意味） |
| `product_info` | ハードウェアのベンダー・製品名・バージョンを設定する。`version` は基本的に `none` で良い。 |

**`apldata`（app系NIC搭載時のみ）の各フィールド:**

| フィールド | 説明 |
|-----------|------|
| `mac` | app系NICのMACアドレス |
| `nw_port_id` | `nw_port` のインデックスに基づいて設定する（1番目なら `1`） |
| `nic_model` | NICのモデル名（例: `NVIDIA-CONNECTX-7`） |

#### 1-8. `cots`

| フィールド | 説明 |
|-----------|------|
| `host_name` | ホスト名 |
| `location` | COTSサーバが属する拠点名（`location` リストの値と一致させる） |
| `ipmi_address` | IPMIのIPアドレス |
| `ipmi_user` | IPMIユーザ名 |
| `ipmi_password` | IPMIパスワード |
| `server_role` | `0`: K8s Control Plane、`1`: K8s Worker Node。COTSサーバの予備ノードを払い出す時は `1`（Worker Node）のCOTSから選択する。 |
| `deployment_type` | `0`: VMのホスト、`1`: ベアメタル。COTSサーバの予備ノードを払い出す時は `1`（ベアメタル）のCOTSから選択する。COTSサーバはベアメタル扱い。 |
| `mgr_mac` | 管理系NICのMACアドレス |
| `host_mac` | ホスト系NICのMACアドレス |
| `host_nw_port_id` | `nw_port` のインデックスに基づいて設定する（1番目なら `1`） |
| `cni_mac` | CNI用NICのMACアドレス |
| `cni_nw_port_id` | `nw_port` のインデックスに基づいて設定する（1番目なら `1`） |
| `cpu_cores` / `memory_mb` / `storage_gb` | コミッション状態でMAAS GUIのSummary TOPに表示されているマシンのスペックを設定する。VMに割り当てる設定ではなく、VMホスト自体のスペックであることに注意。 |
| `status` | `0` が正常 |
| `product_info` | MAAS GUIのSummary左下の`HARDWARE INFORMATION`に記載されている情報をもとに設定する。`version` は基本的に `none` で良いが、物理インフラで参照されるので注意が必要。 |

**`apldata`（app系NIC搭載時のみ）の各フィールド:**

| フィールド | 説明 |
|-----------|------|
| `mac` | app系NICのMACアドレス |
| `nw_port_id` | `nw_port` のインデックスに基づいて設定する（1番目なら `1`） |
| `nic_model` | NICのモデル名（例: `NVIDIA-CONNECTX-7`） |



#### 1-9. `cots_gpu`

テナント構築前はダミー値で良い。

| フィールド | 説明 |
|-----------|------|
| `worker` | GPUが搭載されているCOTSサーバの `host_name` と一致させる |
| `uuid` | `nvidia-smi` コマンドで取得する |
| `model` | テナント構築yaml(../dci_tenant_infra_chart/<マニフェストファイル名>.yaml)と合わせる必要がある |
| `status` | `0` が正常 |

### 2. 依存関係のインストール（初回のみ）

```bash
go mod tidy
```

---

## 使用方法

### 1. `main.go` の生成

```bash
go run main_tmp.go > main.go
```

正常に生成されると `main.go` がカレントディレクトリに作成されます。

---

## トラブルシューティング

**Q: `go run main_tmp.go > main.go` でエラーが発生する**

A: 以下を確認してください。
- Go のバージョンが 1.24 以上であるか（`go version`）
- `go mod tidy` で依存関係がインストールされているか
- `config.yaml` が存在し、YAML構文が正しいか（インデント・コロン等）
- `main_template.go` が同一ディレクトリに存在するか

**Q: `config.yaml` の設定値が正しく反映されない**

A: `go run main_tmp.go > main.go` を再実行して `main.go` を再生成してください。`config.yaml` を編集した後は必ず再生成が必要です。

