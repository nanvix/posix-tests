# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

#===============================================================================
# Build Configuration
#===============================================================================

# Nanvix SDK directory (set by the Docker image).
NANVIX_TOOLCHAIN ?= /opt/nanvix

# Platform and deployment mode (set by CI or z.py).
PLATFORM ?= microvm
PROCESS_MODE ?= single-process
MEMORY_SIZE ?= 256mb

# Downloaded runtime artifacts are used only by the direct Make test target.
NANVIX_RUNTIME ?= ../.nanvix/sysroot

# SDK tools.
export CC := $(NANVIX_TOOLCHAIN)/bin/clang
export CXX := $(NANVIX_TOOLCHAIN)/bin/clang++
export READELF := $(NANVIX_TOOLCHAIN)/bin/llvm-readelf

# Compiler flags.
export CFLAGS := -std=c17
CFLAGS += -Wall -Wextra -Werror
CFLAGS += -O2
CFLAGS += -D__NANVIX_SYSNAME__=\"nanvix\"
CFLAGS += -D__NANVIX_NODENAME__=\"localhost\"
CFLAGS += -D__$(PLATFORM)__
ifeq ($(PROCESS_MODE),standalone)
CFLAGS += -D__NANVIX_STANDALONE__
endif

# C++ compiler flags.
export CXXFLAGS := -std=c++17
CXXFLAGS += -Wall -Wextra -Werror
CXXFLAGS += -O2
CXXFLAGS += -D__NANVIX_SYSNAME__=\"nanvix\"
CXXFLAGS += -D__NANVIX_NODENAME__=\"localhost\"
CXXFLAGS += -D__$(PLATFORM)__
ifeq ($(PROCESS_MODE),standalone)
CXXFLAGS += -D__NANVIX_STANDALONE__
endif

# The compiler drivers select the SDK startup object, linker script, libc,
# compiler runtime, and (for C++) libc++ runtimes.
export LDFLAGS := -Wl,-z,noexecstack

# Output directory for compiled binaries.
export BINARIES_DIR ?= $(CURDIR)/../build

# Output directory for shared libraries.
export LIBRARIES_DIR ?= $(BINARIES_DIR)

#===============================================================================
# Test Suites
#===============================================================================

BASE_SUITES := c-bindings echo-c echo-cpp file-c hello-c hello-cpp memory-c misc-c network-c noop-c noop-cpp thread-c
DYNAMIC_LOADER_SUITES := dlfcn-c dlfcn-global-c dlfcn-needed-c dlfcn-pie-c

# The pinned SDK advertises features.dynamic_loader=false.
DYNAMIC_LOADER ?= false
SUITES := $(BASE_SUITES)
ifeq ($(DYNAMIC_LOADER),true)
SUITES += $(DYNAMIC_LOADER_SUITES)
endif

#===============================================================================
# Build Rules
#===============================================================================

all: $(BINARIES_DIR)
	@test -f "$(NANVIX_TOOLCHAIN)/nanvix-sdk.json" || { echo "Nanvix SDK not found at $(NANVIX_TOOLCHAIN)"; exit 1; }
	@test -x "$(CC)" || { echo "Nanvix SDK Clang not found at $(CC)"; exit 1; }
	@test -x "$(CXX)" || { echo "Nanvix SDK Clang++ not found at $(CXX)"; exit 1; }
	@for suite in $(SUITES); do \
		echo "Building $$suite..."; \
		$(MAKE) -C $$suite all || exit 1; \
	done

clean:
	@for suite in $(BASE_SUITES) $(DYNAMIC_LOADER_SUITES); do \
		$(MAKE) -C $$suite clean || true; \
	done
	rm -rf $(DIST_DIR)

$(BINARIES_DIR):
	mkdir -p $(BINARIES_DIR)

#===============================================================================
# Test Rules
#===============================================================================

# Test suites that can run via plain nanvixd invocation.
# file-c needs VFS access (tests open/read/write on files).
# network-c needs network infrastructure (sockets).
# misc-c needs environment variable setup (NANVIX_TEST).
TESTABLE_SUITES := c-bindings echo-c echo-cpp hello-c hello-cpp memory-c noop-c noop-cpp thread-c

test: test-smoke test-integration

test-smoke:
	@echo "Running smoke tests..."
	@for suite in $(SUITES); do \
		binary="$(BINARIES_DIR)/$${suite}.elf"; \
		if [ ! -f "$$binary" ]; then \
			echo "SKIP $$suite (binary not found)"; \
			continue; \
		fi; \
		echo "OK   $$suite (binary exists)"; \
	done

test-integration:
ifeq ($(PROCESS_MODE),standalone)
	@echo "Skipping integration tests for standalone mode."
else
	@echo "Running integration tests..."
	@for suite in $(TESTABLE_SUITES); do \
		binary="$(BINARIES_DIR)/$${suite}.elf"; \
		if [ ! -f "$$binary" ]; then \
			echo "SKIP $$suite"; \
			continue; \
		fi; \
		echo "RUN  $$suite..."; \
		$(NANVIX_RUNTIME)/bin/nanvixd.elf -console-file /dev/stdout -- "$$binary" && echo "OK   $$suite" || { echo "FAIL $$suite"; exit 1; }; \
	done
endif

#===============================================================================
# Release Rules
#===============================================================================

DIST_DIR := $(CURDIR)/../dist

package: all
	@echo "Packaging release..."
	mkdir -p $(DIST_DIR)
	tar czf $(DIST_DIR)/posix-tests-$(PLATFORM)-$(PROCESS_MODE)-$(MEMORY_SIZE).tar.gz \
		-C $(BINARIES_DIR) $(addsuffix .elf,$(SUITES))
	@echo "Package: $(DIST_DIR)/posix-tests-$(PLATFORM)-$(PROCESS_MODE)-$(MEMORY_SIZE).tar.gz"

verify-package:
	@echo "Verifying package..."
	@tarball="$(DIST_DIR)/posix-tests-$(PLATFORM)-$(PROCESS_MODE)-$(MEMORY_SIZE).tar.gz"; \
	if [ ! -f "$$tarball" ]; then \
		echo "ERROR: Package not found: $$tarball"; \
		exit 1; \
	fi; \
	for suite in $(SUITES); do \
		if ! tar tzf "$$tarball" | grep -q "$${suite}.elf"; then \
			echo "ERROR: Missing $${suite}.elf in package"; \
			exit 1; \
		fi; \
	done; \
	echo "Package verified: $$tarball"

.PHONY: all clean test test-smoke test-integration package verify-package
