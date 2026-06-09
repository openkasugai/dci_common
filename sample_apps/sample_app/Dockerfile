ARG BASE_IMAGE="nvcr.io/nvidia/cuda-dl-base"
ARG BASE_IMAGE_TAG="25.03-cuda12.8-devel-ubuntu24.04"

FROM ${BASE_IMAGE}:${BASE_IMAGE_TAG}

# Define architecture after FROM
ARG ARCH="x86_64"
ARG DEFAULT_PYTHON_VERSION="3.12"
ARG UCX_REF="v1.19.x"


RUN DEBIAN_FRONTEND=noninteractive apt-get update -y && \
    sed -i -e "s/# deb-src/deb-src/g" /etc/apt/sources.list && \
    apt-get install -y \
        ibverbs-utils \
        iproute2 \
        iputils-ping \
        rdmacm-utils \
        libpci-dev \
        pkg-config \
        git \
        wget \
        curl \
        nano \
        jq \
        libibverbs-dev \
        rdma-core \
        libibumad-dev \
        libnuma-dev \
        librdmacm-dev \
        ibverbs-providers \
        libprotobuf-dev \
        libgrpc++-dev \
        etcd-client \
        ninja-build \
        pybind11-dev \
        libclang-dev \
        cmake \
        libgflags-dev \
        libgrpc-dev \
        protobuf-compiler-grpc \
        libaio-dev \
        liburing-dev \
        libcpprest-dev \
        etcd-server \
        autotools-dev \
        automake \
        libtool \
        libz-dev \
        flex \
        libgtest-dev \
        build-essential \
        python3 \
        python3-pip \
        iperf3 \
        gdb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install \
    --reinstall libibverbs-dev rdma-core ibverbs-utils libibumad-dev \
    libnuma-dev librdmacm-dev ibverbs-providers \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*WORKDIR /workspace
RUN git clone https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3.git &&\
        cd etcd-cpp-apiv3 && mkdir build && cd build && \
        cmake .. && make -j$(nproc) && make install

RUN pip3 install --break-system-packages uv

#RUN git clone https://github.com/ai-dynamo/nixl.git && \
#    cd nixl && \
#    git checkout 0.3.1
#WORKDIR /workspace/nixl

RUN echo "=== Cloning nixl repository ===" && \
    rm -rf nixl && \
    git clone https://github.com/ai-dynamo/nixl.git && \
    cd nixl && \
    echo "=== Checking out version 0.3.1 ===" && \
    git checkout 0.3.1 && \
    echo "=== Verifying nixl source files ===" && \
    ls -la && \
    echo "=== Checking for meson.build after clone ===" && \
    find . -name "meson.build" -type f

RUN echo "=== Moving nixl contents to /workspace/nixl ===" && \
    mkdir -p /workspace/nixl && \
    cp -r nixl/* /workspace/nixl/ && \
    cp -r nixl/.* /workspace/nixl/ 2>/dev/null || true && \
    ls -la /workspace/nixl/

WORKDIR /workspace/nixl

RUN echo "=== After WORKDIR change ===" && \
    pwd && \
    echo "=== Directory contents after WORKDIR ===" && \
    ls -la

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

ENV VIRTUAL_ENV=/workspace/nixl/.venv
RUN uv venv $VIRTUAL_ENV --python $DEFAULT_PYTHON_VERSION && \
    # pybind11 pip install needed for ubuntu 22.04
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
     cd ucx &&                       \
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

COPY App/nixl-communicator/assets/nixl.patch /workspace/
#RUN patch < /workspace/nixl.patch
#RUN patch < /workspace/nixl.patch || echo "Patch failed, continuing without patch"
#
#RUN rm -rf build && \
#    mkdir build && \
#    uv run meson setup build/ --prefix=/usr/local/nixl && \
#    ninja -C build install && \
#    rm -r build

RUN echo "=== Debugging nixl directory structure ===" && \
    pwd && \
    ls -la && \
    echo "=== Checking for meson.build ===" && \
    find . -name "meson.build" -type f && \
    echo "=== Applying patch ===" && \
    patch < /workspace/nixl.patch || echo "Patch failed, continuing without patch"

RUN echo "=== Setting up meson build ===" && \
    if [ -f meson.build ]; then \
        echo "Found meson.build, proceeding with build"; \
        rm -rf build && \
        mkdir build && \
        uv run meson setup build/ --prefix=/usr/local/nixl && \
        ninja -C build install && \
        rm -r build; \
    else \
        echo "ERROR: meson.build not found in $(pwd)"; \
        echo "Directory contents:"; \
        ls -la; \
        exit 1; \
    fi

ENV NIXL_PREFIX=/usr/local/nixl
ENV NIXL_PLUGIN_DIR=/usr/local/nixl/lib/$ARCH-linux-gnu/plugins
RUN echo "/usr/local/nixl/lib/$ARCH-linux-gnu" > /etc/ld.so.conf.d/nixl.conf && \
    echo "/usr/local/nixl/lib/$ARCH-linux-gnu/plugins" >> /etc/ld.so.conf.d/nixl.conf && \
    ldconfig

COPY . /opt/nixl-communicator/
#RUN cd /opt/nixl-communicator && \
#    make install && \
#    cd .. && \
#    rm -r nixl-communicator

RUN echo "=== Building nixl-communicator ===" && \
    cd /opt/nixl-communicator/App/nixl-communicator && \
    echo "=== Current directory ===" && \
    pwd && \
    echo "=== Directory contents ===" && \
    ls -la && \
    echo "=== Makefile content ===" && \
    head -10 Makefile && \
    echo "=== Running make install ===" && \
    make install && \
    echo "=== Cleaning up ===" && \
    cd / && \
    rm -rf /opt/nixl-communicator

CMD ["tail", "-f", "/dev/null"]

# Install Python dependencies: PyYAML, FastAPI, Uvicorn, and dnspython
RUN pip3 install --no-cache-dir --break-system-packages pyyaml fastapi uvicorn dnspython

# Create necessary directories
RUN mkdir -p /work/interfaces/http /app

## Copy files from nixl-communicator image with verification
#COPY --from=nixl /usr/local/nixl/ /usr/local/nixl/
#COPY --from=nixl /usr/local/lib/ /usr/local/lib/
#COPY --from=nixl /usr/local/bin/nixl_communicator /usr/local/bin/nixl_communicator
#COPY --from=nixl /etc/ld.so.conf.d/nixl.conf /etc/ld.so.conf.d/nixl.conf
#
## Verify copied files (for debugging)
#RUN echo "=== Verifying nixl installation ===" && \
#    ls -la /usr/local/nixl/ && \
#    ls -la /usr/local/nixl/lib/ && \
#    ls -la /usr/local/bin/nixl_communicator && \
#    echo "=== nixl verification complete ==="
#
## Set up library paths (append to existing config)
#RUN echo "/usr/local/nixl/lib/${ARCH}-linux-gnu" >> /etc/ld.so.conf.d/nixl.conf && \
#    echo "/usr/local/nixl/lib/${ARCH}-linux-gnu/plugins" >> /etc/ld.so.conf.d/nixl.conf && \
#    echo "/usr/local/lib" >> /etc/ld.so.conf.d/nixl.conf && \
#    ldconfig && \
#    echo "=== Library configuration ===" && \
#    cat /etc/ld.so.conf.d/nixl.conf && \
#    echo "=== ldconfig cache ===" && \
#    ldconfig -p | grep -E '(nixl|cuda)' | head -20
#
## Set comprehensive environment variables
#ENV NIXL_PREFIX=/usr/local/nixl
#ENV NIXL_PLUGIN_DIR=/usr/local/nixl/lib/${ARCH}-linux-gnu/plugins
#ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/local/nixl/lib/${ARCH}-linux-gnu:/usr/local/cuda/lib64:${LD_LIBRARY_PATH}
#ENV PATH=/usr/local/bin:/usr/local/nixl/bin:${PATH}
#ENV CUDA_HOME=/usr/local/cuda
#ENV PKG_CONFIG_PATH=/usr/local/nixl/lib/${ARCH}-linux-gnu/pkgconfig:/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}

# Copy Python scripts and configuration files
COPY ./App/scripts/ /app/
COPY ./test/interfaces/http/json/* /work/interfaces/http/
COPY ./test/interfaces/http/txt/* /work/interfaces/http/

# Verify copied application files
RUN echo "=== Application files ===" && \
    ls -la /app/ && \
    echo "=== HTTP interface files ===" && \
    ls -la /work/interfaces/http/ || echo "HTTP interface files not found" && \
    echo "=== Verification complete ==="

# Set working directory
WORKDIR /app

# Set default HTTP port
ENV HTTP_PORT=80

# Expose HTTP port
EXPOSE ${HTTP_PORT}

# # Add health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:${HTTP_PORT}/health/live || exit 1

# Test nixl_communicator availability
RUN echo "=== Testing nixl_communicator ===" && \
    which nixl_communicator && \
    ldd /usr/local/bin/nixl_communicator || echo "ldd check failed but continuing" && \
    echo "=== nixl_communicator test complete ==="

# Set entrypoint to run the FastAPI application
ENTRYPOINT ["python3", "common.py"]
