# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

PROGRAM_NAME := fork-exec-c
BINARY       := $(PROGRAM_NAME).elf

# The execv() target, bundled into the ramfs at "/target" by the harness
# (see .nanvix/z.py SUITE_RAMFS_LIBS).
TARGET_BINARY := fork-exec-target.elf

all: $(BINARIES_DIR)/$(BINARY) $(BINARIES_DIR)/$(TARGET_BINARY)

# Caller / init program (forks, then execs the target).
$(BINARIES_DIR)/$(BINARY): main.o
	$(CC) $(LDFLAGS) main.o $(LIBRARIES) -o $@

# execv() target program (does the vfsd read that hangs after fork+exec).
$(BINARIES_DIR)/$(TARGET_BINARY): target.o
	$(CC) $(LDFLAGS) target.o $(LIBRARIES) -o $@

clean:
	rm -f main.o target.o
	rm -f $(BINARIES_DIR)/$(BINARY)
	rm -f $(BINARIES_DIR)/$(TARGET_BINARY)

%.o: %.c
	$(CC) $(CFLAGS) $< -c -o $@
