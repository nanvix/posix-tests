# POSIX C/C++ Test Suites for Nanvix

A collection of C and C++ test suites and programs that validate the POSIX compatibility layer of
[Nanvix](https://github.com/nanvix/nanvix). These cover file system operations,
threading, memory management, networking, dynamic linking, and other POSIX interfaces,
as well as simple echo, hello-world, and no-op benchmarks.

## Test Suites

| Suite | Description |
|---|---|
| `c-bindings` | Rust-C FFI type size/alignment validation |
| `dlfcn-c` | Dynamic linking (dlopen, dlsym; gated by SDK capability) |
| `dlfcn-global-c` | RTLD_GLOBAL symbol resolution (gated by SDK capability) |
| `dlfcn-needed-c` | DT_NEEDED dependency loading (gated by SDK capability) |
| `dlfcn-pie-c` | PIE dynamic linking (gated by SDK capability) |
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
# 1. Download the Nanvix 0.20.0 runtime and configure the pinned SDK image.
./z setup --with-docker \
  ghcr.io/nanvix/nanvix-sdk-c-clang@sha256:f61737cb0780e6a2058c6d0bdf8ae5562db18de437173b2bcbbe6973abd3689f

# 2. Build all supported test suite ELFs with Clang/LLVM.
./z build

# 3. Run the test suites on Nanvix.
./z test
```

The direct Make flow remains available: run `make init`, `make`, and then
`make run SUITE=file-c`. `make init` downloads runtime binaries only.

Nanvix v0.20.0 publishes runtime assets only for microvm single-process and
standalone deployments at 256 MB; it has no Hyperlight or 128 MB artifacts.
Consequently, the supported manifest and CI matrix use microvm at 256 MB only.
Missing Hyperlight or 128 MB assets are runtime compatibility constraints, not
port failures. All test types, including full standalone and Windows standalone
testing, remain enabled at 256 MB.

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
    ├── dlfcn-global-c/ # RTLD_GLOBAL test suite
    ├── dlfcn-needed-c/ # DT_NEEDED test suite
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

Test suites are cross-compiled with `clang` and `clang++` from the pinned
[`nanvix-sdk-c-clang`](https://github.com/nanvix/nanvix-sdk/pkgs/container/nanvix-sdk-c-clang)
image. The SDK compiler drivers default to `i686-unknown-nanvix`.

All final links use the compiler drivers. They select:

- **`crt0.o`, `user.ld`, libc, libm, and compiler-rt builtins** from the SDK
- **libc++, libc++abi, and libunwind** from the SDK for C++ suites

The sysroot downloaded by `./z setup`, `--with-nanvix`, or `make init` is
runtime-only and supplies `nanvixd`, the kernel, and supporting runtime
binaries. It is never used for compilation or linking.

The pinned SDK reports `features.dynamic_loader=false`; therefore the four
`dlfcn-*` suites are retained in the source tree but excluded from builds,
packages, and test runs until an SDK with dynamic-loader support is selected.

Nanvix v0.20.0 single-process does not provide the filesystem and socket
services required by `file-c` and `network-c`; those suites are reported as
skipped in that mode and remain fully exercised in standalone mode.

### Running

`nanvixd.elf` is the Nanvix daemon that boots a microkernel VM and runs your test binary
inside it. The `-console-file /dev/stdout` flag redirects the test output to the terminal.

## License

This project is distributed under the [MIT License](LICENSE).
