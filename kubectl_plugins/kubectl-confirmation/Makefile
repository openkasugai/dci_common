KUBECTL_PLUGIN ?= kubectl-confirmation

# Get the currently used golang install path (in GOPATH/bin, unless GOBIN is set)
ifeq (,$(shell go env GOBIN))
INSTALL_DIR=$(shell go env GOPATH)/bin
else
INSTALL_DIR=$(shell go env GOBIN)
endif

check_install:
	@if [ -z "$(INSTALL_DIR)" ]; then \
		echo "[Err] The GOBIN or GOPATH variable for "go env" is not set."; \
		exit 1; \
	fi
	@if ! [[ -d "$(INSTALL_DIR)" ]]; then \
		echo "[Err] \"$(INSTALL_DIR)\" is not directory."; \
		exit 1; \
	fi

check_uninstall:
	@if ! [[ -f "$(INSTALL_DIR)/$(KUBECTL_PLUGIN)" ]]; then \
		echo "[Err] plugin \"$(INSTALL_DIR)/$(KUBECTL_PLUGIN)\" not found."; \
		exit 1; \
	fi


.PHONY: build
build:
	go build -o $(KUBECTL_PLUGIN)

.PHONY: clean
clean: $(KUBECTL_PLUGIN)
	rm -f $(KUBECTL_PLUGIN)

.PHONY: install
install: $(KUBECTL_PLUGIN) check_install
	cp -p $(KUBECTL_PLUGIN) $(INSTALL_DIR)

.PHONY: uninstall
uninstall: check_uninstall
	rm -f $(INSTALL_DIR)/$(KUBECTL_PLUGIN)

.PHONY: test
test:
	go test -v ./pkg/safety
