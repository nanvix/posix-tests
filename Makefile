# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

#===============================================================================
# Build Configuration
#===============================================================================

# Nanvix GitHub repository.
NANVIX_REPO ?= nanvix/nanvix

# Nanvix release directory (populated by 'make init').
NANVIX_DIR ?= .nanvix

# Test suites to build.
SUITES := c-bindings dlfcn-c dlfcn-pie-c echo-c echo-cpp file-c hello-c hello-cpp memory-c misc-c network-c noop-c noop-cpp thread-c

# ELF binaries produced by each suite.
BINARIES := $(addsuffix .elf,$(SUITES))

#===============================================================================
# Host Targets
#===============================================================================

all: $(addprefix build/,$(BINARIES))

# Build all test suite ELFs inside Docker and export to build/.
build/%.elf: src/ Makefile Dockerfile $(NANVIX_DIR)/lib/libposix.a
	DOCKER_BUILDKIT=1 docker build \
		--build-arg BASE_IMAGE=$$(cat $(NANVIX_DIR)/.docker-image) \
		--output type=local,dest=build .
	@touch $(addprefix build/,$(BINARIES))

# Run a specific test suite on Nanvix.
run: build/$(SUITE).elf
	$(NANVIX_DIR)/bin/nanvixd.elf -console-file /dev/stdout -- ./build/$(SUITE).elf

clean:
	rm -rf build

#===============================================================================
# Container Targets (used inside Docker)
#===============================================================================

compile:
	$(MAKE) -C src all BINARIES_DIR=/workspace/build

#===============================================================================
# Init — download the latest Nanvix release and resolve the Docker image tag
#===============================================================================

init: $(NANVIX_DIR)/lib/libposix.a

$(NANVIX_DIR)/lib/libposix.a:
	@echo "Downloading the latest Nanvix release..."
	@RELEASE_INFO=$$(gh release view latest --repo "$(NANVIX_REPO)" --json tagName,assets); \
	TAG_NAME=$$(echo "$$RELEASE_INFO" | jq -r '.tagName'); \
	ASSET_NAME=$$(echo "$$RELEASE_INFO" | jq -r \
		'.assets[] | select(.name | startswith("nanvix-microvm-multi-process-release")) | .name'); \
	if [ -z "$$ASSET_NAME" ]; then \
		echo "ERROR: Could not find a microvm multi-process release asset." >&2; \
		exit 1; \
	fi; \
	echo "  Release: $$TAG_NAME"; \
	echo "  Asset: $$ASSET_NAME"; \
	CARGO_TOML=$$(gh api "repos/$(NANVIX_REPO)/contents/Cargo.toml?ref=$$TAG_NAME" \
		--jq '.content' 2>/dev/null | base64 -d) || true; \
	CARGO_VERSION=$$(echo "$$CARGO_TOML" | grep -m1 '^version' | sed 's/.*"\(.*\)".*/\1/') || true; \
	if [ -n "$$CARGO_VERSION" ]; then \
		MAJOR_MINOR="$${CARGO_VERSION%.*}"; \
		DOCKER_IMAGE="nanvix/toolchain:v$${MAJOR_MINOR}.x-minimal"; \
	else \
		DOCKER_IMAGE="nanvix/toolchain:latest-minimal"; \
	fi; \
	echo "  Docker image: $$DOCKER_IMAGE"; \
	TMPDIR=$$(mktemp -d); \
	gh release download latest --repo "$(NANVIX_REPO)" \
		--pattern "$$ASSET_NAME" \
		--dir "$$TMPDIR"; \
	mkdir -p $(NANVIX_DIR); \
	tar xjf "$$TMPDIR/$$ASSET_NAME" -C $(NANVIX_DIR) --strip-components=1; \
	rm -rf "$$TMPDIR"; \
	echo "$$DOCKER_IMAGE" > $(NANVIX_DIR)/.docker-image; \
	echo ""; \
	echo "Done. Nanvix release extracted to $(NANVIX_DIR)/."

distclean: clean
	rm -rf $(NANVIX_DIR)

.PHONY: all run compile clean init distclean
