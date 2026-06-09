NIXL_FLAGS=-I/usr/local/nixl/include -I/usr/local/nixl/include/utils -L/usr/local/nixl/lib/x86_64-linux-gnu/ -lnixl -lnixl_build -lnixl_common -lserdes
CUDA_FLAGS=`pkg-config cuda-12.8 cudart-12.8 --libs --cflags`

build: nixl_communicator
install: nixl_communicator_install

nixl_communicator: nixl_communicator.cpp
	g++ nixl_communicator.cpp $(NIXL_FLAGS) $(CUDA_FLAGS) -g -o nixl_communicator

nixl_communicator_install: nixl_communicator
	cp nixl_communicator /usr/local/bin
