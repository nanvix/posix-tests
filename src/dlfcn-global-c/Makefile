# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.
#
# dlfcn-global-c: Test RTLD_GLOBAL cross-.so symbol resolution.
#
# libconsumer.so is NOT linked against libprovider.so (no DT_NEEDED).
# The test loads libprovider.so with RTLD_GLOBAL first, then loads
# libconsumer.so.  Per POSIX, provider symbols should be available
# to the consumer via the global scope.

PROGRAM_NAME := dlfcn-global-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

all: $(OBJECTS) libs-all
	$(CC) $(LDFLAGS) -pie -rdynamic -Wl,--no-dynamic-linker $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean: libs-clean
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

# libconsumer.so is NOT linked with -lprovider (no DT_NEEDED).
libs-all:
	$(CC) libs/provider.c -shared -fPIC -o $(LIBRARIES_DIR)/libprovider.so
	$(CC) libs/consumer.c -shared -fPIC -o $(LIBRARIES_DIR)/libconsumer.so

libs-clean:
	rm -f $(LIBRARIES_DIR)/libprovider.so
	rm -f $(LIBRARIES_DIR)/libconsumer.so

%.o: %.c
	$(CC) $(CFLAGS) -fPIE $< -c -o $@
