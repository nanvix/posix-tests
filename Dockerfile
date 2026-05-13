# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

# Build all POSIX test suites using the Nanvix minimal Docker image.
#
# Usage (run from the repository root):
#   DOCKER_BUILDKIT=1 docker build \
#       --build-arg BASE_IMAGE=$(cat .nanvix/.docker-image) \
#       --output type=local,dest=build .
#
# Prerequisites:
#   'make init' must be run first to download the Nanvix release into .nanvix/sysroot/.

# BASE_IMAGE is resolved by 'make init' and saved in .nanvix/.docker-image.
ARG BASE_IMAGE=ghcr.io/nanvix/toolchain-gcc:sha-34a3641
FROM ${BASE_IMAGE} AS builder

WORKDIR /workspace

# Copy source files and Nanvix release artifacts.
COPY src/ src/
COPY Makefile ./
COPY .nanvix/ .nanvix/

# Build configuration — forwarded from z.py or overridden via --build-arg.
ARG PLATFORM=microvm
ARG PROCESS_MODE=multi-process
ARG MEMORY_SIZE=128mb

# Build all test suites.
RUN mkdir -p build && make compile \
    PLATFORM=${PLATFORM} \
    PROCESS_MODE=${PROCESS_MODE} \
    MEMORY_SIZE=${MEMORY_SIZE}

# Export the compiled binaries.
FROM scratch
COPY --from=builder /workspace/build/*.elf /
