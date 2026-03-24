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
#   'make init' must be run first to download the Nanvix release into .nanvix/.

# BASE_IMAGE is resolved by 'make init' and saved in .nanvix/.docker-image.
ARG BASE_IMAGE=nanvix/toolchain:latest-minimal
FROM ${BASE_IMAGE} AS builder

WORKDIR /workspace

# Copy source files and Nanvix release artifacts.
COPY src/ src/
COPY Makefile ./
COPY .nanvix/ .nanvix/

# Build all test suites.
RUN mkdir -p build && make compile

# Export the compiled binaries.
FROM scratch
COPY --from=builder /workspace/build/*.elf /
