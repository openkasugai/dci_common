ARG BASE_IMAGE="nvcr.io/nvidia/cuda-dl-base"
ARG BASE_IMAGE_TAG="25.03-cuda12.8-devel-ubuntu24.04"

FROM ${BASE_IMAGE}:${BASE_IMAGE_TAG}

ARG ARCH="x86_64"
ARG DEFAULT_PYTHON_VERSION="3.12"
ARG UCX_REF="v1.19.x"

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install \
    ninja-build \
    pybind11-dev \
    libclang-dev \
    cmake \
    libgflags-dev \
    libgrpc-dev \
    libgrpc++-dev \
    libprotobuf-dev \
    libaio-dev \
    liburing-dev \
    protobuf-compiler-grpc \
    libcpprest-dev \
    etcd-server \
    etcd-client \
    autotools-dev \
    automake \
    libtool \
    libz-dev \
    flex \
    libgtest-dev \
    build-essential \
    python3-pip \
    gdb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install \
    --reinstall libibverbs-dev rdma-core ibverbs-utils libibumad-dev \
    libnuma-dev librdmacm-dev ibverbs-providers \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
RUN git clone https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3.git &&\
	cd etcd-cpp-apiv3 && mkdir build && cd build && \
	cmake .. && make -j$(nproc) && make install

RUN pip3 install --break-system-packages uv

RUN git clone https://github.com/ai-dynamo/nixl.git && \
    cd nixl && \
    git checkout 0.3.1
WORKDIR /workspace/nixl

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

ENV VIRTUAL_ENV=/workspace/nixl/.venv
RUN uv venv $VIRTUAL_ENV --python $DEFAULT_PYTHON_VERSION && \
    # Install Python build dependencies (pybind11 required for Ubuntu compatibility)
    uv pip install --upgrade meson pybind11 patchelf

# Setup Mellanox DOCA repository and install DOCA/DPDK packages
# This section configures the Mellanox repository and installs DOCA SDK components:
#  - Uses secure GPG key handling via file to avoid binary output in build logs
#  - Enables strict error checking with 'set -eux' for immediate failure detection
#  - Large packages (like doca-all) may appear to hang during download - this is normal
RUN set -eux; \
    # Initialize PKG_CONFIG_PATH to prevent 'set -u' errors when undefined
    : "${PKG_CONFIG_PATH:=}"; \
    ARCH_SUFFIX=$([ "${ARCH}" = "aarch64" ] && echo "arm64-sbsa" || echo "${ARCH}"); \
    export PKG_CONFIG_PATH="/opt/mellanox/doca/lib/${ARCH_SUFFIX}-linux-gnu/pkgconfig:/opt/mellanox/dpdk/lib/${ARCH_SUFFIX}-linux-gnu/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"; \
    curl -fsSL -o /tmp/mellanox.gpg https://linux.mellanox.com/public/repo/doca/3.0.0/ubuntu24.04/${ARCH_SUFFIX}/GPG-KEY-Mellanox.pub; \
    gpg --dearmor -o /usr/share/keyrings/mellanox-archive-keyring.gpg /tmp/mellanox.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/mellanox-archive-keyring.gpg] https://linux.mellanox.com/public/repo/doca/3.0.0/ubuntu24.04/${ARCH_SUFFIX} ./" > /etc/apt/sources.list.d/mellanox.list; \
    rm -f /tmp/mellanox.gpg; \
    DEBIAN_FRONTEND=noninteractive apt-get update -y; \
    # Log package installation details for troubleshooting
    echo "[INFO] Installing DOCA / DPDK packages for ${ARCH_SUFFIX}"; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        mlnx-dpdk mlnx-dpdk-dev \
        doca-sdk-common doca-sdk-dma doca-sdk-dpdk-bridge \
        doca-sdk-eth doca-sdk-flow doca-sdk-rdma doca-all \
        doca-sdk-gpunetio libdoca-sdk-gpunetio-dev; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

RUN rm -rf /usr/lib/ucx
RUN rm -rf /opt/hpcx/ucx

RUN cd /usr/local/src && \
     git clone https://github.com/openucx/ucx.git && \
     cd ucx && 			     \
     git checkout $UCX_REF &&        \
     ./autogen.sh && ./configure     \
         --enable-shared             \
         --disable-static            \
         --disable-doxygen-doc       \
         --enable-optimizations      \
         --enable-cma                \
         --enable-devel-headers      \
         --with-cuda=/usr/local/cuda \
         --with-verbs                \
         --with-dm                   \
         --with-gdrcopy=/usr/local   \
         --with-efa                  \
         --enable-mt &&              \
    make -j &&                      \
    make -j install-strip &&        \
    cd .. && rm -r ucx && \
    ldconfig

COPY assets/nixl.patch /workspace/
RUN patch < /workspace/nixl.patch

RUN rm -rf build && \
    mkdir build && \
    uv run meson setup build/ --prefix=/usr/local/nixl && \
    ninja -C build install && \
    rm -r build

ENV NIXL_PREFIX=/usr/local/nixl
ENV NIXL_PLUGIN_DIR=/usr/local/nixl/lib/$ARCH-linux-gnu/plugins
RUN echo "/usr/local/nixl/lib/$ARCH-linux-gnu" > /etc/ld.so.conf.d/nixl.conf && \
    echo "/usr/local/nixl/lib/$ARCH-linux-gnu/plugins" >> /etc/ld.so.conf.d/nixl.conf && \
    ldconfig

COPY . /opt/nixl-communicator/
RUN cd /opt/nixl-communicator && \
    make install && \
    cd .. && \
    rm -r nixl-communicator

CMD ["tail", "-f", "/dev/null"]
