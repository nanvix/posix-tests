# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

PROGRAM_NAME := dlfcn-pie-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

all: $(OBJECTS) libs-all
	$(CC) $(LDFLAGS) -pie -rdynamic -Wl,--no-dynamic-linker $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean: libs-clean
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

libs-all:
	$(CC) libs/mul.c -shared -fPIC -o $(LIBRARIES_DIR)/libmul-pie.so

libs-clean:
	rm -f $(LIBRARIES_DIR)/libmul-pie.so

%.o: %.c
	$(CC) $(CFLAGS) -fPIE $< -c -o $@
