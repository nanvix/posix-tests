# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.
#
# dlfcn-needed-c: Test DT_NEEDED automatic dependency loading.
#
# libconsumer.so is linked against libprovider.so, creating a DT_NEEDED
# entry.  The loader should auto-load libprovider.so when opening
# libconsumer.so.  This is the standard mechanism for shared library
# dependencies (e.g., a Python C extension depending on libm.so).

PROGRAM_NAME := dlfcn-needed-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

all: $(OBJECTS) libs-all
	$(CC) $(LDFLAGS) -pie -rdynamic -Wl,--no-dynamic-linker $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean: libs-clean
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

# libconsumer.so is linked with -lprovider (creates DT_NEEDED entry).
libs-all:
	$(CC) libs/provider.c -shared -fPIC -o $(LIBRARIES_DIR)/libprovider.so
	$(CC) libs/consumer.c -shared -fPIC -L$(LIBRARIES_DIR) -lprovider -o $(LIBRARIES_DIR)/libconsumer.so

libs-clean:
	rm -f $(LIBRARIES_DIR)/libprovider.so
	rm -f $(LIBRARIES_DIR)/libconsumer.so

%.o: %.c
	$(CC) $(CFLAGS) -fPIE $< -c -o $@
