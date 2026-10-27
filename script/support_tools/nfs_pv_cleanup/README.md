# nfs_pv_cleanup/README.md

## 概要
このディレクトリは、削除したテナントのPVで使用されていたNFSサーバ上のデータを削除するスクリプトです。  
作業者端末からAnsible SSH経由でNFSサーバに接続して実行します。

---

## ソース構成
```
nfs_pv_cleanup/
├── README.md               # 本ドキュメント
├── nfs_pv_cleanup.sh       # メイン実行スクリプト
├── inventory.ini           # NFSサーバのインベントリ
├── vars.yaml               # 削除対象テナントのNFS設定
└── nfs_pv_cleanup.yaml     # Playbook（NFSデータ削除）
```

---

## 使用の前提条件
1. NFSサーバへのSSH接続が可能であること
2. [`tenant_delete`](../../tenant_delete/README.md) スクリプトの実行が完了していること（Playbook 01 によるテナント論理インフラ削除後、NFSデータが孤立した状態になってから実行すること）

---

## 使用前準備

### 1. `inventory.ini` の編集

NFSサーバのIPアドレスとユーザ名、パスワードを実環境に合わせて編集します。
* 初期状態では、パスワード項目は ***** のマスク値で登録されています。
* 実運用時は、各環境の実値に置き換えてください。

```ini
[nfs_servers]
nfs-server01 ansible_host=192.168.2.xxx ansible_user=cloud-user ansible_password="******" ansible_become_password="******"
```

### 2. `vars.yaml` の編集

削除対象テナントのnamespaceと、NFSサーバ上のエクスポートパスを設定します。  
`nfs_server_export_path` は、テナントプロビジョニング時に `nfs-subdir-external-provisioner.yaml` の `path:` に設定した値と同じ値を指定してください。

```yaml
tenants:
  - tenant_namespace: f01-tenant-1
    nfs_server_export_path: "/export/nfs/f01-tenant-1"
```

---

## 実行方法

```bash
cd support_tools/nfs_pv_cleanup/
```

### NFSデータ削除

```bash
bash ./nfs_pv_cleanup.sh
```

### 削除対象ディレクトリの確認

実行前にNFSサーバにSSHログインして削除対象を確認できます。

```bash
# NFSサーバにSSHログイン
ssh <ansible_user>@<ansible_host>

# 削除対象ディレクトリの内容確認
sudo ls -la <nfs_server_export_path>/
```

---

## 動作仕様

- `vars.yaml` の `tenants` リストに定義されたテナントを順番に処理します
- 各テナントの `nfs_server_export_path` 配下のデータをすべて削除します（`rm -rf <path>/*`）
- `nfs_server_export_path` で指定したディレクトリ自体は削除されません（配下のデータのみ削除）
- 対象ディレクトリが空の場合はエラーなく正常終了します
