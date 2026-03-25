# POSIX C/C++ Test Suites for Nanvix

A collection of C and C++ test suites and programs that validate the POSIX compatibility layer of
[Nanvix](https://github.com/nanvix/nanvix). These cover file system operations,
threading, memory management, networking, dynamic linking, and other POSIX interfaces,
as well as simple echo, hello-world, and no-op benchmarks.

## Test Suites

| Suite | Description |
|---|---|
| `c-bindings` | Rust-C FFI type size/alignment validation |
| `dlfcn-c` | Dynamic linking (dlopen, dlsym) |
| `dlfcn-pie-c` | PIE dynamic linking |
| `echo-c` | Echo stdin to stdout (C) |
| `echo-cpp` | Echo stdin to stdout (C++) |
| `file-c` | File system operations (open, read, write, stat, link, mkdir, etc.) |
| `hello-c` | Hello world (C) |
| `hello-cpp` | Hello world (C++) |
| `memory-c` | malloc/free, aligned\_alloc, realloc, mmap/munmap, heap stress |
| `misc-c` | UID/GID, clock/time, uname, hostname, nanosleep, getenv |
| `network-c` | IPv4 (INET) and Unix domain sockets |
| `noop-c` | No-op program (C) |
| `noop-cpp` | No-op program (C++) |
| `thread-c` | Threading, mutexes, condition variables, rwlocks, TLS, TDA |

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
    ├── c-bindings/    # Rust-C FFI validation
    ├── dlfcn-c/       # Dynamic linking test suite
    ├── dlfcn-pie-c/   # PIE dynamic linking test suite
    ├── echo-c/        # Echo program (C)
    ├── echo-cpp/      # Echo program (C++)
    ├── file-c/        # File system test suite
    ├── hello-c/       # Hello world (C)
    ├── hello-cpp/     # Hello world (C++)
    ├── memory-c/      # Memory management test suite
    ├── misc-c/        # Miscellaneous POSIX test suite
    ├── network-c/     # Networking test suite
    ├── noop-c/        # No-op program (C)
    ├── noop-cpp/      # No-op program (C++)
    └── thread-c/      # Threading test suite
```

## How It Works

### Cross-Compilation

Test suites are cross-compiled using the `i686-nanvix-gcc` toolchain inside the
[`nanvix/toolchain`](https://hub.docker.com/r/nanvix/toolchain) minimal Docker image.

Each test suite is linked against:

- **`libposix.a`** — Nanvix POSIX compatibility layer (from the Nanvix release)
- **`libc.a`** — Newlib C library (from the toolchain)
- **`libstdc++.a`** — C++ standard library (from the toolchain, for C++ suites)
- **`user.ld`** — Linker script defining the Nanvix user-space memory layout (from the Nanvix release)

### Running

`nanvixd.elf` is the Nanvix daemon that boots a microkernel VM and runs your test binary
inside it. The `-console-file /dev/stdout` flag redirects the test output to the terminal.

## License

This project is distributed under the [MIT License](LICENSE).
