# RDMA communicator using NIXL

## Usage

```sh
nixl_communicator ROLE ADDRESS PORT MEMORY_TYPE OPERATION
```

* `ROLE`: 役割
  * `initiator`: RDMAセッション開始者
    * `READ` の場合 : 送信者 (READされる)
    * `WRITE` の場合: 受信者 (WRITEされる)
  * `target`: RDMAセッションの待ち受け者
    * `READ` の場合 : 受信者 (READする)
    * `WRITE` の場合: 送信者 (WRITEする)
* `ADDRESS`: `target` の待ち受けアドレス
  * `initiator` の場合のみ利用する
* `PORT`:
  * `initiator` の場合: `target` の待ち受けポート
  * `target` の場合   : 待ち受けポート
* `MEMORY_TYPE`: 送受信メモリ種別
  * `DRAM`: ホストメモリ
  * `VRAM`: GPUメモリ
* `OPERATION`:
  * `READ` : RMA get操作
  * `WRITE`: RMA put操作

以下に注意のこと。

* `ADDRESS` と `PORT` には `initiator` と `target` ともに `target` のものを指定する。
* `OPERATION` には `initiator` と `target` で同一のものを指定する。
* 各プロセスが利用するNICデバイス名を環境変数の `UCX_NET_DEVICES` で指定する。
* TCP通信などが行なわれないように環境変数の `UCX_TLS` に `rc,cuda_copy` を指定する。

## Build Image

```sh
docker build -t nixl-communicator .
```

## Create Container on Docker

```sh
docker create --gpus all --name nixl-communicator \
  --privileged \
  --net=host \
  --cap-add CAP_SYS_PTRACE \
  --shm-size="8g" \
  --device=/dev/infiniband/uverbs0 \
  --device=/dev/infiniband/rdma_cm \
  --ipc=host \
  --ulimit memlock=-1 \
  -e CUDA_CACHE_DISABLE=0 \
  -v /dev/infiniband:/dev/infiniband \
  nixl-communicator
```

## Excute tool

* on Docker

    ```sh
    $ docker exec -it nixl-communicator bash
    # nixl_communicator ...
    ```
* on k8s

    ```sh
    $ kubectl -n <NAMESPACE> exec -it <PODNAME> -- bash
    # nixl_communicator ...
    ```

## Examples

`target` を `10.40.10.70:10000` で動作させる例を示す。

なお、実行環境のNICデバイス名が以下であるものとする。

* `initiator`: `mlx5_1:1`
* `target`   : `mlx5_2:1`

### HOST <--(READ)-- GPU

#### Run Target

```sh
UCX_TLS="rc,cuda_copy" UCX_NET_DEVICES="mlx5_2:1" nixl_communicator target 10.40.10.70 10000 DRAM READ
```

* ホストメモリに読み込む操作を行うため、ホストメモリを意味する `DRAM` を指定する。

#### Run Initiator

```sh
UCX_TLS="rc,cuda_copy" UCX_NET_DEVICES="mlx5_1:1" nixl_communicator initiator 10.40.10.70 10000 VRAM READ
```

* GPUメモリを読み込んでもらうため、GPUメモリを意味する `VRAM` を指定する。

#### 結果確認

`READ` の場合、通信に成功すると `target` の標準出力に以下が出力されます。

```
XX:14:41.726001958  9191 nixl_communicator.cpp:293] Transfer completed and Buffers match with Remote
XX:14:41.726010398  9191 nixl_communicator.cpp:294] UCX Transfer Success!!!
```

### HOST <--(WRITE)-- GPU

#### Run Target

```sh
UCX_TLS="rc,cuda_copy" UCX_NET_DEVICES="mlx5_2:1" nixl_communicator target 10.40.10.70 10000 VRAM WRITE
```

* GPUメモリを書き込む操作を行なうため、GPUメモリを意味する `VRAM` を指定する。

#### Run Initiator

```sh
UCX_TLS="rc,cuda_copy" UCX_NET_DEVICES="mlx5_1:1" nixl_communicator initiator 10.40.10.70 10000 DRAM WRITE
```

* ホストメモリに書き込んでもらうため、ホストメモリを意味する `DRAM` を指定する。

#### 結果確認

`WRITE` の場合、通信に成功すると `initiator` の標準出力に以下が出力されます。

```
XX:14:41.726001958  9191 nixl_communicator.cpp:293] Transfer completed and Buffers match with Remote
XX:14:41.726010398  9191 nixl_communicator.cpp:294] UCX Transfer Success!!!
```

---

(c) NTT, Inc.
