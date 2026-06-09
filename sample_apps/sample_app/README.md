# APFWスタブアプリ
本アプリはnixl_communicatorを用いてDCIアプリの接続機能と処理機能の間でGPU Direct RDMA通信を行うものである。

目次
- [APFWスタブアプリ](#apfwスタブアプリ)
  - [APFWスタブアプリの機能](#apfwスタブアプリの機能)
  - [使い方](#使い方)
    - [コンテナイメージの作成方法](#コンテナイメージの作成方法)
    - [APFWスタブアプリの配備](#apfwスタブアプリの配備)
    - [APFWスタブアプリ間の通信](#apfwスタブアプリ間の通信)
    - [HTTPインターフェース](#httpインターフェース)
      - [1.statusチェックの実行](#1statusチェックの実行)
      - [2.metricsチェックの実行](#2metricsチェックの実行)
      - [3.metrics/prometheusチェックの実行](#3metricsprometheusチェックの実行)
      - [4.health/liveチェックの実行](#4healthliveチェックの実行)
      - [5.health/readyチェックの実行](#5healthreadyチェックの実行)
    - [ログの確認](#ログの確認)
    - [接続先参照の切り替え(設定ファイル or Service名で名前解決)](#接続先参照の切り替え設定ファイル-or-service名で名前解決)
  - [テストデータを用いた通信の実行例](#テストデータを用いた通信の実行例)
    - [接続パターン](#接続パターン)
      - [接続パターン1](#接続パターン1接続機能から1つの処理機能への通信)
      - [接続パターン2](#接続パターン2送受信の両方を行う接続機能を含む通信)
      - [接続パターン3](#接続パターン3接続機能から2つの処理機能への分岐を持つ通信)
      - [接続パターン4](#接続パターン4レプリカ機能を持つ2つの接続機能から2つの処理機能への同時通信)
    - [前提](#前提)
    - [事前準備](#事前準備)
      - [1. NICCluesterPolicyの配備とSRIOV Device Pluginのリスタート](#1-niccluesterpolicyの配備とsriov-device-pluginのリスタート)
      - [2. ノードのMIGインスタンス用リソースのResourceClaimTemplateの配備](#2-ノードのmigインスタンス用リソースのresourceclaimtemplateの配備)
      - [3. ノードのDataPlane用NICのVF用のHost Device Networkの配備](#3-ノードのdataplane用nicのvf用のhost-device-networkの配備)
      - [4. 通信パターンとデータ転送の方向の指定](#4-通信パターンとデータ転送の方向の指定)
    - [実施](#実施)

---

## APFWスタブアプリの機能
App/scripts配下のスクリプトの以下を用いてnixl_communicatorによるGPU Direct RDMA通信を行う
- client.py：DCIアプリの接続機能。設定ファイルに従い処理機能や後段の接続機能に接続する。
  - 起動コマンドの引数によりnixl_communicatorに渡す引数(DRAM/VRAM、READ/WRITE)を読み込む
    - ※テストデータはDRAM、WRITEのパターンのみ格納しており、詳細は/App/nixl-communicator/README.mdを参照
  - SIGHUPシグナルを受けるとイニシエーターとしてnixl_communicatorを呼出す
  - statusチェックを行う
  - metricsチェックを行う
  - metrics/prometheusチェックを行う
  - health/liveチェックを行う
  - health/readyチェックを行う
- server.py：DCIアプリの処理機能。接続機能から接続される。
  - 起動コマンドの引数によりnixl_communicatorに渡す引数(DRAM/VRAM、READ/WRITE)を読み込む
    - ※テストデータはDRAM、WRITEのパターンのみ格納しており、詳細は/App/nixl-communicator/README.mdを参照
  - nixl_communicatorのターゲットとしてnixl_communicatorを呼出す
  - statusチェックを行う
  - metricsチェックを行う
  - metrics/prometheusチェックを行う
  - health/liveチェックを行う
  - health/readyチェックを行う
- server_client.py：DCIアプリの2段目以降の接続機能。設定ファイルに従い処理機能や後段の接続機能に接続する。前段の接続機能から接続される。
（前段から接続される際はターゲットとして、処理機能に接続する際はイニシエーターとして動作する。）
  - 起動コマンドの引数によりnixl_communicatorに渡す引数(DRAM/VRAM、READ/WRITE)を読み込む
    - ※テストデータはDRAM、WRITEのパターンのみ格納しており、詳細は/App/nixl-communicator/README.mdを参照
  - nixl_communicatorのターゲットとしてnixl_communicatorを呼出す
  - SIGHUPシグナルを受けるとイニシエーターとしてnixl_communicatorを呼出す
  - statusチェックを行う
  - metricsチェックを行う
  - metrics/prometheusチェックを行う
  - health/liveチェックを行う
  - health/readyチェックを行う
- common.py：各機能関数をまとめたファイル
- nixl_communicator：DCIアプリから呼出されてGPU Direct RDMA通信を実行する。
  App/nixl-communicatorにて作成される実行ファイルを使用する。
  - ※Multus CNIの追加インターフェイスの命名規則により、Podの2nd NICの名前は"net1"を想定。


## 使い方
### コンテナイメージの作成方法
1. APFWスタブアプリのコンテナイメージ作成
```bash
$ cd ./App/
$ sudo buildah bud -t sample-app:ut .
```

### APFWスタブアプリの配備
接続機能、処理機能用のPodを配備する。

### APFWスタブアプリ間の通信
1. 設定ファイル(DCIアプリ制御用情報)の格納
接続機能用Podの特定のディレクトリ(/app-conn-control-info-manager-dci/)に設定ファイル(appConnectControlInfo.yaml)を格納する
```bash
kubectl cp -n dci <設定ファイルのファイルパス>  <接続機能用Podの名前>:/app-conn-control-info-manager-dci/appConnectControlInfo.json
```
2. nixl_communicatorの実行
SIGHUP送信先プロセスIDの取得
```bash
kubectl exec -n dci <接続機能用Podの名前> -- pgrep -f "client.py"
```
接続機能用PodにSIGHUPを送る
```bash
kubectl exec -n dci <接続機能用Podの名前> -- kill -SIGHUP <プロセスID>
```


### HTTPインターフェース
/status, /metrics, /metrics/prometheus, /health/live, /health/readyにアクセス可能
#### 1.statusチェックの実行

localhost:80/statusにアクセスする
```bash
kubectl exec -n dci <接続機能用Podの名前> -- curl -X GET http://localhost:80/status | jq .
```
なお、実行中はコンテナ内の/work/interfaces/http/status.jsonというファイルを参照して結果を返しており、ビルド前では下記ファイルが対象。
> ./test/interfaces/http/json/status.json

以下はHTTP/GETの応答例。
- ファイルが存在する
  - ファイル内容を返す(デフォルト値)
  ```bash
  {
    "name": "hoge",
    "status": "PROCESSING",
    "statuses": {
        "compo1": "IDLE",
        "compo2": "PROCESSING"
    },
    "metas": {
        "aaa": "AAA"
    },
    "terminating": false
  }
    ```
  - 辞書型ではないならば下記を返す
  ```bash
  {"data": ファイル内容}
  ```
- ファイルが存在しない
  ```bash
  {
    "name": "No_File", 
    "status": "NotReady", 
    "statuses": [], 
    "metas": [], 
    "terminating": True
  }
  ```
- ファイル取得エラーのとき
  ```bash
  {
    "name": "Something_Went_Wrong", 
    "status": "NotReady", 
    "statuses": [], 
    "metas": [], 
    "terminating": True
  }
  ```

#### 2.metricsチェックの実行
localhost:80/metricsにアクセスする
```bash
kubectl exec -n dci <接続機能用Podの名前> -- curl -X GET http://localhost:80/metrics | jq .
```
なお、実行中はコンテナ内の/work/interfaces/http/metrics.jsonというファイルを参照して結果を返しており、ビルド前では下記ファイルが対象。
> ./test/interfaces/http/json/metrics.json

以下はHTTP/GETの応答例。
- ファイルが存在する
  - ファイル内容を返す(デフォルト値)
  ```bash
  {
    "xxx": "1",
    "yyy": "2"
  }
  ```
- ファイルが存在しない
  ```bash
  {"metrics": "No_File"}
  ```
- ファイル取得エラーのとき
  ```bash
  {"metrics": "Something_Went_Wrong"}
  ```

#### 3.metrics/prometheusチェックの実行
localhost:80/metrics/prometheusにアクセスする
```bash
kubectl exec -n dci <接続機能用Podの名前> -- curl -X GET http://localhost:80/metrics/prometheus
```
なお、実行中はコンテナ内の/work/interfaces/http/prometheus.jsonというファイルを参照して結果を返しており、ビルド前では下記ファイルが対象。
> ./test/interfaces/http/json/prometheus.json

以下はHTTP/GETの応答例。
- ファイルが存在する
  - ファイル内容を返す(デフォルト値)
  ```bash
  # HELP xxx Xxx
  # TYPE xxx gauge
  xxx{state="1"} 1
  # HELP yyy Yyy
  # TYPE yyy gauge
  yyy{state="2"} 1
  ```
- ファイルが存在しない
  ```bash
    # HELP app_state Application state
    # TYPE app_state gauge
    app_state{state="NotReady"} 1
    # HELP processing_total Total processing tasks
    # TYPE processing_total gauge
    processing_total 0
  ```
- ファイル取得エラーのとき
  ```bash
    # HELP app_state Application state
    # TYPE app_state gauge
    app_state{state="Error"} 1
    # HELP processing_total Total processing tasks
    # TYPE processing_total gauge
    processing_total 0
  ```　

#### 4.health/liveチェックの実行

localhost:80/health/liveにアクセスする
```bash
kubectl exec -n dci <接続機能用Podの名前> -- curl -X GET http://localhost:80/health/live
```
なお、実行中はコンテナ内の/work/interfaces/http/healthLive.txtというファイルを参照して結果を返しており、ビルド前では下記ファイルが対象。
> ./test/interfaces/http/text/healthLive.txt

- ファイル内容にかかわらず何も返さない。常に下記のステータスコードを返却する。
 ```bash
 200 OK
```

#### 5.health/readyチェックの実行
localhost:80/health/readyにアクセスする
```bash
kubectl exec -n dci <接続機能用Podの名前> -- curl -X GET http://localhost:80/health/ready
```
なお、実行中はコンテナ内の/work/interfaces/http/healhReady.txtというファイルを参照して結果を返しており、ビルド前では下記ファイルが対象。
> ./test/interfaces/http/text/healthReady.txt

- ファイル内容が200であれば、下記のステータスコードを返却する。
  ```bash
  200 OK
  ```
- ファイル内容が200以外または取得エラーならば下記のステータスコードを返却する。
  ```bash
  503 Service Unavailable
  ```

### ログの確認
コマンド:
```bash
kubectl logs -n dci <コンテナ名>
```

nixl_communicatorの実行結果や、HTTP/GETの結果がロギングされる
- 通信に成功するとWRITEの場合イニシエーター側に以下のログが出力される
  ```bash
  XX:16:57.790621892  37 nixl_communicator.cpp:602] Transfer completed and Buffers match with Remote
  XX:16:57.790622737  37 nixl_communicator.cpp:603] UCX Transfer Success!!!
  ```
- HTTP/GETのログは以下のように出力される
  ```bash
  2025-10-20 12:08:25,473 INFO: [HTTP RECV] method=GET url=http://localhost/status client=127.0.0.1 req_len=0
  2025-10-20 12:08:25,473 INFO: [Status Check] Received request
  2025-10-20 12:08:25,473 INFO: [HTTP RESP] method=GET url=http://localhost/status client=127.0.0.1 req_len=0 resp_len=130 duration_ms=0.64 status=200
  ```
  ```bash
  2025-10-20 12:08:12,062 INFO: [HTTP RECV] method=GET url=http://182.168.5.20:80/health/ready client=192.168.10.39 req_len=0
  2025-10-20 12:08:12,063 INFO: [Health Check] /health/ready
  2025-10-20 12:08:12,063 WARNING: Text file not found: /work/interfaces/http/healthReady.txt
  2025-10-20 12:08:12,063 INFO: [HTTP RESP] method=GET url=http://182.168.5.20:80/health/ready client=192.168.10.39 req_len=0 resp_len=0 duration_ms=0.63 status=503
  ```

### 接続先参照の切り替え(設定ファイル or Service名で名前解決)
環境変数"USE_DNS"で切り替える
  - trueのとき
    - Service名で名前解決
  - falseのとき
    - 設定ファイル参照

環境変数の指定はマニフェストで行う
```bash
$ more ./test/yaml/TestYaml/1node/dciapp-perftest-conn-x1_node01-mig.yaml
apiVersion: v1
kind: Pod
metadata:
  name: dciapp-perftest-conn-x1
  namespace: dci
  annotations:
    k8s.v1.cni.cncf.io/networks: |
      [{
        "name": "demo-network1",
        "ips": ["192.0.2.200/24"]
      }]
spec:
  shareProcessNamespace: true
  containers:
  - name: sample-app
    image: localhost/sample-app:ut
    imagePullPolicy: Never
    command: ["python3", "client.py", "DRAM", "WRITE"]
    env:
    - name: USE_DNS
      value: "false" ★
    securityContext:
      capabilities:
        add: ["NET_RAW", "IPC_LOCK"]
```

なお、Service名で名前解決する場合は以下のyamlをapplyしておくこと

```bash
kubectl apply -f service.yaml
kubectl apply -f endpointslice.yaml
```

<br>

## テストデータを用いた通信の実行例
./test/yaml/TestYaml配下のテストデータを用いてAPFWスタブアプリを実行する場合の手順を以下に示す。
### 接続パターン
TestYamlで用意している接続パターンは以下の4つになる
+ #### 接続パターン1：接続機能から1つの処理機能への通信
    ```bash
      接続機能X->処理機能A
    ```
+ #### 接続パターン2：送受信の両方を行う接続機能を含む通信
    ```bash
      接続機能X->接続機能Y->処理機能A
    ```
+ #### 接続パターン3：接続機能から2つの処理機能への分岐を持つ通信
    ```bash
      接続機能X┬>処理機能A
  　　　  　 └>処理機能B
    ```
+ #### 接続パターン4：レプリカ機能を持つ2つの接続機能から2つの処理機能への同時通信

    ```bash
      接続機能X1┬>処理機能A1
      接続機能X2┴>処理機能A2 
    ```

また、テストの実施環境として、以下のパターンとした
+ 1Node構成：全ての機能を単一のk8s Nodeに配備して、APFWスタブアプリの通信は全て1台のK8s Node内に閉じる
  + 1台目のK8s node(node01)ではNVIDIA GPUをMIGインスタンスにして各機能のPodに配備する



### 前提
+ a. K8s NodeにMIGインスタンスを作成可能なNVIDIA GPUを搭載していること
+ b. NVIDIA Network Operaterを配備していること
+ c. SR-IOV CNIを配備していること
+ d. GPU Operatorを配備していること
+ e. k8s-dra-driver-gpuを配備していること
+ f. K8s NodeにMIGを設定していること


### 事前準備
#### 1. NICCluesterPolicyの配備とSRIOV Device Pluginのリスタート
```bash
$ cd ./test/yaml/TestYaml/common/
$ kubectl apply -f nic-cluster-policy_demo-app_ct.yaml
$ kubectl rollout restart ds network-operator-sriov-device-plugin -n nvidia-network-operator
```


#### 2. ノードのMIGインスタンス用リソースのResourceClaimTemplateの配備
```bash
$ kubectl apply -f mig-device.yaml
```

#### 3. ノードのDataPlane用NICのVF用のHost Device Networkの配備
```bash
$ kubectl apply -f demo-network1_node01.yaml
```

#### 4. 通信パターンとデータ転送の方向の指定
- spec.containers[].commandにて以下を指定する
  - 3番目の引数
    - `MEMORY_TYPE`:送受信メモリ種別を下記のいずれかで指定
      - `DRAM`: ホストメモリ
      - `VRAM`: GPUメモリ
  - 4番目の引数
    - `Operation`を下記のいずれかで指定
      - `READ`: RMA get操作
      - `WRITE`: RMA put操作
  - 下記は`MEMORY_TYPE`: `DRAM`、`Operation`: `WRITE`を指定するときのテストファイルの一部を示す。
    ```bash
    $ vi ./test/yaml/TestYaml/1node/dciapp-perftest-conn-x1_node01-mig.yaml
    (省略)
    spec:
      shareProcessNamespace: true
      containers:
      - name: sample-app
        image: localhost/sample-app:ut
        imagePullPolicy: Never
        command: ["python3", "client.py", "DRAM", "WRITE"]    ★
    (省略)
    ```


### 実施
+ 接続パターン1の実施
  + 接続パターン1用のAPFWスタブアプリの配備、コンテナへの設定ファイルの格納、APFWスタブアプリ間の通信
    1.Podを配備する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl apply -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-proc-a1_node01-mig.yaml
    ```
    2. 配備したPodを確認する
    ```bash
    $ kubectl get pod -n dci -o wide
    ```
    3. 接続機能Podに接続設定ファイルを追加する
    ```bash
    $ kubectl cp -n dci ../common/appConnectControlInfo_pat2-1_conn-x1.json  dciapp-perftest-conn-x1:/app-conn-control-info-manager-dci/appConnectControlInfo.json
    ```
    4. 接続機能Podで動作するプロセスIDを取得する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- pgrep -f "client.py"
    ```
    5. 接続機能PodにSIGHUPを送信する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- kill -SIGHUP [プロセスID]
    ```
  + 接続パターン1用のAPFWスタブアプリ(各種接続機能、処理機能)の削除
    1.Podを削除する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl delete -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-proc-a1_node01-mig.yaml
    ```
    2.削除したPodを確認する
    ```bash
    $ kubectl get pod -n dci
    ```

+ 接続パターン2の実施
  + 接続パターン2用のAPFWスタブアプリの配備、コンテナへの設定ファイルの格納、APFWスタブアプリ間の通信
    1.Podを配備する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl apply -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-conn-y_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-proc-a1_node01-mig.yaml
    ```
    2. 配備したPodを確認する
    ```bash
    $ kubectl get pod -n dci -o wide
    ```
    3. 接続機能Podに接続設定ファイルを追加する
    ```bash
    $ kubectl cp -n dci ../common/appConnectControlInfo_pat2-2_conn-x1.json  dciapp-perftest-conn-x1:/app-conn-control-info-manager-dci/appConnectControlInfo.json
    $ kubectl cp -n dci ../common/appConnectControlInfo_pat2-2_conn-y.json  dciapp-perftest-conn-y:/app-conn-control-info-manager-dci/appConnectControlInfo.json
    ```
    4. 接続機能Podで動作するプロセスIDを取得する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- pgrep -f "client.py"
    $ kubectl exec -n dci dciapp-perftest-conn-y -- pgrep -f "server_client.py"
    ```
    5. 接続機能PodにSIGHUPを送信する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- kill -SIGHUP [プロセスID]
    $ kubectl exec -n dci dciapp-perftest-conn-y -- kill -SIGHUP [プロセスID]
    ```
  + 接続パターン2用のAPFWスタブアプリ(各種接続機能、処理機能)の削除
    1.Podを削除する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl delete -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-conn-y_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-proc-a1_node01-mig.yaml
    ```
    2.削除したPodを確認する
    ```bash
    $ kubectl get pod -n dci
    ```

+ 接続パターン3の実施
  + 接続パターン3用のAPFWスタブアプリの配備、コンテナへの設定ファイルの格納、APFWスタブアプリ間の通信
    1.Podを配備する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl apply -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-proc-a1_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-proc-b_node01-mig.yaml
    ```
    2. 配備したPodを確認する
    ```bash
    $ kubectl get pod -n dci -o wide
    ```
    3. 接続機能Podに接続設定ファイルを追加する
    ```bash
    $ kubectl cp -n dci ../common/appConnectControlInfo_pat2-3_conn-x1.json  dciapp-perftest-conn-x1:/app-conn-control-info-manager-dci/appConnectControlInfo.json
    ```
    4. 接続機能Podで動作するプロセスIDを取得する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- pgrep -f "client.py"
    ```
    5. 接続機能PodにSIGHUPを送信する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- kill -SIGHUP [プロセスID]
    ```
  + 接続パターン3用のAPFWスタブアプリ(各種接続機能、処理機能)の削除
    1.Podを削除する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl delete -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-proc-a1_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-proc-b_node01-mig.yaml
    ```
    2.削除したPodを確認する
    ```bash
    $ kubectl get pod -n dci
    ```

+ 接続パターン4の実施
  + 接続パターン4用のAPFWスタブアプリの配備、コンテナへの設定ファイルの格納、APFWスタブアプリ間の通信
    1.Podを配備する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl apply -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-conn-x2_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-proc-a1_node01-mig.yaml
    $ kubectl apply -f dciapp-perftest-proc-a2_node01-mig.yaml
    ```
    2. 配備したPodを確認する
    ```bash
    $ kubectl get pod -n dci -o wide
    ```
    3. 接続機能Podに接続設定ファイルを追加する
    ```bash
    $ kubectl cp -n dci ../common/appConnectControlInfo_pat2-4_conn-x1.json  dciapp-perftest-conn-x1:/app-conn-control-info-manager-dci/appConnectControlInfo.json
    $ kubectl cp -n dci ../common/appConnectControlInfo_pat2-4_conn-x2.json  dciapp-perftest-conn-x2:/app-conn-control-info-manager-dci/appConnectControlInfo.json
    ```
    4. 接続機能Podで動作するプロセスIDを取得する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- pgrep -f "client.py"
    $ kubectl exec -n dci dciapp-perftest-conn-x2 -- pgrep -f "client.py"
    ```
    5. 接続機能Podに同時にSIGHUPを送信する
    ```bash
    $ kubectl exec -n dci dciapp-perftest-conn-x1 -- kill -SIGHUP [プロセスID]
    kubectl exec -n dci dciapp-perftest-conn-x2 -- kill -SIGHUP [プロセスID]
    ```
  + 接続パターン4用のAPFWスタブアプリ(各種接続機能、処理機能)の削除
    1.Podを削除する
    ```bash
    $ cd ./test/yaml/TestYaml/1node/
    $ kubectl delete -f dciapp-perftest-conn-x1_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-conn-x2_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-proc-a1_node01-mig.yaml
    $ kubectl delete -f dciapp-perftest-proc-a2_node01-mig.yaml
    ```
    2.削除したPodを確認する
    ```bash
    $ kubectl get pod -n dci
    ```
