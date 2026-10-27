# DCI-2.0 パラメータシート

本書は、DCI運用者がDCI管理用クラスタおよびDCIテナント論理インフラ構築に必要な情報(パラメータ)をまとめたものである。

> **注意:** 本書は記入用のテンプレートです。実際のIPアドレス・パスワード等を記入したコピーを公開リポジトリにコミットしないでください。

## 1. 使用するDHRC資材・主なバージョン一覧

https://github.com/openkasugai/

| repository/OSS | tag /version |
|---|---|
| dci_manager | v1.0.0 |
| dci_physical_infrastructure | v1.0.0 |
| dci_tenant_infrastructure | v1.0.0 |
| dci_common | v1.0.0 |
| kubernetes | 1.34.8 |
| go | 1.26.2 |
| helm | 4.0.4 |
| velero | 1.17.1 |
| その他OSS | 別紙OSS一覧を参照 |

## 2. アドレス・アカウント情報

### 操作端末

| 操作端末 | ホスト名 | マネージャNW 管理用IP | ユーザ・パスワード |
|---|---|---|---|
| DCI運用者用操作端末 |  |  |  |
| テナント運用者用操作端末 |  |  |  |

### 外部ストレージ(NFS)

| 外部ストレージ | ホスト名 | マネージャNW 管理用IP | ユーザ・パスワード | エクスポートディレクトリのパス |
|---|---|---|---|---|
| NFSサーバ（VM） |  |  |  |  |

### 外部ストレージ(バックアップ)

| 外部ストレージ | ホスト名 | マネージャNW 管理用IP | ユーザ・パスワード | MINIO情報: IPアドレス | MINIO情報: ポート番号 | MINIO情報: aws_access_key_id | MINIO情報: aws_secret_access_key | MINIO情報: バケット名 |
|---|---|---|---|---|---|---|---|---|
| バックアップサーバ（VM） |  |  |  |  |  |  |  |  |

### 各種サーバ

| サーバ | IPアドレス or サーバ名 | 備考 |
|---|---|---|
| NTPサーバ |  |  |
| DNSサーバ |  |  |
| 踏み台サーバ(BASTION_IP) |  | ←Harbor/Grafana 踏み台 |

| サーバ | あり/なし | IPアドレス or サーバ名 | 通知先メールアドレス |
|---|---|---|---|
| SMTPサーバ |  |  |  |

### NW情報

DCIシステム NW C情報（COTS#3）

| # | NW | CIDR | デフォルト | 備考 |
|---|---|---|---|---|
| 1 | マネージャ用NW |  |  |  |
| 2 | ホスト用NW |  |  |  |
| 3 | CNI用NW |  |  |  |
| 4 | アプリデータ用NW |  |  |  |
| 5 | k8s POD用 |  | 10.245.0.0/16 |  |
| 6 | k8s service用 |  | 10.96.0.0/12 |  |
| 7 | アプリPoD 2nd-NIC用(SR-IOV network operater) |  | 192.168.1.64/26 | 他と重複しなければ何でもいい,ネットマスクはアプリによる |

### アクセス情報(DCI管理用)

| # | DCI管理用サーバ | ホスト名 | IPMI/BMC IP | マネージャNW用MAC | マネージャNW用IP | インタフェース名 | 冗長化用VIP(CP) | 冗長化用VIP(LB_VIP) | ユーザ・パスワード(IPMI/BMC) | ユーザ・パスワード(HW管理等) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | DCI管理用VMホストサーバ |  |  | - |  |  | - | - |  |  |
| 2 | DCI管理用クラスタ Control Plane1 |  |  | - |  |  | （VIPアサインする） | （CP用とは違うVIPをアサインする） |  |  |
| 3 | DCI管理用クラスタ Control Plane2 |  |  | - |  |  | （VIPアサインする） | （CP用とは違うVIPをアサインする） |  |  |
| 4 | DCI管理用クラスタ Control Plane3 |  |  | - |  |  | （VIPアサインする） | （CP用とは違うVIPをアサインする） |  |  |
| 5 | DCI管理用クラスタ node1 |  |  | - |  |  | - | - |  |  |
| 6 | DCI管理用クラスタ node2 |  |  | - |  |  | - | - |  |  |
| 7 | MAASサーバ |  |  | - |  |  | - | - |  |  |

※ Control Plane1~3 の冗長化用VIPは共通の値を1つアサインする。

### アクセス情報(DCIテナント論理インフラ用)

| # | DCIテナント論理インフラ用サーバ | ホスト名 | IPMI/BMC IP | マネージャNW用MAC | マネージャNW用IP | 冗長化用VIP(CP) | 冗長化用VIP(LB_VIP) | ユーザ・パスワード(IPMI/BMC) | ユーザ・パスワード(HW管理等) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | COTSサーバ(Control Plane) |  |  |  |  | （CP用とは違うVIPをアサインする） | （CP用とは違うVIPをアサインする） |  |  |
| 2 | COTSサーバ(Control Plane) |  |  |  |  | （CP用とは違うVIPをアサインする） | （CP用とは違うVIPをアサインする） |  |  |
| 3 | COTSサーバ(Control Plane) |  |  |  |  | （CP用とは違うVIPをアサインする） | （CP用とは違うVIPをアサインする） |  |  |
| 4 | COTSサーバ |  |  |  |  | - | - |  |  |
| 5 | 計算サーバ |  |  |  |  | - | - |  |  |
| 6 | :（以降、必要な数だけ記載） |  |  |  |  | - | - |  |  |

※ Control Plane 1~3 の冗長化用VIPは共通の値を1つアサインする。

### DCI管理用クラスタ構築用アカウント情報

| # | OSS | ユーザ | パスワード | デフォルト: ユーザ | デフォルト: パスワード | デフォルト: database名 |
|---|---|---|---|---|---|---|
| 1 | DCI管理用クラスタ Harbor |  |  | admin | Harbor12345 | - |
| 2 | DCI管理用クラスタ Grafana |  |  | admin | prom-operator | - |
| 3 | 構成管理DB PostgreSQL |  |  | postgres | (secret管理) | app |
| 4 | MAAS |  |  | admin | password |  |

### テナント論理インフラ構築用アカウント情報

| # | OSS | ユーザ | パスワード |
|---|---|---|---|
| 1 | DCIテナント論理インフラ Harbor |  |  |
| 2 | DCI管理用クラスタ Grafana |  |  |

### OS RHELライセンス情報

| # | 項目 | 値 |
|---|---|---|
| 1 | RHEL activation-key |  |
| 2 | RHEL organization |  |

## 3. 構成管理DB情報

構成管理DBに必要な情報

main.goで使用

### 1. TPhysical（物理インフラ情報）

物理インフラの拠点名称

テーブル名: `t_physical`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | name | 物理インフラ名（ユニークな名称） | phy1 | phy1 | // Name of the DCI physical infrastructure.<br>phy := &amp;model.TPhysical{} の中 |
|  | description | 説明（必要であれば） | (任意) |  |  |

### 2. TLocation（拠点情報）

物理インフラがある拠点をすべて記載する（以下は2拠点の例）

テーブル名: `t_location`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | Location1 | 設置拠点名（ユニークな名称） | dc1 | dc1 | loc1 := &amp;model.TLocation{} の中。<br>拠点数分だけ変数(loc1,loc2)を分けて記載 |
|  | description | 説明（必要であれば） | (任意) |  |  |
| 2 | Location2 | 物理インフラの拠点が複数ある場合、設置拠点名（ユニークな名称） | dc2 | dc2 |  |
|  | description | 説明（必要であれば） | (任意) |  |  |

（以降、必要な数だけ同様に記載する）

### 3. TNwSwitch（ネットワークスイッチ）

HOST/CNI/APPDATAで使用するSW機器情報、DHRCから制御するSW全ての情報を記載する

テーブル名: `t_nw_switch`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | nw_switch_id | UUID(自動生成) | UUID-XXXXXXX1 | 変更不要（自動生成） | swList := []*model.TNwSwitch{} の中。<br>リスト形式で、スイッチ分だけ記載。<br>※ パラメータシートに無いが、statusは「0」固定<br>main.goでは、リストを設定した後にスイッチ分だけ<br>sw1, _ := qsw.WithContext(ctx).Where(...<br>sw2, _ := qsw.WithContext(ctx).Where(...<br>:<br>を記載する |
|  | NwSwitchName | SW名 | l2-switch-host01 |  |  |
|  | Location | 設置拠点を変数で指定 | dc1 |  | ※ 拠点は、loc1.Location の形で指定。<br> 文字列ではない |
|  | NwIPAddress | 管理用IPアドレス | 172.18.195.239 |  |  |
|  | NwUser | 管理用User | user1 |  |  |
|  | product_info.vendor | ベンダ | edgecore networks |  |  |
|  | product_info.product_name | 製品名 | AS4625-54T |  |  |
|  | product_info.os | NOS | Edgecore SONiC |  |  |
|  | product_info.version | バージョン | none |  |  |
| 2 | nw_switch_id | UUID(自動生成) | UUID-XXXXXXX2 | 変更不要（自動生成） |  |
|  | NwSwitchName | SW名 | l2-switch-cni01 |  |  |
|  | Location | 設置拠点 | dc1 |  | 変数で指定（loc1.Locationなど） |
|  | NwIPAddress | 管理用IPアドレス | 172.18.195.239 |  |  |
|  | NwUser | 管理用User | user1 |  |  |
|  | product_info.vendor | ベンダ | edgecore networks |  |  |
|  | product_info.product_name | 製品名 | AS4625-54T |  |  |
|  | product_info.os | NOS | Broadcom SONiC |  |  |
|  | product_info.version | バージョン | none |  |  |
| 3 | nw_switch_id | UUID(自動生成) | UUID-XXXXXXX3 | 変更不要（自動生成） |  |
|  | NwSwitchName | SW名 | l2-switch-app01 |  |  |
|  | Location | 設置拠点 | dc1 |  | 変数で指定（loc1.Locationなど） |
|  | NwIPAddress | 管理用IPアドレス | 172.18.195.239 |  |  |
|  | NwUser | 管理用User | user1 |  |  |
|  | product_info.vendor | ベンダ | edgecore networks |  |  |
|  | product_info.product_name | 製品名 | DCS208/AS5812-54X |  |  |
|  | product_info.os | NOS | Edgecore SONiC |  |  |
|  | product_info.version | バージョン | none |  |  |

（以降、必要な数だけ同様に記載する）

### 4. TNwPort（NWポート）

テナントに使用する全サーバのNIC（HOST/CNI/APPDATA）と接続された接続先SW IDと接続先SW インタフェースの一覧（HOST/CNI/APPDATAで使用するSW全て）

テーブル名: `t_nw_port`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | NwSwitchID | 登録したスイッチのNwSwitchID | UUID-XXXXXXX1 |  | ports := []*model.TNwPort{}の中。<br>NwSwitchID:    sw1.NwSwitchID,の形式で指定する。<br>リスト形式で、ポート分だけ記載。<br>※ main.go では変数が埋まっている。<br>※ sw1変数の変更も必要<br>  変数内で名前を指定している個所がある。 |
|  | InterfaceName | IF名：Ethernet0など VLAN設定するときに指定するI/F名 | Ethernet0 |  |  |
| 2 | NwSwitchID | 登録したスイッチのNwSwitchID | UUID-XXXXXXX2 |  | 変数で設定(sw1.NwSwitchID、sw2.NwSwitchID、sw3.NwSwitchIDなど) |
|  | InterfaceName | IF名：Ethernet0など VLAN設定するときに指定するI/F名 | Ethernet0 |  |  |
| 3 | NwSwitchID | 登録したスイッチのNwSwitchID | UUID-XXXXXXX3 |  | 変数で設定(sw1.NwSwitchID、sw2.NwSwitchID、sw3.NwSwitchIDなど) |
|  | InterfaceName | IF名：Ethernet0など VLAN設定するときに指定するI/F名 | Ethernet0 |  |  |
| 4 | NwSwitchID | 登録したスイッチのNwSwitchID | UUID-XXXXXXX1 |  | 変数で設定(sw1.NwSwitchID、sw2.NwSwitchID、sw3.NwSwitchIDなど) |
|  | InterfaceName | IF名：Ethernet0など VLAN設定するときに指定するI/F名 | Ethernet4 |  |  |
| 5 | NwSwitchID | 登録したスイッチのNwSwitchID | UUID-XXXXXXX2 |  | 変数で設定(sw1.NwSwitchID、sw2.NwSwitchID、sw3.NwSwitchIDなど) |
|  | InterfaceName | IF名：Ethernet0など VLAN設定するときに指定するI/F名 | Ethernet4 |  |  |
| 6 | NwSwitchID | 登録したスイッチのNwSwitchID | UUID-XXXXXXX3 |  | 変数で設定(sw1.NwSwitchID、sw2.NwSwitchID、sw3.NwSwitchIDなど) |
|  | InterfaceName | IF名：Ethernet0など VLAN設定するときに指定するI/F名 | Ethernet10 |  |  |

（以降、必要な数だけ同様に記載する）

### 5. TMaa（MAAS情報）

テーブル名: `t_maas`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | physical_infra_id | MAAS制御する物理インフラのIDを変数で指定 | 1 |  | maas := &amp;model.TMaa{} の中。<br>PhysicalInfraID: rp.IDの部分 |
|  | AccessURL | MAAS API URL | http://172.18.195.29:5240/MAAS/api/2.0/ |  |  |
|  | APIKey | MAASのAPIキー<br>※構築マニュアルの「3.2.2.7. MAASへのRHELイメージ登録」の手順の中で表示されたAPIキーを設定してください | &lt;MAAS GUIで確認したAPIkeyを記載する&gt; |  |  |
|  | product_info.vendor | ベンダ | canonical | canonical | 固定 |
|  | product_info.product_name | 製品名 | MAAS | MAAS | 固定 |
|  | product_info.version | バージョン | 3.6 | 3.6 | 固定 |

### 6. TCdi（CDI情報）

テーブル名: `t_cdi` ※ v2.0とv1.1の場合で設定が異なる

#### (1) CDI管理ソフトウェア v2.0の場合

| cdi_id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | CdiName | 識別名（cdi_v2.0などユニークな名称） | cdi_v1.1 |  | c := &amp;model.TCdi{}の中。<br>extraParams も必要なら修正する。 |
|  | Location | 拠点（dc1など） | dc1 |  |  |
|  | RemoteHost | LinuxクライアントPC IPアドレス | 172.18.11.111 |  |  |
|  | RemoteUser | LinuxクライアントPC login user | ubuntu |  |  |
|  | GroupName | リソースグループ名 | group0 | group0 | 固定 |
|  | product_info.vendor | ベンダ | fujitsu |  |  |
|  | product_info.product_name | 製品名 | PRIMERGY CDI |  |  |
|  | product_info.version | CDI管理ソフトウェアのバージョン | 1.1 | 2.0 | 固定 |
|  | extra_parameters.cdi_user | LinuxクライアントPCでの cdictl -u $URL auth login 時のusername | cdiadmin | dhrcsystem | 固定 |
|  | extra_parameters.cdi_password | LinuxクライアントPCでの cdictl -u $URL auth login 時のPassword | ** |  |  |
|  | extra_parameters.director_password | Director login ID (liqadmin) のパスワード（hhchkコマンドの-Dオプションで指定するパスワード） | ** |  |  |
|  | extra_parameters.cdi_host | CDI管理ソフトウェア(ホストOS)の IPアドレス | 172.18.195.205 |  |  |
|  | extra_parameters.cdi_host_user | CDI管理サーバ(ホストOS)のユーザ | *** |  |  |
|  | extra_parameters.cdi_host_password | CDI管理サーバ(ホストOS)のパスワード（hhchkコマンドの-Fオプションで指定するパスワード） | *** |  |  |
|  | extra_parameters.cdi_guest | CDI管理ソフトウェア(ゲストOS)の IPアドレス | 172.18.195.205 |  |  |
|  | extra_parameters.cdi_guest_user | CDI管理ソフトウェア(ゲストOS) のuser | cdiadmin |  |  |
|  | extra_parameters.cdi_guest_password | CDI管理ソフトウェア(ゲストOS)のパスワード | *** |  |  |
|  | extra_parameters.cdi_host_password | CDI管理サーバ(ホスト)のrootのパスワード | *** |  |  |

#### (2) CDI管理ソフトウェア v1.1の場合

| cdi_id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | CdiName | 識別名（cdi_v1.1などユニークな名称） | cdi_v1.1 |  | c := &amp;model.TCdi{}の中。<br>extraParams も必要な修正する。 |
|  | Location | 拠点（dc1など） | dc1 |  |  |
|  | RemoteHost | LinuxクライアントPC IPアドレス | 172.18.11.111 |  |  |
|  | RemoteUser | LinuxクライアントPC login user | ubuntu |  |  |
|  | GroupName | リソースグループ名 | group0 | group0 | 固定 |
|  | product_info.vendor | ベンダ | fujitsu |  |  |
|  | product_info.product_name | 製品名 | PRIMERGY CDI |  |  |
|  | product_info.version | CDI管理ソフトウェアのバージョン | 1.1 | 1.1 | 固定 |
|  | extra_parameters.cdi_user | LinuxクライアントPCでの cdictl -u $URL auth login 時のusername | cdiadmin | dhrcsystem | 固定 |
|  | extra_parameters.cdi_password | LinuxクライアントPCでの cdictl -u $URL auth login 時のPassword | ** |  |  |
|  | extra_parameters.director_password | Director login ID (liqadmin) のパスワード（hhchkコマンドの-Dオプションで指定するパスワード） | ** |  |  |
|  | extra_parameters.cdi_host_password | CDI管理サーバ(ホストOS) rootのパスワード（hhchkコマンドの-Fオプションで指定するパスワード） | *** |  |  |
|  | extra_parameters.cdi_guest | CDI管理ソフトウェア(ゲストOS)の IPアドレス | 172.18.195.205 |  |  |
|  | extra_parameters.cdi_guest_user | CDI管理ソフトウェア(ゲストOS) のuser | cdiadmin |  |  |
|  | extra_parameters.cdi_guest_password | CDI管理ソフトウェア(ゲストOS)のパスワード | *** |  |  |

### 7. TCdiBox（PCI-BOX情報）

テーブル名: `t_cdi_box`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | boxIPAddress | PCI-Box管理用 IPアドレス | 172.18.22.222 |  |  |
|  | cdi_id | 接続されたCDIのID | 1 | 変更不要 | box := &amp;model.TCdiBox{} の中。変数で指定（rc.CdiIDなど） |

### 8. TCdiGpu（CDI GPU）

CDI PCI-BOXに搭載されているGPUの数分記載する

テーブル名: `t_cdi_gpu`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | ResUUID | CDIでの res_uuid | f2543f10-... |  | cgpuList := []*model.TCdiGpu{} の中。<br>リストで記載。 |
|  | ResName | CDIでのリソース名称 | gpu0 |  |  |
|  | cdi_id | 接続されたCDIのID | 1 |  | 変数で指定（rc.CdiIDなど） |
|  | box_id | 搭載されたPCI-BoxのID | 1 |  | 変数で指定（rc.IDなど） |
|  | UUID | GPU UUID (※nvidia-smiで確認)<br>※システム構築時はダミーの値でもよい | GPU-xxxx |  |  |
| 2 | ResUUID | CDIでの res_uuid | caf49b8d-... |  |  |
|  | ResName | CDIでのリソース名称 | gpu1 |  |  |
|  | cdi_id | 接続されたCDIのID | 1 |  | 変数で指定（rc.CdiIDなど） |
|  | box_id | 搭載されたPCI-BoxのID | 1 |  | 変数で指定（rc.IDなど） |
|  | UUID | GPU UUID (※nvidia-smiで確認)<br>※システム構築時はダミーの値でもよい | GPU-xxxx |  |  |
| 3 | ResUUID | CDIでの res_uuid | caf49b80-... |  |  |
|  | ResName | CDIでのリソース名称 | gpu3 |  |  |
|  | cdi_id | 接続されたCDIのID | 1 |  | 変数で指定（rc.CdiIDなど） |
|  | box_id | 搭載されたPCI-BoxのID | 1 |  | 変数で指定（rc.IDなど） |
|  | UUID | GPU UUID (※nvidia-smiで確認)<br>※システム構築時はダミーの値でもよい | GPU-xxxx |  |  |

（以降、必要な数だけ同様に記載する）

### 9. TCdiSsd（CDI SSD）

CDI PCI-BOXに搭載されているSSDの数分記載する

テーブル名: `t_cdi_ssd`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | ResUUID | CDIでの res_uuid | f2543f20-... |  | cssdList := []*model.TCdiSsd{} の中。<br>リストで記載。 |
|  | ResName | CDIでのリソース名称 | ssd0 |  |  |
|  | cdi_id | 接続されたCDIのID | 1 |  | 変数で指定（rc.CdiIDなど） |
|  | box_id | 搭載されたPCI-BoxのID | 1 |  | 変数で指定（rc.IDなど） |
|  | StorageGb | 容量(GB) | 960 |  |  |
| 2 | ResUUID | CDIの res_uuid | f2543f80-... |  |  |
|  | ResName | CDIでのリソース名称 | ssd1 |  |  |
|  | cdi_id | 接続されたCDIのID | 1 |  | 変数で指定（rc.CdiIDなど） |
|  | box_id | 搭載されたPCI-BoxのID | 1 |  | 変数で指定（rc.IDなど） |
|  | StorageGb | 容量(GB) | 960 |  |  |

（以降、必要な数だけ同様に記載する）

### 10. TCdiComputePool（CDI Compute）

CDI 計算サーバの台数分記載する

テーブル名: `t_cdi_compute_pool`

| server_id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | HostName | ホスト名（ユニークな名称） | pgcdi-compute01 |  | ccpList := []*model.TCdiComputePool{} の中。<br>リストで記載。 |
|  | IpmiAddress | IPMI/BMC IPアドレス | 172.18.111.222 |  |  |
|  | IpmiUser | IPMIのUser | user1 |  |  |
|  | IpmiPassword | IPMIのPassword | ** |  |  |
|  | MgrMacAddress | マネージャ用NICのMACアドレス | f0:b2... |  |  |
|  | HostMacAddress | ホスト用NICのMACアドレス | f0:b2... |  |  |
|  | CniMacAddress | CNI用NICのMACアドレス | b8:3f... |  |  |
|  | ApldataMacAddress | アプリデータ用NICのMACアドレス | 94:6d... |  | 変数のポインタを指定する |
|  | HostNwPortID | ホスト用NW NICが接続されたスイッチのポートを設定する。具体的には、t_nw_portテーブルに登録されたレコードのうち、スイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 1 |  |  |
|  | CniNwPortID | CNI用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 2 |  |  |
|  | ApldataNwPortID | 計算サーバにアプリデータ用NICが搭載されている場合、アプリデータ用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 3 |  | 変数のポインタを指定する |
|  | ApldataNicModel | アプリデータ用NICモデル | NVIDIA-CONNECTX-6-DX |  | 変数のポインタを指定する |
|  | CPUCores | CPUコア数 | 144 |  |  |
|  | Memory | メモリサイズ(MiB) | 533504 |  |  |
|  | cdi_id | 接続されたCDIのIDを変数で指定（rc.CdiIDなど） | 1 |  |  |
|  | ResName | CDIのリソース名 | pcpu0 |  |  |
|  | product_info.vendor | ベンダ | fujitsu |  |  |
|  | product_info.product_name | 製品名 | PRIMERGY RX2530 M7 |  |  |
|  | product_info.version | Version | none |  |  |
| 2 | HostName | ホスト名（ユニークな名称） | pgcdi-compute01 |  | ccpList := []*model.TCdiComputePool{} の中。<br>リストで記載。 |
|  | IpmiAddress | IPMI/BMC IPアドレス | 172.18.111.222 |  |  |
|  | IpmiUser | IPMIのUser | user1 |  |  |
|  | IpmiPassword | IPMIのPassword | ** |  |  |
|  | MgrMacAddress | マネージャ用NICのMACアドレス | f0:b2... |  |  |
|  | HostMacAddress | ホスト用NICのMACアドレス | f0:b2... |  |  |
|  | CniMacAddress | CNI用NICのMACアドレス | b8:3f... |  |  |
|  | ApldataMacAddress | アプリデータ用NICのMACアドレス | 94:6d... |  | 変数のポインタを指定する |
|  | HostNwPortID | ホスト用NW NICが接続されたスイッチのポートを設定する。具体的には、t_nw_portテーブルに登録されたレコードのうち、スイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 1 |  |  |
|  | CniNwPortID | CNI用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 2 |  |  |
|  | ApldataNwPortID | 計算サーバにアプリデータ用NICが搭載されている場合、アプリデータ用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 3 |  | 変数のポインタを指定する |
|  | ApldataNicModel | アプリデータ用NICモデル | NVIDIA-CONNECTX-6-DX |  | 変数のポインタを指定する |
|  | CPUCores | CPUコア数 | 144 |  |  |
|  | Memory | メモリサイズ(MiB) | 533504 |  |  |
|  | cdi_id | 接続されたCDIのIDを変数で指定（rc.CdiIDなど） | 1 |  |  |
|  | ResName | CDIのリソース名 | pcpu0 |  |  |
|  | product_info.vendor | ベンダ | fujitsu |  |  |
|  | product_info.product_name | 製品名 | PRIMERGY RX2530 M7 |  |  |
|  | product_info.version | Version | none |  |  |

（以降、必要な数だけ同様に記載する）

### 11. TCotsServerPool（COTSサーバ）

COTSサーバの台数分記載する

テーブル名: `t_cots_server_pool`

| server_id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | Location | 拠点 | dc1 | dc1 | cotsList := []*model.TCotsServerPool{} の中。<br>リストで記載。<br>※ ここのLocationは文字列。 |
|  | HostName | ホスト名（ユニークな名称） | cots-control01 |  |  |
|  | IpmiAddress | IPMI/BMC アドレス | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane、1: K8s Worker Node | 0 | 0 | Control Plane用 |
|  | DeploymentType | 0: VM のホスト、1: ベアメタル | 1 | 1 |  |
|  | MgrMacAddress | マネージャ用NICのMACアドレス | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | ホスト用NICのMACアドレス | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | ホスト用NW NICが接続されたスイッチのポートを設定する。具体的には、t_nw_portテーブルに登録されたレコードのうち、スイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 10 |  |  |
|  | CniMacAddress | CNI用NICのMACアドレス | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | CNI用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 11 |  |  |
|  | CPUCores | CPUコア数 | 48 |  |  |
|  | Memory | メモリサイズ(MiB) | 196608 |  |  |
|  | StorageGb | ストレージサイズ(GB) | 480 |  |  |
|  | product_info.vendor | ベンダ | dell |  |  |
|  | product_info.product_name | 製品 | PowerEdge R740 |  |  |
|  | product_info.version | Version | none |  |  |
| 2 | Location | 拠点 | dc2 | dc1 |  |
|  | HostName | ホスト名（ユニークな名称） | cots-worker01 |  |  |
|  | IpmiAddress | IPMI/BMC アドレス | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane、1: K8s Worker Node | 1 | 0 | Control Plane用 |
|  | DeploymentType | 0: VM のホスト、1: ベアメタル | 0: VM のホスト、1: ベアメタル | 1 |  |
|  | MgrMacAddress | マネージャ用NICのMACアドレス | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | ホスト用NICのMACアドレス | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | ホスト用NW NICが接続されたスイッチのポートを設定する。具体的には、t_nw_portテーブルに登録されたレコードのうち、スイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 5 |  |  |
|  | CniMacAddress | CNI用NICのMACアドレス | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | CNI用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 6 |  |  |
|  | CPUCores | CPUコア数 | 128 |  |  |
|  | Memory | メモリサイズ(MiB) | 786432 |  |  |
|  | StorageGb | ストレージサイズ(GB) | 8642 |  |  |
|  | product_info.vendor | ベンダ | supermicro |  |  |
|  | product_info.product_name | 製品 | SYS-421GE-TNRT |  |  |
|  | product_info.version | Version | none |  |  |
| 3 | Location | 拠点 | dc2 | dc1 |  |
|  | HostName | ホスト名（ユニークな名称） | cots-worker01 |  |  |
|  | IpmiAddress | IPMI/BMC アドレス | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane、1: K8s Worker Node | 1 | 0 | Control Plane用 |
|  | DeploymentType | 0: VM のホスト、1: ベアメタル | 1 | 1 |  |
|  | MgrMacAddress | マネージャ用NICのMACアドレス | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | ホスト用NICのMACアドレス | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | ホスト用NW NICが接続されたスイッチのポートを設定する。具体的には、t_nw_portテーブルに登録されたレコードのうち、スイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 9 |  |  |
|  | CniMacAddress | CNI用NICのMACアドレス | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | CNI用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 10 |  |  |
|  | CPUCores | CPUコア数 | 128 | 64 |  |
|  | Memory | メモリサイズ(MiB) | 786432 | 524288 |  |
|  | StorageGb | ストレージサイズ(GB) | 8642 | 960 |  |
|  | product_info.vendor | ベンダ | supermicro | supermicro |  |
|  | product_info.product_name | 製品 | SYS-421GE-TNRT | SYS-420GP-TNR |  |
|  | product_info.version | Version | none | 123456789 |  |
| 4 | Location | 拠点 | dc2 |  |  |
|  | HostName | ホスト名（ユニークな名称） | cots-worker01 |  |  |
|  | IpmiAddress | IPMI/BMC アドレス | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane、1: K8s Worker Node | 1 | 1 | Worker node用 |
|  | DeploymentType | 0: VM のホスト、1: ベアメタル | 1 | 1 |  |
|  | MgrMacAddress | マネージャ用NICのMACアドレス | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | ホスト用NICのMACアドレス | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | ホスト用NW NICが接続されたスイッチのポートを設定する。具体的には、t_nw_portテーブルに登録されたレコードのうち、スイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 9 |  |  |
|  | CniMacAddress | CNI用NICのMACアドレス | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | CNI用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 10 |  |  |
|  | ApldataMacAddress | アプリデータ用NICのMACアドレス | 00:00:00:00:00:03 |  | 変数のポインタを指定する |
|  | ApldataNwPortID | 計算サーバにアプリデータ用NICが搭載されている場合、アプリデータ用NW NICが接続されたスイッチのポートを設定する。具体的には、ホスト用NWと同様にスイッチとポートが対応するレコードの主キー(id)の値(※1)を設定する<br>(※1)t_nw_portテーブルの主キー(id)の値は、レコード登録時に自動採番される1始まりの数値になります | 6 |  | 変数のポインタを指定する |
|  | ApldataNicModel | アプリデータ用NICのモデル | NVIDIA-CONNECTX-6-DX |  | 変数のポインタを指定する |
|  | CPUCores | CPUコア数 | 128 |  |  |
|  | Memory | メモリサイズ(MiB) | 786432 |  |  |
|  | StorageGb | ストレージサイズ(GB) | 8642 |  |  |
|  | product_info.vendor | ベンダ | supermicro |  |  |
|  | product_info.product_name | 製品 | SYS-421GE-TNRT |  |  |
|  | product_info.version | Version | none |  |  |

（以降、必要な数だけ同様に記載する）

worker idとhostnameの関連付け

| No | worker id | ホスト名 |  | 設定 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | workerのID(worker1など) | ホスト名（hostname-xxxなど） |  |  | worker1, _ := qcots.WithContext(ctx).Where(qcots.HostName.Eq("hostname-xxx")).First() |
| 2 | workerのID(worker2など) | ホスト名（hostname-yyyなど） |  |  | worker2, _ := qcots.WithContext(ctx).Where(qcots.HostName.Eq("hostname-yyy")).First() |
| 3 | workerのID(worker3など) | ホスト名（hostname-zzzなど） |  |  | worker3, _ := qcots.WithContext(ctx).Where(qcots.HostName.Eq("hostname-zzz")).First() |

### 12. TCotsServerGpu（COTS GPU）

各COTSサーバに搭載されているGPUの情報を記載する

テーブル名: `t_cots_server_gpu`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | server_id | t_cots_server_poolのserver Id | worker1 | worker1.ServerID | cotsGpuList := []*model.TCotsServerGpu{} の中。<br>リストで記載。<br>対応するhostnameと関連付けしたIDを変数で指定（worker1.ServerIDなど） |
|  | UUID | GPUのUUID (※nvidia-smiで確認) テナント構築時はダミーの値でもよい | GPU-00000000-0000-0000-0000-000000000001 |  |  |
|  | model | GPUのモデル | NVIDIA-H100 |  |  |
| 2 | server_id | t_cots_server_poolのserver Id | worker2 |  | 対応するhostnameと関連付けしたIDを変数で指定（worker1.ServerIDなど） |
|  | UUID | GPUのUUID (※nvidia-smiで確認) テナント構築時はダミーの値でもよい | GPU-00000000-0000-0000-0000-000000000001 |  |  |
|  | model | GPUのモデル | NVIDIA-H100 |  |  |
| 3 | server_id | t_cots_server_poolのserver Id | worker3 |  | 対応するhostnameと関連付けしたIDを変数で指定（worker2.ServerIDなど） |
|  | UUID | GPUのUUID (※nvidia-smiで確認) テナント構築時はダミーの値でもよい | GPU-00000000-0000-0000-0000-000000000002 |  |  |
|  | model | GPUのモデル | NVIDIA-H100 |  |  |

（以降、必要な数だけ同様に記載する）

### 13. TOsInfo（OS情報）

テナント用サーバにデプロイする MAASにイメージ登録した OSを記載する（基本変更の必要なし）

テーブル名: `t_os_info`

| id | カラム | 意味 | 例 | 設定値 | main.goでの記載箇所 |
|---|---|---|---|---|---|
| 1 | OsDistribution | OS種別 | rhel | rhel | osInfo := &amp;model.TOsInfo{} の中。 |
|  | OsVersion | バージョン | 9.6-custom | 9.6-custom |  |
|  | LoginUser | ログインUser | cloud-user | cloud-user |  |

## 4. テナント論理インフラ構築情報

テナント構築に必要な情報(DCI運用者向け)

### 1. Cluster

そのままでも利用可能

| 項目 | 例 | 設定値 |
|---|---|---|
| name | tenant-1 |  |
| namespace | tenant-1 |  |
| clusterNetwork.services | 10.96.0.0/12 |  |
| clusterNetwork.pods | 10.245.0.0/16 |  |
| controlPlaneRef.kind | KubeadmControlPlane |  |
| controlPlaneRef.name | (KubeadmControlPlaneのnameと合わせる) |  |
| infrastructureRef.kind | DCICluster |  |
| infrastructureRef.name | (DCIClusterのnameと合わせる) |  |

### 2. DCICluster

| カラム | 例 | 設定値 |
|---|---|---|
| name | (Clusterのnameと合わせる) |  |
| namespace | (Clusterのnamespaceと合わせる) |  |

#### controlPlaneEndpoint

DCIテナント論理インフラのControl Planeで使用する VIPアドレスを記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| host | 172.18.165.30 |  |
| port | 6443 |  |

#### logicalNetwork

##### manager

DCIテナント論理インフラのマネージャ用NWの CIDR、 VLAN ID、使用可能なIPアドレス範囲を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| cidrBlock | 172.18.193.0/24 |  |
| vlanID | 1193 |  |
| ipAddressRange.start | 172.18.193.70 |  |
| ipAddressRange.end | 172.18.193.78 |  |

##### host

DCIテナント論理インフラのホスト用NWの CIDR、 VLAN ID、使用可能なIPアドレス範囲を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| cidrBlock | 172.18.162.0/24 |  |
| vlanID | 1162 |  |
| ipAddressRange.start | 172.18.162.10 |  |
| ipAddressRange.end | 172.18.162.200 |  |

##### cni

DCIテナント論理インフラのCNI用NWの CIDR、 VLAN ID、使用可能なIPアドレス範囲を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| cidrBlock | 172.18.165.0/24 |  |
| vlanID | 1165 |  |
| ipAddressRange.start | 172.18.165.10 |  |
| ipAddressRange.end | 172.18.165.200 |  |

##### appData

DCIテナント論理インフラのアプリデータ用NWの CIDR、 VLAN ID、使用可能なIPアドレス範囲を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| cidrBlock | 172.18.168.0/24 |  |
| vlanID | 1168 |  |
| ipAddressRange.start | 172.18.168.10 |  |
| ipAddressRange.end | 172.18.168.200 |  |

### 3. KubeadmControlPlane

DCIテナント論理インフラの Control Planeに使用する情報を記載する

| 項目 | 例 | 設定値 | 備考 |
|---|---|---|---|
| name | controlplane |  |  |
| namespace | (Clusterのnamespaceと合わせる) |  |  |
| replicas | 3 |  |  |
| k8s version | v1.34.2（使用する資材と合わせる） |  |  |
| machineTemplate.spec.infrastructureRef.kind | DCIMachineTemplate |  |  |
| machineTemplate.spec.infrastructureRef.name | (DCIMachineTemplateと合わせる) |  |  |
| kubeadmConfigSpec.ntp.servers | 172.18.197.80 |  |  |
| files: kind.pod, spec.containers.env.vip_address | &lt;DCIClusterのcontrolPlaneEndpointと同じ値を設定すること&gt; 例：172.18.165.30 |  |  |
| preKubeadmCommands: CNI_GW | &lt;CNI用NW GW IPアドレス&gt; 例: 172.18.165.251 |  |  |
| preKubeadmCommands: nameserver | &lt;DNS IPアドレス&gt; 例： 8.8.8.8 8.8.4.4 |  |  |
| preKubeadmCommands: KUBERNETES_VERSION | v1.34 |  |  |
| preKubeadmCommands: CRIO_VERSION | v1.34 |  |  |
| preKubeadmCommands:PODS_CIDR | &lt;Podで使用するCIDR&gt; 例：10.245.0.0/16 |  |  |
| preKubeadmCommands:MANAGER_CIDR | &lt;マネージャNWで使用するCIDR&gt; 例：172.18.193.0/24 |  |  |
| preKubeadmCommands:HOST_CIDR | &lt;ホストNWで使用するCIDR&gt; 例：172.18.162.0/24 |  |  |
| preKubeadmCommands:CNI_CIDR | &lt;CNI NWで使用するCIDR&gt; 例：172.18.165.0/24 |  |  |
| TENANT_OPERATOR_CIDR | テナント運用者操作端末のCIDR(FW接続許可に必要) |  | ←アドレス_アカウント情報から |
| BASTION_IP | テナント運用者が踏み台経由でアクセスする場合の踏み台IPアドレス |  | ←アドレス_アカウント情報から |
| LB_VIP | テナントLB用VIP |  | ←アドレス_アカウント情報から（テナント用に採番） |
| POD_CIDR | テナント用Pod CIDR |  |  |
| preKubeadmCommands:HOST_GW | &lt;HOST用NW GW IPアドレス&gt; 例: 172.18.162.251 |  |  |
| RHEL activation-key | xxxxxxx |  |  |
| RHEL organization | 12345678 |  |  |
| kubernetes のパッケージ名 | （インストールするk8sのパッケージ名） |  |  |
| CRI-O のパッケージ名 | （インストールするcri-oのパッケージ名） |  |  |

### 4. KubeadmConfigTemplate

DCIテナント論理インフラの worker nodeに使用する 情報を記載する

| 項目 | 例 | 設定値 | 備考 |
|---|---|---|---|
| name | worker |  |  |
| namespace | (Clusterのnamespaceと合わせる) |  |  |
| ntp.servers | 172.18.197.80 |  |  |
| preKubeadmCommands: PODS_CIDR | &lt;Podで使用するCIDR&gt; 例：10.245.0.0/16 |  |  |
| preKubeadmCommands: SVC_CIDR | &lt;serviceで使用するCIDR&gt; 例：10.96.0.0/12 |  |  |
| preKubeadmCommands: MANAGER_CIDR | &lt;マネージャNWで使用するCIDR&gt; 例：172.18.193.0/24 |  |  |
| preKubeadmCommands: HOST_CIDR | &lt;ホストNWで使用するCIDR&gt; 例：172.18.162.0/24 |  |  |
| preKubeadmCommands: CNI_CIDR | &lt;CNI NWで使用するCIDR&gt; 例：172.18.165.0/24 |  |  |
| preKubeadmCommands: nameserver | 8.8.8.8 8.8.4.4 |  |  |
| preKubeadmCommands: CNI_GW | &lt;CNI用NW GW IPアドレス&gt; 例: 172.18.165.251 |  |  |
| preKubeadmCommands: HOST_GW | &lt;HOST用NW GW IPアドレス&gt; 例: 172.18.162.251 |  |  |
| TENANT_OPERATOR_CIDR | テナント運用者操作端末のCIDR(FW接続許可に必要) |  | ←アドレス_アカウント情報から |
| BASTION_IP | テナント運用者が踏み台経由でアクセスする場合の踏み台IPアドレス |  | ←アドレス_アカウント情報から |
| POD_CIDR | テナント用Pod CIDR |  |  |
| RHEL activation-key | XXXXXXXXX |  |  |
| RHEL organization | 12345678 |  |  |

### 5. DCIMachineTemplate（controlplane）

DCIテナント論理インフラのControl Planeで使用するマシンの情報を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| name | controlplane |  |
| namespace | (Clusterのnamespaceと合わせる) |  |
| location | (構成管理DBのLocationと合わせる） |  |
| serverSpec.type | VM（固定） |  |
| os.distribution | rhel（固定） |  |
| os.version | 9.6-custom（固定） |  |
| minCPU | 4 |  |
| minMemory(MiB) | 32768 |  |
| minStorage(GB) | 80 |  |

### 6. DCIMachineTemplate (worker node1)

DCIテナント論理インフラの worker node1で使用するマシンの情報を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| name | worker-1 |  |
| namespace | (Clusterのnamespaceと合わせる) |  |
| location | (構成管理DBのLocationと合わせる） |  |
| serverSpec.type | COTSServer |  |
| os.distribution | rhel（固定） |  |
| os.version | 9.6-custom（固定） |  |
| gpu.model | NVIDIA-BLACKWELL |  |
| gpu.num | 2 |  |
| nic.model | NVIDIA-CONNECTX-6-DX |  |
| nic.num | 1 |  |

### 7. DCIMachineTemplate (worker node2)

*※必要であれば*

DCIテナント論理インフラの worker node2で使用するマシンの情報を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| name | worker-2 |  |
| namespace | (Clusterのnamespaceと合わせる) |  |
| location | (構成管理DBのLocationと合わせる） |  |
| serverSpec.type | ComposedServer（固定） |  |
| os.distribution | rhel（固定） |  |
| os.version | 9.6-custom（固定） |  |
| gpu.model | NVIDIA-H100-PCIE-80GB |  |
| gpu.num | 1 |  |
| nic.model | NVIDIA-CONNECTX-6-DX |  |
| nic.num | 1 |  |

### 8. MachineDeployment（worker-md-1）

DCIテナント論理インフラの worker node1に使用する情報を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| name | worker-md-1 |  |
| namespace | (Clusterのnamespaceと合わせる) |  |
| clusterName | (Clusterのnameと合わせる) |  |
| replicas | 1 |  |
| selector.matchLabels.cluster.x-k8s.io/cluster-name | clusterNameと同じに設定する |  |
| version | v1.34.2（使用する資材と合わせる） |  |
| infrastructureRef.kind | DCIMachineTemplate |  |
| infrastructureRef.name | worker-1 |  |

### 9. MachineDeployment（worker-md-2）

*※必要であれば*

DCIテナント論理インフラの worker node2に使用する情報を記載する

| 項目 | 例 | 設定値 |
|---|---|---|
| name | worker-md-2 |  |
| namespace | (Clusterのnamespaceと合わせる) |  |
| clusterName | (Clusterのnameと合わせる) |  |
| replicas | 1 |  |
| version | v1.34.2（使用する資材と合わせる） |  |
| infrastructureRef.kind | DCIMachineTemplate |  |
| infrastructureRef.name | worker-2 |  |

Copyright 2026 NTT, Inc.
