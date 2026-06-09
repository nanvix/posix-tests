# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

PROGRAM_NAME := dlfcn-weak-c

SOURCES := $(wildcard *.c)
OBJECTS := $(SOURCES:.c=.o)
BINARY  := $(PROGRAM_NAME).elf

# Relocation+symbol assertions for the produced .so files.
#
# We assert both the relocation type and the symbol name (and where
# meaningful, that the symbol binding is WEAK / UND) so that fixtures cannot
# silently drift to exercising the wrong symbol.
#
# Weak function refs guarded by `if (&fn) fn();` compile to a GOT load +
# indirect call, so only R_386_GLOB_DAT is emitted.  Weak data refs go through
# the GOT for the same reason.  Strong undefined function calls go through
# the PLT and produce R_386_JUMP_SLOT.  Weak undefined function calls without
# a NULL check (the weak-PLT fixtures below) also produce R_386_JUMP_SLOT,
# allowing us to exercise the loader's handling of weak `JUMP_SLOT`.

# Macro: assert that `$(1)` contains a relocation of type `$(2)`
# (e.g. `R_386_GLOB_DAT`) against the symbol named `$(3)`.  Uses
# `readelf -rW` so symbol names are not truncated, and `grep -E`
# so the pattern stays robust against extra columns.
define ASSERT_RELOC
@if ! $(READELF) -rW $(1) | grep -E -q '$(2)[[:space:]].*[[:space:]]$(3)$$'; then \
	echo "Error: expected $(2) relocation against $(3) in $(1)"; \
	$(READELF) -rW $(1); \
	exit 1; \
fi
endef

# Macro: assert that `$(1)` declares `$(2)` as an undefined dynamic symbol
# with binding `$(3)` (WEAK or GLOBAL).  We deliberately do not check the
# symbol type: the linker may emit `NOTYPE` for undefined function refs that
# carry no in-module definition, while OBJECT/FUNC are reserved for symbols
# with a known kind.  The intended *use* is verified by the relocation-type
# assertion below; here we only prove the symbol is undefined and weak/global.
define ASSERT_DYNSYM
@if ! $(READELF) -WsD $(1) | grep -E -q '$(3)[[:space:]]+(DEFAULT|HIDDEN|PROTECTED|INTERNAL)[[:space:]]+UND[[:space:]]+$(2)$$'; then \
	echo "Error: expected $(3) UND dynamic symbol $(2) in $(1)"; \
	$(READELF) -WsD $(1); \
	exit 1; \
fi
endef

all: $(OBJECTS) libs-all
	$(CC) $(LDFLAGS) -pie -rdynamic -Wl,--no-dynamic-linker $(OBJECTS) $(LIBRARIES) -o $(BINARIES_DIR)/$(BINARY)

clean: libs-clean
	rm -f $(OBJECTS)
	rm -f $(BINARIES_DIR)/$(BINARY)

libs-all:
	# Weak function ref with NULL-guard (R_386_GLOB_DAT) -- resolved variant.
	$(CC) $(CFLAGS) libs/weak_func.c -shared -fPIC -DCALLBACK_NAME=main_callback -o $(LIBRARIES_DIR)/libweak-func-resolved.so
	$(call ASSERT_DYNSYM,$(LIBRARIES_DIR)/libweak-func-resolved.so,main_callback,WEAK)
	$(call ASSERT_RELOC,$(LIBRARIES_DIR)/libweak-func-resolved.so,R_386_GLOB_DAT,main_callback)
	# Weak function ref with NULL-guard (R_386_GLOB_DAT) -- missing variant.
	$(CC) $(CFLAGS) libs/weak_func.c -shared -fPIC -DCALLBACK_NAME=missing_callback -o $(LIBRARIES_DIR)/libweak-func-missing.so
	$(call ASSERT_DYNSYM,$(LIBRARIES_DIR)/libweak-func-missing.so,missing_callback,WEAK)
	$(call ASSERT_RELOC,$(LIBRARIES_DIR)/libweak-func-missing.so,R_386_GLOB_DAT,missing_callback)
	# Weak data ref (R_386_GLOB_DAT) -- resolved variant.
	$(CC) $(CFLAGS) libs/weak_data.c -shared -fPIC -DWEAK_DATA_NAME=weak_data -o $(LIBRARIES_DIR)/libweak-data-resolved.so
	$(call ASSERT_DYNSYM,$(LIBRARIES_DIR)/libweak-data-resolved.so,weak_data,WEAK)
	$(call ASSERT_RELOC,$(LIBRARIES_DIR)/libweak-data-resolved.so,R_386_GLOB_DAT,weak_data)
	# Weak data ref (R_386_GLOB_DAT) -- missing variant.
	$(CC) $(CFLAGS) libs/weak_data.c -shared -fPIC -DWEAK_DATA_NAME=missing_weak_data -o $(LIBRARIES_DIR)/libweak-data-missing.so
	$(call ASSERT_DYNSYM,$(LIBRARIES_DIR)/libweak-data-missing.so,missing_weak_data,WEAK)
	$(call ASSERT_RELOC,$(LIBRARIES_DIR)/libweak-data-missing.so,R_386_GLOB_DAT,missing_weak_data)
	# Weak function ref WITHOUT NULL-guard (R_386_JUMP_SLOT) -- resolved variant.
	$(CC) $(CFLAGS) libs/weak_func_plt.c -shared -fPIC -DCALLBACK_NAME=main_callback -o $(LIBRARIES_DIR)/libweak-plt-resolved.so
	$(call ASSERT_DYNSYM,$(LIBRARIES_DIR)/libweak-plt-resolved.so,main_callback,WEAK)
	$(call ASSERT_RELOC,$(LIBRARIES_DIR)/libweak-plt-resolved.so,R_386_JUMP_SLOT,main_callback)
	# Weak function ref WITHOUT NULL-guard (R_386_JUMP_SLOT) -- missing variant.
	$(CC) $(CFLAGS) libs/weak_func_plt.c -shared -fPIC -DCALLBACK_NAME=missing_plt_callback -o $(LIBRARIES_DIR)/libweak-plt-missing.so
	$(call ASSERT_DYNSYM,$(LIBRARIES_DIR)/libweak-plt-missing.so,missing_plt_callback,WEAK)
	$(call ASSERT_RELOC,$(LIBRARIES_DIR)/libweak-plt-missing.so,R_386_JUMP_SLOT,missing_plt_callback)
	# Strong undefined function call (R_386_JUMP_SLOT) -- regression guard.
	$(CC) $(CFLAGS) libs/strong_missing.c -shared -fPIC -o $(LIBRARIES_DIR)/libstrong-missing.so
	$(call ASSERT_DYNSYM,$(LIBRARIES_DIR)/libstrong-missing.so,strong_missing,GLOBAL)
	$(call ASSERT_RELOC,$(LIBRARIES_DIR)/libstrong-missing.so,R_386_JUMP_SLOT,strong_missing)

libs-clean:
	rm -f $(LIBRARIES_DIR)/libweak-func-resolved.so
	rm -f $(LIBRARIES_DIR)/libweak-func-missing.so
	rm -f $(LIBRARIES_DIR)/libweak-data-resolved.so
	rm -f $(LIBRARIES_DIR)/libweak-data-missing.so
	rm -f $(LIBRARIES_DIR)/libweak-plt-resolved.so
	rm -f $(LIBRARIES_DIR)/libweak-plt-missing.so
	rm -f $(LIBRARIES_DIR)/libstrong-missing.so

%.o: %.c
	$(CC) $(CFLAGS) -fPIE $< -c -o $@
