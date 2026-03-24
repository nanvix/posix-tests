# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

PROGRAM_NAME := dlfcn-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

# Required relocation types for the shared library.
REQUIRED_TYPES = R_386_RELATIVE R_386_PC32 R_386_GLOB_DAT R_386_32 R_386_JUMP_SLOT

all: $(OBJECTS) libs-all
	$(CC) $(LDFLAGS) $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean: libs-clean
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

libs-all:
	$(CC) libs/mul.c -shared -fPIC -o $(LIBRARIES_DIR)/libmul.so
	@for TYPE in $(REQUIRED_TYPES); do \
	if ! readelf -r $(LIBRARIES_DIR)/libmul.so | grep -q $$TYPE; then \
	echo "Error: Relocation type $$TYPE not found in $(LIBRARIES_DIR)/libmul.so"; \
	exit 1; \
	fi \
	done

libs-clean:
	rm -f $(LIBRARIES_DIR)/libmul.so

%.o: %.c
	$(CC) $(CFLAGS) $< -c -o $@
