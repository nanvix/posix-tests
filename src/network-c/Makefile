# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

PROGRAM_NAME := network-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

all: $(OBJECTS)
	$(CC) $(LDFLAGS) $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean:
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

%.o: %.c
	$(CC) $(CFLAGS) $< -c -o $@
