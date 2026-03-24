# POSIX C Test Suites for Nanvix

A collection of C test suites that validate the POSIX compatibility layer of
[Nanvix](https://github.com/nanvix/nanvix). These tests exercise file system operations,
threading, memory management, networking, dynamic linking, and other POSIX interfaces.

## Test Suites

| Suite | Description |
|---|---|
| `file-c` | File system operations (open, read, write, stat, link, mkdir, etc.) |
| `thread-c` | Threading, mutexes, condition variables, rwlocks, TLS, TDA |
| `memory-c` | malloc/free, aligned\_alloc, realloc, mmap/munmap, heap stress |
| `misc-c` | UID/GID, clock/time, uname, hostname, nanosleep, getenv |
| `network-c` | IPv4 (INET) and Unix domain sockets |
| `dlfcn-c` | Dynamic linking (dlopen, dlsym) |
| `dlfcn-pie-c` | PIE dynamic linking |
| `c-bindings` | Rust-C FFI type size/alignment validation |

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- [GitHub CLI](https://cli.github.com/) (`gh`)
- [KVM](https://github.com/nanvix/nanvix/blob/main/doc/setup.md#4-setup-kvm) enabled

## Quick Start

```bash
# 1. Download the latest Nanvix release (provides nanvixd.elf, libposix.a, and user.ld).
make init

# 2. Build all test suite ELFs using the Nanvix minimal Docker image.
make

# 3. Run a specific test suite on Nanvix.
make run SUITE=file-c
```

## Project Structure

```plain
.
├── z                  # Bootstrap wrapper for zutils
├── .nanvix/z.py       # Build script (setup, build, test, release, clean)
├── Makefile           # Host-side build rules (init, build via Docker, run, clean)
├── Dockerfile         # Cross-compilation inside the Nanvix Docker image
└── src/
    ├── Makefile       # Container-side orchestrator
    ├── file-c/        # File system test suite
    ├── thread-c/      # Threading test suite
    ├── memory-c/      # Memory management test suite
    ├── misc-c/        # Miscellaneous POSIX test suite
    ├── network-c/     # Networking test suite
    ├── dlfcn-c/       # Dynamic linking test suite
    ├── dlfcn-pie-c/   # PIE dynamic linking test suite
    └── c-bindings/    # Rust-C FFI validation
```

## How It Works

### Cross-Compilation

Test suites are cross-compiled using the `i686-nanvix-gcc` toolchain inside the
[`nanvix/toolchain`](https://hub.docker.com/r/nanvix/toolchain) minimal Docker image.

Each test suite is linked against:

- **`libposix.a`** — Nanvix POSIX compatibility layer (from the Nanvix release)
- **`libc.a`** — Newlib C library (from the toolchain)
- **`user.ld`** — Linker script defining the Nanvix user-space memory layout (from the Nanvix release)

### Running

`nanvixd.elf` is the Nanvix daemon that boots a microkernel VM and runs your test binary
inside it. The `-console-file /dev/stdout` flag redirects the test output to the terminal.

## License

This project is distributed under the [MIT License](LICENSE).
