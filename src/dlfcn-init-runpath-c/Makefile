# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.
#
# dlfcn-init-runpath-c: Tests for `.init_array` / `.fini_array`
# constructor and destructor invocation, and for DT_RUNPATH-driven
# DT_NEEDED dependency search.

PROGRAM_NAME := dlfcn-init-runpath-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

all: $(OBJECTS) libs-all
	$(CC) $(LDFLAGS) -pie -rdynamic -Wl,--no-dynamic-linker $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean: libs-clean
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

# libctor.so   - constructor/destructor witness, used by the .init_array tests.
# libchild.so  - dependency of libparent.so. Will be staged into
#                lib/subdir/ at ramfs time so it is only reachable via
#                libparent.so's DT_RUNPATH (z.py SUITE_RAMFS_LIBS).
# libparent.so - DT_NEEDED=libchild.so, DT_RUNPATH=lib/subdir/.
#
# `--enable-new-dtags` ensures the linker emits DT_RUNPATH (not the
# deprecated DT_RPATH) for libparent.so, matching what modern
# toolchains produce by default.
libs-all:
	$(CC) libs/ctor.c -shared -fPIC -o $(LIBRARIES_DIR)/libctor.so
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libctor.so | grep -q '(INIT_ARRAY)'; then \
	echo "Error: INIT_ARRAY missing in $(LIBRARIES_DIR)/libctor.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libctor.so; \
	exit 1; \
	fi
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libctor.so | grep -q '(FINI_ARRAY)'; then \
	echo "Error: FINI_ARRAY missing in $(LIBRARIES_DIR)/libctor.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libctor.so; \
	exit 1; \
	fi
	$(CC) libs/subdir/child.c -shared -fPIC -o $(LIBRARIES_DIR)/libchild.so
	$(CC) libs/parent.c -shared -fPIC \
	    -L$(LIBRARIES_DIR) -lchild \
	    -Wl,--enable-new-dtags,-rpath,lib/subdir \
	    -o $(LIBRARIES_DIR)/libparent.so
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libparent.so | grep -E -q '\(NEEDED\)[[:space:]]+Shared library: \[libchild\.so\]'; then \
	echo "Error: DT_NEEDED libchild.so missing in $(LIBRARIES_DIR)/libparent.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libparent.so; \
	exit 1; \
	fi
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libparent.so | grep -E -q '\(RUNPATH\)[[:space:]]+Library runpath: \[lib/subdir\]'; then \
	echo "Error: DT_RUNPATH lib/subdir missing in $(LIBRARIES_DIR)/libparent.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libparent.so; \
	exit 1; \
	fi
	@if $(READELF) -d $(LIBRARIES_DIR)/libparent.so | grep -q '(RPATH)'; then \
	echo "Error: legacy DT_RPATH present in $(LIBRARIES_DIR)/libparent.so (expected DT_RUNPATH only)"; \
	$(READELF) -d $(LIBRARIES_DIR)/libparent.so; \
	exit 1; \
	fi

libs-clean:
	rm -f $(LIBRARIES_DIR)/libctor.so
	rm -f $(LIBRARIES_DIR)/libchild.so
	rm -f $(LIBRARIES_DIR)/libparent.so

%.o: %.c
	$(CC) $(CFLAGS) -fPIE $< -c -o $@
