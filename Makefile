# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

#===============================================================================
# Build Configuration
#===============================================================================

# Nanvix GitHub repository.
NANVIX_REPO ?= nanvix/nanvix

# Nanvix runtime directory (populated by 'make init').
NANVIX_DIR ?= .nanvix
NANVIX_RUNTIME ?= $(NANVIX_DIR)/sysroot
NANVIX_VERSION ?= 0.20.0

# Content-addressed SDK coordinate comes from the canonical manifest.
NANVIX_MANIFEST ?= .nanvix/nanvix.toml
NANVIX_SDK_IMAGE_NAME = $(shell sed -n 's/^sdk-image = "\(.*\)"/\1/p' $(NANVIX_MANIFEST))
NANVIX_SDK_IMAGE_DIGEST = $(shell sed -n 's/^sdk-digest = "\(.*\)"/\1/p' $(NANVIX_MANIFEST))
NANVIX_SDK_IMAGE ?= $(NANVIX_SDK_IMAGE_NAME)@$(NANVIX_SDK_IMAGE_DIGEST)

# Build/runtime knobs (must match Dockerfile defaults). Used both to select the
# correct release asset in 'make init' and to parameterize the Docker build.
PLATFORM     ?= microvm
PROCESS_MODE ?= single-process
MEMORY_SIZE  ?= 256mb

# Test suites to build.
SUITES := c-bindings echo-c echo-cpp file-c hello-c hello-cpp memory-c misc-c network-c noop-c noop-cpp thread-c

# ELF binaries produced by each suite.
BINARIES := $(addsuffix .elf,$(SUITES))

#===============================================================================
# Host Targets
#===============================================================================

all: $(addprefix build/,$(BINARIES))

# Build all test suite ELFs inside Docker and export to build/.
build/%.elf: src/ Makefile Dockerfile
	DOCKER_BUILDKIT=1 docker build \
		--build-arg BASE_IMAGE=$(NANVIX_SDK_IMAGE) \
		--build-arg PLATFORM=$(PLATFORM) \
		--build-arg PROCESS_MODE=$(PROCESS_MODE) \
		--build-arg MEMORY_SIZE=$(MEMORY_SIZE) \
		--output type=local,dest=build .
	@touch $(addprefix build/,$(BINARIES))

# Run a specific test suite on Nanvix.
run: $(NANVIX_RUNTIME)/bin/nanvixd.elf build/$(SUITE).elf
	$(NANVIX_RUNTIME)/bin/nanvixd.elf -bin-dir $(NANVIX_RUNTIME)/bin -console-file /dev/stdout -- ./build/$(SUITE).elf

clean:
	rm -rf build

#===============================================================================
# Container Targets (used inside Docker)
#===============================================================================

compile:
	$(MAKE) -C src all BINARIES_DIR=/workspace/build

#===============================================================================
# Init — download the runtime matching the pinned SDK
#===============================================================================

init: $(NANVIX_RUNTIME)/bin/nanvixd.elf

$(NANVIX_RUNTIME)/bin/nanvixd.elf:
	@echo "Downloading Nanvix runtime v$(NANVIX_VERSION)..."
	@RELEASE_INFO=$$(gh release view "v$(NANVIX_VERSION)" --repo "$(NANVIX_REPO)" --json tagName,assets); \
	TAG_NAME=$$(echo "$$RELEASE_INFO" | jq -r '.tagName'); \
	ASSET_PREFIX="nanvix-x86-$(PLATFORM)-$(PROCESS_MODE)-release-$(MEMORY_SIZE)-"; \
	ASSET_NAME=$$(echo "$$RELEASE_INFO" | jq -r --arg prefix "$$ASSET_PREFIX" \
		'.assets[] | select(.name | startswith($$prefix)) | .name'); \
	if [ -z "$$ASSET_NAME" ]; then \
		echo "ERROR: Could not find a release asset starting with '$$ASSET_PREFIX'." >&2; \
		exit 1; \
	fi; \
	if [ "$$(echo "$$ASSET_NAME" | wc -l)" -ne 1 ]; then \
		echo "ERROR: Multiple release assets matched '$$ASSET_PREFIX':" >&2; \
		echo "$$ASSET_NAME" >&2; \
		exit 1; \
	fi; \
	echo "  Release: $$TAG_NAME"; \
	echo "  Asset: $$ASSET_NAME"; \
	echo "  SDK image: $(NANVIX_SDK_IMAGE)"; \
	CACHE_DIR="$(NANVIX_DIR)/cache/runtime-init"; \
	rm -rf "$$CACHE_DIR"; \
	mkdir -p "$$CACHE_DIR" "$(NANVIX_RUNTIME)"; \
	gh release download "$$TAG_NAME" --repo "$(NANVIX_REPO)" \
		--pattern "$$ASSET_NAME" \
		--dir "$$CACHE_DIR"; \
	tar xjf "$$CACHE_DIR/$$ASSET_NAME" -C "$(NANVIX_RUNTIME)" --strip-components=1; \
	rm -rf "$$CACHE_DIR"; \
	echo ""; \
	echo "Done. Nanvix runtime extracted to $(NANVIX_RUNTIME)/."

distclean: clean
	rm -rf $(NANVIX_DIR)/sysroot $(NANVIX_DIR)/cache $(NANVIX_DIR)/buildroot
	rm -rf $(NANVIX_DIR)/venv $(NANVIX_DIR)/env.json

.PHONY: all run compile clean init distclean
