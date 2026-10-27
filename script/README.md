# README.md

## 概要
このディレクトリは、DCI-2.0 の管理基盤構築からテナント構築・削除までを自動化するスクリプト群です。

主な目的は以下です。
- 構築作業の所要時間を短縮する
- 手作業による設定ミスを減らす
- 実行ログと診断結果を残し、再実行しやすくする

## 対象範囲
本スクリプト群は、主に以下の作業を自動化します。
- DCI管理用クラスタ構築
- DCI管理用クラスタへの構成品配備
- DCIテナント論理インフラ構築
- DCIテナント論理インフラへの構成品配備
- DCIテナント論理インフラ削除

## 全体実行フロー

### 使用前準備
```text
インベントリファイル設定・編集
バージョン設定・編集
ネットワーク設定・編集
ホスト固有設定・編集
```

使用前準備の具体的な設定手順は、各ディレクトリREADMEを参照してください。

### DCI管理用クラスタ構築フロー
```text
manager_cluster_setup
  -> manager_software_deploy
```

### テナント構築フロー
```text
tenant_provisioning
  -> tenant_deploy
```

### テナント削除フロー
```text
tenant_delete
  -> (必要に応じて) support_tools/minio_bucket_management delete
  -> (必要に応じて) support_tools/nfs_pv_cleanup
```

## ディレクトリ構成と役割

| ディレクトリ | 役割 | メインスクリプト | 詳細 |
|---|---|---|---|
| manager_cluster_setup | 管理用Kubernetesクラスタ構築 | manager_cluster_setup.sh | [manager_cluster_setup/README.md](manager_cluster_setup/README.md) |
| manager_software_deploy | 管理用クラスタへの構成品配備 | manager_software_deploy.sh | [manager_software_deploy/README.md](manager_software_deploy/README.md) |
| tenant_provisioning | テナント論理インフラ構築 | tenant_provisioning.sh | [tenant_provisioning/README.md](tenant_provisioning/README.md) |
| tenant_deploy | テナント論理インフラへの構成品配備 | tenant_deploy.sh | [tenant_deploy/README.md](tenant_deploy/README.md) |
| tenant_delete | テナント論理インフラ削除 | tenant_delete.sh | [tenant_delete/README.md](tenant_delete/README.md) |
| support_tools | 事前準備・診断・MinIO補助・NFS PVクリーンアップツール | 各サブディレクトリ参照 | 下記参照 |

## support_tools の使い分け

- pre_setup_tools/data_collect_tools
  - MAAS/CDI情報を収集し、構成管理DB向け入力ファイルを生成
  - 詳細: [support_tools/pre_setup_tools/data_collect_tools/README.md](support_tools/pre_setup_tools/data_collect_tools/README.md)

- pre_setup_tools/configuration_management_database
  - 構成管理DB登録用の生成ツール
  - 詳細: [support_tools/pre_setup_tools/configuration_management_database/README.md](support_tools/pre_setup_tools/configuration_management_database/README.md)

- pre_setup_tools/dci_tenant_infra_chart
  - テナント論理インフラ定義ファイル作成補助
  - 詳細: [support_tools/pre_setup_tools/dci_tenant_infra_chart/README.md](support_tools/pre_setup_tools/dci_tenant_infra_chart/README.md)

- diagnosis
  - 各スクリプトの実行結果診断とサマリー出力
  - 詳細: [support_tools/diagnosis/README.md](support_tools/diagnosis/README.md)

- minio_bucket_management
  - MinIOバケット作成/削除
  - 詳細: [support_tools/minio_bucket_management/README.md](support_tools/minio_bucket_management/README.md)

- nfs_pv_cleanup
  - 削除したテナントのPVで使用されていたNFSサーバ上のデータを削除
  - 詳細: [support_tools/nfs_pv_cleanup/README.md](support_tools/nfs_pv_cleanup/README.md)

## 共通前提条件
実行前に、少なくとも以下を満たしてください。
- 操作端末に Ansible 2.14.18 以上が導入済み
- 対象ノードへ SSH 鍵認証で接続可能
- 対象ノードで sudo のパスワードレス実行が可能
- 操作端末に Git が導入済み
- 対象ノードに想定OSが導入済みで、必要なサブスクリプション登録が完了

## 実行時のルール
- スクリプトは決められた順序で実行してください
- 失敗時は設定を修正して再実行してください
- 実行ログは各ディレクトリの ansible/logs 配下で確認してください

## 実行例（manager_cluster_setup）
以下は、管理用クラスタ構築スクリプトを実行し、診断まで行う一連の実行例です。

この実行例で分かることは以下です。
- スクリプト起動からPlaybook完了までの基本的な流れ
- 実行ログの確認方法
- diagnosisツールの実行方法

```bash
cd dci_common/script
ls -1
```

```bash
cd manager_cluster_setup
bash manager_cluster_setup.sh
```

```bash
cd ../support_tools/diagnosis
./diagnosis.sh manager_cluster_setup --script-root ../..
```

## 補足
このREADMEは全体像の把握を目的とした要約です。
各設定値、Vault、Playbook単位の詳細は各ディレクトリのREADMEを参照してください。
