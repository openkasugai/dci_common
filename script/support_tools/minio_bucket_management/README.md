# minio_bucket_management/README.md

## 概要
このディレクトリは、MinIOサーバ上のバケットをAnsible SSH経由で作成・削除するスクリプトです。
作業者端末からAnsible SSH経由でMinIOサーバに接続して実行します。

---

## ソース構成
```
minio_bucket_management/
├── README.md                       # 本ドキュメント
├── minio_bucket_management.sh      # メイン実行スクリプト
├── inventory.ini                   # MinIOサーバのインベントリ
├── vars.yaml                       # MinIO接続設定とバケット名リスト
├── minio_bucket_create.yaml        # Playbook（バケット作成）
└── minio_bucket_delete.yaml        # Playbook（バケット削除）
```

---

## 使用の前提条件
1. 事前準備（バックアップストレージ）のMinIOのインストールが完了していること

---

## 使用前準備

### 1. `inventory.ini` の編集

MinIOサーバのIPアドレスとユーザ名、パスワードを実環境に合わせて編集します。
* 初期状態では、パスワード項目は ***** のマスク値で登録されています。
* 実運用時は、各環境の実値に置き換えてください。

```ini
[minio_servers]
minio-server01 ansible_host=192.168.2.105 ansible_user=cloud-user ansible_password="******" ansible_become_password="******"
```

### 2. `vars.yaml` の編集

MinIOの接続設定と、作成/削除するバケット名を設定します。

```yaml
minio_network: "kes-net"
minio_image: "minio/mc:RELEASE.2024-08-17T11-33-50Z"
minio_alias: "local"
minio_endpoint: "http://minio:9000"
```

`buckets` には作成/削除するバケット名をフルネームで列挙してください。
用途に応じて以下のいずれかを参考に、実環境のバケット名を設定します。

**冗長化構成のLoki向けの場合:**

Lokiバケットを作成します。

```yaml
buckets:
  - "loki"
  - "loki-ruler"
  - "loki-admin"
```

**テナント用Loki/Velero向けの場合:**

Lokiは `<prefix>-<テナント識別子>`・`<prefix>-<テナント識別子>-admin`・`<prefix>-<テナント識別子>-ruler` の3つ、
Veleroは `<velero-bucket-name>` の1つが対象となります。

```yaml
buckets:
  - "loki-f01-tenant-1"
  - "loki-f01-tenant-1-admin"
  - "loki-f01-tenant-1-ruler"
  - "test-velero-bucket-f01-tenant-1"
```

MinIOの認証情報を設定します。
* 初期状態では、パスワード項目は ***** のマスク値で登録されています。
* 実運用時は、各環境の実値に置き換えてください。

```yaml
minio_user: "minio"          # MinIOアクセスキー（ユーザ名）
minio_password: "*****"      # MinIOシークレットキー（パスワード）
```

## 実行方法

```bash
cd support_tools/minio_bucket_management/
```

### バケット作成

```bash
bash ./minio_bucket_management.sh create
```

### バケット削除

```bash
bash ./minio_bucket_management.sh delete
```

### バケット状態確認

バケットの一覧と状態を確認する場合は、MinIOサーバに直接SSHしてdockerコマンドを実行します。

```bash
# MinIOサーバにSSHログイン
ssh <ansible_user>@<ansible_host>

# バケット一覧を確認
sudo docker run --rm --network <minio_network> \
  --entrypoint sh <minio_image> -c \
  "mc alias set <minio_alias> <minio_endpoint> <minio_user> <minio_password> && mc ls <minio_alias>"
```

`vars.yaml` の設定値を使用した実行例:

```bash
sudo docker run --rm --network kes-net \
  --entrypoint sh quay.io/minio/mc:RELEASE.2024-08-17T11-33-50Z -c \
  "mc alias set local http://minio:9000 minio minio123 && mc ls local"
```

---

## 動作仕様

- 対象バケットが存在しない場合の作成はスキップされます（冪等性あり）
- 対象バケットが存在しない場合の削除はスキップされます（冪等性あり）
- MinIOサーバ上で `sudo docker run quay.io/minio/mc` を実行し、`mc` コマンドでバケット操作を行います
- `kes-net` Docker ネットワーク内の `minio` ホスト名で MinIO に接続します
