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

$(BINARIES_DIR):
	mkdir -p $(BINARIES_DIR)

.PHONY: all clean
