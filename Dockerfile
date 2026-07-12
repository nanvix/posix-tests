# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

# Build all POSIX test suites using the Nanvix C/Clang SDK image.
#
# Usage (run from the repository root):
#   DOCKER_BUILDKIT=1 docker build \
#       --build-arg BASE_IMAGE=ghcr.io/nanvix/nanvix-sdk-c-clang@sha256:... \
#       --output type=local,dest=build .
#
# Build-time headers, libraries, startup objects, and linker scripts are all
# provided by this content-addressed SDK image.
ARG BASE_IMAGE=ghcr.io/nanvix/nanvix-sdk-c-clang@sha256:f61737cb0780e6a2058c6d0bdf8ae5562db18de437173b2bcbbe6973abd3689f
FROM ${BASE_IMAGE} AS builder

WORKDIR /workspace

# Copy source files.
COPY src/ src/
COPY Makefile ./

# Build configuration — forwarded from z.py or overridden via --build-arg.
ARG PLATFORM=microvm
ARG PROCESS_MODE=single-process
ARG MEMORY_SIZE=256mb

# Build all test suites.
RUN mkdir -p build && make compile \
    PLATFORM=${PLATFORM} \
    PROCESS_MODE=${PROCESS_MODE} \
    MEMORY_SIZE=${MEMORY_SIZE}

# Export the compiled binaries. Dynamic-loader suites are gated off because
# the pinned SDK advertises features.dynamic_loader=false.
FROM scratch
COPY --from=builder /workspace/build/ /
