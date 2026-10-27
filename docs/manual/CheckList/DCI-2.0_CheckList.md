# DCI-2.0 チェックリスト（DCI管理用クラスタ構築前）

DCI運用者が DCI管理用クラスタを構築する前のチェックリストです。

各項目を確認したら、チェックボックスにチェックを入れてください。

## 操作端末

### DCI運用者用

- [ ] DCI運用者が操作する端末(RHEL推奨)は準備されているか

## DCI管理用サーバ

### BIOS

- [ ] **システムボード**: ハードウェア(CPU,PCIバスエラーなど)が発生していないか
- [ ] **IPMI/BMC**: IPMIのIPアドレス,GWは設定されているか

### OS

- [ ] **RHEL9.6**: DCI管理用サーバへインストール& RHELサブスクリプション登録済か
  - Control Plane用 x3台
  - k8s node用 x2台
  - MAASサーバ用 x1台

### サービス

- [ ] **firewalld**: firewalldサービスは停止状態か
- [ ] **DNS**: DNSサーバ利用可能か（名前解決・外部アクセス可能か）
- [ ] **NTP**: NTPサーバが利用可能か（時刻同期設定可能か）

## PG-CDI

### CDI機器

- [ ] **システム構築**: CDI機器が接続され、セットアップ完了しているか
  - 管理サーバ
  - CDI管理ソフトウェア
  - Director
  - Fabric SW+ ・PCI-BOX
  - 計算サーバ
  - CDIクライアントPC

### CDI管理ソフト

- [ ] **設定確認**: CDI管理ソフト(Guest OS)が起動されているか
- [ ] **設定確認**: CDI管理ソフト(Guest OS)のcdiadminのhomeディレクトリに hhchk.cfgファイルが存在するか

### LinuxクライアントPC

- [ ] **設定確認**: VM作成・クライアントPC立ち上がっているか
- [ ] **設定確認**: expectインストールされているか
- [ ] **設定確認**: cdictlのPath設定(シンボリックリンク)されているか
- [ ] **設定確認**: cdictlでリソースgroup0設定されているか
- [ ] **設定確認**: DHRCコンポーネント用ユーザ dhrcsystem が作成されているか

## NW機器

### SW全般

- [ ] **管理用ポート**: IPアドレス,GWは設定されているか

### L2 SW

- [ ] **HOST用, CNI用, APPDATA用**: DHRCから操作対象とするポートはVLAN(デフォルトVLAN含む)設定されていないか（VLAN削除されているか）
- [ ] **HOST用, CNI用, APPDATA用**: 接続されているポートは LLDP有効になっているか

### L3 SW

- [ ] **マネージャ⇔テナント間**: ACL/VLANルーティング設定済か
- [ ] **テナント⇔テナント間**: 異なるテナントのVLAN間はルーティング設定されていない（NW分離されている）か

## MAAS

### MAAS3.6.x

- [ ] **サーバ**: MAASサーバ構築済で、MAAS GUIにアクセス可能か
- [ ] **OS image**: MAASにRHEL9.6 OSカスタムイメージ登録済か
- [ ] **DHCP**: マネージャ用NW(NIC1) Subnet設定/DHCP有効か、static DHCP leasesで固定アドレス設定済か
- [ ] **DHCP**: 動的IPアドレス割当の場合、DHCP Dynamic reserved range設定されているか
- [ ] **DHCP**: VM用フリープールの設定(DHCP reserved rangeから除外)されているか

## DCIテナント論理インフラ用リソース

### COTSサーバ

- [ ] **IPMI/BMC（iDRAC / iRMC など GUIで設定）**: IPMIオーバーLAN有効化されているか

### Composedサーバ

- [ ] **IPMI/BMC（iDRAC / iRMC など GUIで設定）**: redfish有効化されているか
- [ ] **BIOS設定**: マネージャ用NICがPXEboot有効になっているか
- [ ] **BIOS設定**: Boot順：マネージャ用NIC1がPXEbootで最初になっているか
- [ ] **BIOS設定**: SR-IOVが有効になっているか

## ネットワーク疎通確認

### マネージャ用NW

- [ ] **IPMI/BMC用NIC**: 操作端末からセットアップした全機器とのping疎通OKか
- [ ] **HW管理用NIC**: 操作端末からセットアップした全機器とのping疎通OKか
- [ ] **HW管理用NIC**: マネージャ用NWから外部（Internet）と接続可能か

## 外部ストレージ

### PV用

- [ ] **NFS**: NFSサーバが利用可能か
- [ ] **NFS**: NFSサーバは no_root_squash 設定されているか

### バックアップ用

- [ ] **S3互換**: バックアップストレージとしてMinIOが利用可能か

Copyright 2026 NTT, Inc.
