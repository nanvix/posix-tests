# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.
#
# dlfcn-diamond-c: Diamond DT_NEEDED graph resolution.
#
#   libdiamond.so
#     +-- DT_NEEDED libleft.so   --+
#     +-- DT_NEEDED libright.so  --+-- DT_NEEDED libbase.so
#
# The loader must consolidate the two DT_NEEDED libbase.so edges onto
# a single in-memory libbase.so instance.

PROGRAM_NAME := dlfcn-diamond-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

all: $(OBJECTS) libs-all
	$(CC) $(LDFLAGS) -pie -rdynamic -Wl,--no-dynamic-linker $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean: libs-clean
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

# libbase.so   - leaf of the diamond, no deps.
# libleft.so   - DT_NEEDED libbase.so.
# libright.so  - DT_NEEDED libbase.so.
# libdiamond.so - DT_NEEDED libleft.so, libright.so.
libs-all:
	$(CC) libs/base.c -shared -fPIC -o $(LIBRARIES_DIR)/libbase.so
	# `--enable-new-dtags` on the dependent libs ensures DT_RUNPATH (not
	# the deprecated DT_RPATH) is emitted; the resolver in Nanvix's
	# loader only honours DT_RUNPATH.  libbase.so has no DT_NEEDED so
	# it does not need the flag.
	$(CC) libs/left.c -shared -fPIC \
	    -L$(LIBRARIES_DIR) -lbase \
	    -Wl,--enable-new-dtags,-rpath,lib \
	    -o $(LIBRARIES_DIR)/libleft.so
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libleft.so | grep -E -q '\(NEEDED\)[[:space:]]+Shared library: \[libbase\.so\]'; then \
	echo "Error: DT_NEEDED libbase.so missing in $(LIBRARIES_DIR)/libleft.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libleft.so; \
	exit 1; \
	fi
	$(CC) libs/right.c -shared -fPIC \
	    -L$(LIBRARIES_DIR) -lbase \
	    -Wl,--enable-new-dtags,-rpath,lib \
	    -o $(LIBRARIES_DIR)/libright.so
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libright.so | grep -E -q '\(NEEDED\)[[:space:]]+Shared library: \[libbase\.so\]'; then \
	echo "Error: DT_NEEDED libbase.so missing in $(LIBRARIES_DIR)/libright.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libright.so; \
	exit 1; \
	fi
	$(CC) libs/diamond.c -shared -fPIC \
	    -L$(LIBRARIES_DIR) -lleft -lright \
	    -Wl,--enable-new-dtags,-rpath,lib \
	    -o $(LIBRARIES_DIR)/libdiamond.so
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libdiamond.so | grep -E -q '\(NEEDED\)[[:space:]]+Shared library: \[libleft\.so\]'; then \
	echo "Error: DT_NEEDED libleft.so missing in $(LIBRARIES_DIR)/libdiamond.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libdiamond.so; \
	exit 1; \
	fi
	@if ! $(READELF) -d $(LIBRARIES_DIR)/libdiamond.so | grep -E -q '\(NEEDED\)[[:space:]]+Shared library: \[libright\.so\]'; then \
	echo "Error: DT_NEEDED libright.so missing in $(LIBRARIES_DIR)/libdiamond.so"; \
	$(READELF) -d $(LIBRARIES_DIR)/libdiamond.so; \
	exit 1; \
	fi

libs-clean:
	rm -f $(LIBRARIES_DIR)/libbase.so
	rm -f $(LIBRARIES_DIR)/libleft.so
	rm -f $(LIBRARIES_DIR)/libright.so
	rm -f $(LIBRARIES_DIR)/libdiamond.so

%.o: %.c
	$(CC) $(CFLAGS) -fPIE $< -c -o $@
