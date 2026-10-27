# テナント構築用Kubernetesマニフェストファイル生成ツール

## 概要

本ディレクトリは、DHRC (Dynamic Hardware Resource Control) のDCIテナント論理インフラ（Cluster API + DCI リソース）を構築するための Kubernetes マニフェスト（YAML）を Helm テンプレートで生成するツールです。

`values.yaml` に記述したクラスタ・ネットワーク・ノード設定を読み込み、Kubernetes マニフェストを自動生成してDCIテナント論理インフラ構築に使用します。

**全体の流れ:**

```
values.yaml（ユーザーが環境情報を記述）
       ↓ helm template <マニフェストファイル名> . -f values.yaml | sed '/^# Source: /d' > <マニフェストファイル名>.yaml
<マニフェストファイル名>.yaml（生成されたKubernetesマニフェスト）
```

---

## ソース構成

```
dci_tenant_infra_chart/
├── README.md           # 本ドキュメント
├── Chart.yaml          # Helm チャートのメタデータ（名前・バージョン）
├── values.yaml         # インフラ設定ファイル（ユーザ編集対象）
└── templates/
    └── all.yaml        # Helm テンプレート（マニフェスト生成元）
```

**生成物:**

| ファイル | 説明 |
|---------|------|
| `<マニフェストファイル名>.yaml` | `helm template` コマンドの実行により生成される Kubernetes マニフェスト |

### 各ファイルの説明

| ファイル | 説明 |
|---------|------|
| `values.yaml` | ユーザが編集する環境設定ファイル。クラスタ・ネットワーク・ノード等のインフラ情報を記述する |
| `templates/all.yaml` | Go の `text/template` 構文で書かれたテンプレートファイル。`{{range}}`/`{{if}}` によるループ・条件分岐を含む |
| `Chart.yaml` | Helm チャートのメタデータ（チャート名：`dci-tenant-infra`、バージョン：`0.1.0`） |

---

## 使用の前提条件

**Helm v3 以上** がインストールされていること
   ```bash
   #バージョン確認
   helm version
   ```
   
   ```bash
   #実行例
   $ helm version
   version.BuildInfo{Version:"v3.17.3", GitCommit:"e4da49785aa6e6ee2b86efd5dd9e43400318262b", GitTreeState:"clean", GoVersion:"go1.23.7"}
   ```

---

## 使用前準備

### 1. `values.yaml` の編集

`values.yaml` を環境に合わせて編集します。以下の各セクションを設定します。

| セクション | 説明 |
|-----------|------|
| `cluster` | クラスタ名・ネームスペース |
| `kubernetes` | Pod CIDR・Service CIDR |
| `controlPlane` | CPレプリカ数・拠点・サーバタイプ・OS・暗号化キー・kubeconfig Secret名 |
| `controlPlaneEndpoint` | コントロールプレーンエンドポイント IP アドレス |
| `managerNetwork` | マネージャーネットワーク（CIDR・VLAN ID・IPレンジ） |
| `hostNetwork` | ホストネットワーク（CIDR・VLAN ID・IPレンジ） |
| `cniNetwork` | CNI ネットワーク（CIDR・VLAN ID・IPレンジ） |
| `appDataNetwork` | アプリデータネットワーク（CIDR・VLAN ID・IPレンジ） |
| `kubeVip` | kube-vip の VIP アドレス |
| `ntp` | NTP サーバーリスト |
| `dns` | DNS ネームサーバー・サーチドメイン |
| `rhc` | RHC アクティベーションキー・組織ID |
| `cni` | CNI ゲートウェイ IP アドレス |
| `pbr` | Policy Based Routing 設定（ホスト・CNI 各ネットワークのサブネット・ゲートウェイ） |
| `proxy` | プロキシサーバ設定（オプション） |
| `firewall` | ファイアウォール設定（NodePort・LoadBalancer Service のアクセス制御） |
| `caCertificate` | Harbor ルート CA 証明書（PEM 形式） |
| `worker` | ワーカーノードリスト（GPU・NIC・クラスタオートスケーラー設定） |

**各セクションの詳細**

#### 1-1. `cluster`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `name` | テナントクラスタ名 | `tenant-1` |
| `namespace` | リソース作成先 Namespace | `tenant-1` |

> **⚠ 注意:** `namespace` は `cluster`・`controlPlane`・`worker[].machineDeployment`・`worker[].kubeadmConfigTemplate`・`worker[].machineTemplate` の**合計 5 箇所**に記載されています。テナント名を変更する際はすべて揃えて変更してください。一箇所でも更新漏れがあると、リソースが意図しない Namespace に作成されます。

#### 1-2. `kubernetes`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `podCidr` | Pod に割り当てる CIDR | `192.17.0.0/16` |
| `svcCidr` | Service に割り当てる CIDR | `10.100.0.0/12` |

> **⚠ 注意:**
>- ここに設定するのは **DCIテナント論理インフラに設定する CIDR** です。DCI管理用クラスタに設定済みの CIDR と混同しないよう注意してください。
>- `podCidr` と `svcCidr` は互いに重複しないように設定してください。重複すると Pod 間通信や Service の名前解決が正常に機能しません。また、物理ネットワーク（`managerNetwork` / `hostNetwork` / `cniNetwork` / `appDataNetwork`）の CIDR とも重複しないよう注意してください。

#### 1-3. `controlPlane`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `name` | KubeadmControlPlane リソース名 | `controlplane` |
| `namespace` | リソース作成先 Namespace | `tenant-1` |
| `replicas` | コントロールプレーンノード台数（1 または 3 推奨） | `1` |
| `location` | 拠点識別子 | `dc1` |
| `serverType` | サーバ種別 | いずれかを選択（ComposedServer/COTSServer/VM/ComposedServerOrCOTSServer） |
| `os.distribution` | OS ディストリビューション | `rhel` |
| `os.version` | OS バージョン | `9.6-custom` |
| `minCPU` | 最小 CPU 要件 | （空欄） |
| `minMemory` | 最小メモリ要件 | （空欄） |
| `minStorage` | 最小ストレージ要件 | （空欄） |
| `encryptionKey` | etcd Secret 暗号化キー（base64 エンコード、32 バイト） | 取得方法は下記参照 |
| `secretName` | マネジメント API の kubeconfig を格納した Secret 名 | `management-api-kubeconfig-for-tenant-1` |

> **⚠ 注意:**
>- `secretName` の命名規則は `management-api-kubeconfig-for-<テナント名>` です。`cluster.name` を変更した際は `secretName` も合わせて変更してください。更新漏れがあると Secret の参照に失敗してクラスタが起動しません。
>- `minCPU`、`minMemory`、`minStorage`は、`serverType`が`VM`の場合に限り必須の項目です。それ以外の場合は、空欄で構いません。

**`controlPlane.encryptionKey` の取得方法:**

下記コマンドを実行して表示されたbase64エンコードキーをコピーして取得

```bash
#base64エンコードキー表示
$ head -c 32 /dev/urandom | base64
```

```bash
#実行例
$ head -c 32 /dev/urandom | base64
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 1-4. `controlPlaneEndpoint`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `controlPlaneEndpoint` | コントロールプレーンエンドポイント IP アドレス | `192.168.2.32` |

> **⚠ 注意:** ここに設定するのは **DCIテナント論理インフラに設定する VIP** です。DCI管理用クラスタに設定済みの VIP と混同しないよう注意してください。誤ってDCI管理用クラスタ側の VIP を入力すると、テナントの API サーバーがDCI管理用クラスタを乗っ取る形になり、両クラスタとも正常に動作しなくなります。

#### 1-5. `managerNetwork` / `hostNetwork` / `cniNetwork` / `appDataNetwork`

4 つのネットワークセクションはすべて同一の構造です。

| キー | 説明 | 設定値例（managerNetwork） |
|-----|------|--------------------------|
| `cidrBlock` | ネットワーク CIDR | `192.168.2.0/24` |
| `vlanID` | VLAN ID | `1` |
| `ipRange.start` | IP 割当範囲の開始アドレス | `192.168.2.41` |
| `ipRange.end` | IP 割当範囲の終了アドレス | `192.168.2.49` |

> **⚠ 注意:** `ipRange.start` / `ipRange.end` は必ず対応する `cidrBlock` のアドレス範囲内に収めてください。範囲外のアドレスを設定すると、IP アドレスの払い出しに失敗します。

#### 1-6. `kubeVip`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `address` | kube-vip の VIP アドレス（`controlPlaneEndpoint` と同じ値を設定する） | `192.168.2.32` |

> **⚠ 注意:** `kubeVip.address` は必ず `controlPlaneEndpoint` と**同じ IP アドレス**を設定してください。値が異なると kube-vip が広告する VIP と Kubernetes API サーバーのエンドポイントが一致せず、クラスタが正常に起動しません。また、`controlPlaneEndpoint` と同様に**DCI管理用クラスタ側の VIP と混同しない**よう注意してください。

#### 1-7. `ntp`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `servers[].host` | NTP サーバのホスト名または IP アドレス（複数指定可） | `192.168.2.80` |

#### 1-8. `dns`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `nameserver` | DNS ネームサーバの IP アドレス | `8.8.8.8` |
| `search` | DNS サーチドメイン | `maas` |

#### 1-9. `rhc`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `activationKey` | RHC アクティベーションキー | `example-key` |
| `organization` | Red Hat 組織 ID（文字列として引用符で囲む） | `"12345678"` |

#### 1-10. `cni`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `cidrPrefix` | CNI ネットワークの IP アドレスプレフィックス（**末尾の `.` を含む**） | `192.168.2.` |
| `gateway` | CNI ゲートウェイ IP アドレス | `192.168.2.2` |

#### 1-11. `pbr`（オプション）

このセクション全体はオプションです。記述しない場合、Policy Based Routing は設定されません。

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `hostNW.subnet` | ホストネットワーク側サブネット（CIDR） | `192.168.20.0/24` |
| `hostNW.gateway` | ホストネットワーク側ゲートウェイ IP アドレス | `192.168.20.2` |
| `cniNW.subnet` | CNI ネットワーク側サブネット（CIDR） | `192.168.2.0/24` |

#### 1-12. `proxy`（オプション）

このセクション全体はオプションです。記述しない場合、プロキシ設定（`/etc/environment`・dnf・subscription-manager）は一切行われません。

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `address` | プロキシサーバのホスト名または IP アドレス | `192.168.2.90` |
| `port` | プロキシサーバのポート番号 | `8080` |
| `tenantHarborIP` | テナントの Harbor サーバの IP アドレス（`no_proxy` 除外リストに追加される） | `192.168.2.90` |
| `managerHarborIP` | マネージャの Harbor サーバの IP アドレス（`no_proxy` 除外リストに追加される） | `192.168.2.90` |

> **⚠ 注意:** `address`・`port`・`tenantHarborIP`・`managerHarborIP` の 4 つがすべて揃っている場合のみプロキシ設定が有効になります。1 つでも欠けると設定がスキップされます。

#### 1-13. `firewall`

コントロールプレーンおよびワーカーノードのファイアウォールルールに使用します。NodePort タイプ Service および LoadBalancer タイプ Service へのアクセス元制御に参照されます。

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `tenantOperatorCidr` | テナントオペレータのネットワーク CIDR | `192.168.2.0/24` |
| `bastionIP` | 踏み台サーバの IP アドレスまたは CIDR | `192.168.2.0/22` |
| `loadBalancerVIP` | LoadBalancer タイプ Service に割り当てた VIP | `192.168.2.31` |

> **⚠ 注意:** このセクションは必須です。省略するとマニフェスト生成時にテンプレートエラーが発生します。

#### 1-14. `caCertificate`

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `caCertificate` | Harbor の Root CA 証明書（PEM 形式）。`\|` 記法のブロックスカラーで記述する | `-----BEGIN CERTIFICATE-----` から始まる PEM テキスト |

#### 1-15. `worker`

各ワーカーノード定義はリストの 1 要素です。複数ワーカーを定義する場合はリストに要素を追加します。

| キー | 説明 | 設定値例 |
|-----|------|---------|
| `machineDeployment.name` | MachineDeployment リソース名（リスト内で一意にすること） | `md-worker-1` |
| `machineDeployment.namespace` | リソース作成先 Namespace | `tenant-1` |
| `clusterAutoscaler.nodeGroupMaxSize` | オートスケール時の最大ノード数（省略可） | `2` |
| `clusterAutoscaler.nodeGroupMinSize` | オートスケール時の最小ノード数（省略可） | `1` |
| `clusterAutoscaler.cpu` | ノードの CPU コア数（省略可） | `112` |
| `clusterAutoscaler.memoryG` | ノードのメモリ量（省略可） | `128G` |
| `clusterAutoscaler.diskGi` | ノードのディスク容量（省略可） | `960Gi` |
| `clusterAutoscaler.maxPods` | ノードあたり最大 Pod 数（省略可） | `110` |
| `clusterAutoscaler.gpuCount` | ノードの GPU 数（省略可） | `2` |
| `replicas` | ワーカーノード台数 | `1` |
| `kubeadmConfigTemplate.name` | KubeadmConfigTemplate リソース名 | `kct-worker-1` |
| `kubeadmConfigTemplate.namespace` | リソース作成先 Namespace | `tenant-1` |
| `machineTemplate.name` | DCIMachineTemplate リソース名 | `mt-worker-1` |
| `machineTemplate.namespace` | リソース作成先 Namespace | `tenant-1` |
| `location` | 拠点識別子 | `dc1` |
| `serverType` | サーバ種別 | いずれかを選択（ComposedServer/COTSServer/VM/ComposedServerOrCOTSServer） |
| `os.distribution` | OS ディストリビューション | `rhel` |
| `os.version` | OS バージョン | `9.6-custom` |
| `minCPU` | 最小 CPU 要件 | （空欄） |
| `minMemory` | 最小メモリ要件 | （空欄） |
| `minStorage` | 最小ストレージ要件 | （空欄） |
| `gpu.model` | GPU モデル名 | `NVIDIA-TESLA-T4-PCIE-16GB` |
| `gpu.num` | GPU 搭載数 | `1` |
| `nic.model` | NIC モデル名 | `NVIDIA-CONNECTX-5f` |
| `nic.num` | NIC 搭載数 | `1` |

> **⚠ 注意:**
>- 複数ワーカーを定義する場合、`machineDeployment.name`・`kubeadmConfigTemplate.name`・`machineTemplate.name` はリスト内で**すべて一意**にしてください。同じ名前が重複すると、既存リソースに上書き適用され意図しない設定になります。
>- `clusterAutoscaler` はNodeのオートスケールを有効にする場合の設定項目でオプションです。記述した場合、MachineDeployment に Cluster Autoscaler 用アノテーションが付与されます。有効にしない場合は項目ごと削除します。
>- `kubeadmConfigTemplate.name` などにテナント名や番号を含めない汎用的な名前（例: `worker`）を使うと、同一DCI管理用クラスタに複数テナントを展開した際に名前が衝突します。`kct-<テナント名>-worker-1` のようにテナントを識別できる名前にしてください。
>- `minCPU`、`minMemory`、`minStorage`は、`serverType`が`VM`の場合に限り必須の項目です。それ以外の場合は、空欄で構いません。

**`worker` セクションのリスト形式:**

ワーカーノードを複数定義する場合は、`worker:` リストに要素を追加します。1台のみの場合でも必ずリスト形式で記述してください。

```yaml
worker:
  - machineDeployment:
      name: worker-md-1
      namespace: default
    replicas: 1
    location: dc1
    serverType: COTSServer
    gpu:
      model: NVIDIA-H100-PCIE-80GB
      num: 1
    nic:
      model: NVIDIA-CONNECTX-6-DX
      num: 1
    # 必要に応じて worker-md-2 以降を追加
  - machineDeployment:
      name: worker-md-2
      namespace: default
    replicas: 1
    ...
```

---

## 使用方法

### 1. Kubernetes マニフェストを生成する

```bash
helm template <マニフェストファイル名> . -f values.yaml | sed '/^# Source: /d' > <マニフェストファイル名>.yaml
```

例：マニフェストファイル名が `tenant-a` の場合

```bash
helm template tenant-a . -f values.yaml | sed '/^# Source: /d' > tenant-a.yaml
```

> **補足:** `sed '/^# Source: /d'` は `helm template` が自動付与するコメント行（`# Source: templates/all.yaml`）を除去します。

正常に生成されると <マニフェストファイル名>.yaml がカレントディレクトリに出力されます。この YAML を kubectl apply することで、以下の Kubernetes リソースが作成されます。

| リソース種別 | 説明 |
|------------|------|
| `Cluster` | Cluster API のクラスタリソース |
| `DCICluster` | DCI 固有のクラスタインフラリソース（ネットワーク設定含む） |
| `KubeadmControlPlane` | コントロールプレーン設定（kubeadm・kube-vip・auditd 等） |
| `MachineDeployment` | ワーカーノードのデプロイ設定 |
| `DCIMachineTemplate` | DCI 固有のマシンテンプレート（GPU・NIC 仕様） |
| `KubeadmConfigTemplate` | ワーカーノード用 kubeadm 設定テンプレート |

---

## トラブルシューティング

**Q: `helm template` でエラーが発生する**

A: 以下を確認してください。
- Helm のバージョンが v3 以上であるか（`helm version`）
- カレントディレクトリが `dci_tenant_infra_chart/` であるか
- `values.yaml` が存在し、YAML 構文が正しいか（インデント・コロン等）
- `templates/all.yaml` および `Chart.yaml` が同一ディレクトリに存在するか

**Q: 生成した YAML の設定値が正しく反映されない**

A: `values.yaml` を修正した後、`helm template` コマンドを再実行して YAML を再生成してください。`values.yaml` を編集した後は必ず再生成が必要です。

**Q: ワーカーノードを複数定義したい**

A: `values.yaml` の `worker:` セクションはリスト形式のため、要素を追加するだけで複数ワーカーを定義できます。`worker-md-1`、`worker-md-2` のように `machineDeployment.name` が一意になるよう設定してください。
