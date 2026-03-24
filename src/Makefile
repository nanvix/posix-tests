# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

#===============================================================================
# Build Configuration
#===============================================================================

# Nanvix sysroot (set by the host Makefile or z.py).
NANVIX_SYSROOT ?= ../.nanvix

# Toolchain directory (set by the Docker image).
NANVIX_TOOLCHAIN ?= /opt/nanvix

# Platform and deployment mode (set by CI or z.py).
PLATFORM ?= microvm
PROCESS_MODE ?= multi-process
MEMORY_SIZE ?= 128mb

# Cross-compiler.
export CC := $(NANVIX_TOOLCHAIN)/bin/i686-nanvix-gcc

# Compiler flags.
export CFLAGS := -std=c17
CFLAGS += -m32 -march=pentiumpro -Wa,-march=pentiumpro
CFLAGS += -Wall -Wextra -Werror
CFLAGS += -O2
CFLAGS += -D__NANVIX_SYSNAME__=\"nanvix\"
CFLAGS += -D__NANVIX_NODENAME__=\"localhost\"
CFLAGS += -D__$(PLATFORM)__
ifeq ($(PROCESS_MODE),standalone)
CFLAGS += -D__NANVIX_STANDALONE__
endif

# Linker flags.
export LDFLAGS := -z noexecstack -T $(NANVIX_SYSROOT)/lib/user.ld

# Libraries.
export LIBPOSIX := $(NANVIX_SYSROOT)/lib/libposix.a
export LIBC := $(NANVIX_TOOLCHAIN)/i686-nanvix/lib/libc.a
export LIBRARIES := -Wl,--start-group $(LIBPOSIX) $(LIBC) -Wl,--end-group

# Output directory for compiled binaries.
export BINARIES_DIR ?= $(CURDIR)/../build

# Output directory for shared libraries.
export LIBRARIES_DIR ?= $(BINARIES_DIR)

#===============================================================================
# Test Suites
#===============================================================================

SUITES := c-bindings dlfcn-c dlfcn-pie-c file-c memory-c misc-c network-c thread-c

#===============================================================================
# Build Rules
#===============================================================================

all: $(BINARIES_DIR)
	@for suite in $(SUITES); do \
		echo "Building $$suite..."; \
		$(MAKE) -C $$suite all || exit 1; \
	done

clean:
	@for suite in $(SUITES); do \
		$(MAKE) -C $$suite clean || true; \
	done
	rm -rf $(DIST_DIR)

$(BINARIES_DIR):
	mkdir -p $(BINARIES_DIR)

#===============================================================================
# Test Rules
#===============================================================================

# nanvixd binary from the sysroot.
NANVIXD := $(NANVIX_SYSROOT)/bin/nanvixd.elf

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
	@echo "Running integration tests..."
	@for suite in $(SUITES); do \
		binary="$(BINARIES_DIR)/$${suite}.elf"; \
		if [ ! -f "$$binary" ]; then \
			echo "SKIP $$suite"; \
			continue; \
		fi; \
		echo "RUN  $$suite..."; \
		$(NANVIXD) -console-file /dev/stdout -- "$$binary" && echo "OK   $$suite" || { echo "FAIL $$suite"; exit 1; }; \
	done

#===============================================================================
# Release Rules
#===============================================================================

DIST_DIR := $(CURDIR)/../dist

package: all
	@echo "Packaging release..."
	mkdir -p $(DIST_DIR)
	tar cjf $(DIST_DIR)/posix-tests-$(PLATFORM)-$(PROCESS_MODE)-$(MEMORY_SIZE).tar.bz2 \
		-C $(BINARIES_DIR) $(addsuffix .elf,$(SUITES))
	@echo "Package: $(DIST_DIR)/posix-tests-$(PLATFORM)-$(PROCESS_MODE)-$(MEMORY_SIZE).tar.bz2"

verify-package:
	@echo "Verifying package..."
	@tarball="$(DIST_DIR)/posix-tests-$(PLATFORM)-$(PROCESS_MODE)-$(MEMORY_SIZE).tar.bz2"; \
	if [ ! -f "$$tarball" ]; then \
		echo "ERROR: Package not found: $$tarball"; \
		exit 1; \
	fi; \
	for suite in $(SUITES); do \
		if ! tar tjf "$$tarball" | grep -q "$${suite}.elf"; then \
			echo "ERROR: Missing $${suite}.elf in package"; \
			exit 1; \
		fi; \
	done; \
	echo "Package verified: $$tarball"

.PHONY: all clean test test-smoke test-integration package verify-package
