# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

"""Nanvix build script for posix-tests.

Usage:
    ./z setup     # Download Nanvix sysroot
    ./z build     # Cross-compile all test suites
    ./z test      # Run test suite (smoke + integration + functional)
    ./z release   # Package release tarball
    ./z clean     # Remove build artifacts
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from nanvix_zutil import CFG_SYSROOT, CFG_TOOLCHAIN, EXIT_MISSING_DEP, ZScript, log

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Makefile variable names (build-system-specific).
_MAKE_VAR_SYSROOT = "NANVIX_SYSROOT"
_MAKE_VAR_TOOLCHAIN = "NANVIX_TOOLCHAIN"
_MAKE_VAR_PLATFORM = "PLATFORM"
_MAKE_VAR_PROCESS_MODE = "PROCESS_MODE"
_MAKE_VAR_MEMORY_SIZE = "MEMORY_SIZE"

# All test suites built by the Makefile.
ALL_SUITES = [
    "c-bindings", "dlfcn-c", "dlfcn-pie-c", "echo-c", "echo-cpp",
    "file-c", "hello-c", "hello-cpp", "memory-c", "misc-c",
    "network-c", "noop-c", "noop-cpp", "thread-c",
]

# Suites that can run via plain nanvixd invocation (no special infra).
TESTABLE_SUITES = [
    "c-bindings", "echo-c", "echo-cpp", "hello-c", "hello-cpp",
    "memory-c", "noop-c", "noop-cpp", "thread-c",
]

# Docker image for cross-compilation.
DOCKER_IMAGE = "nanvix/toolchain:latest-minimal"

# Windows host-native binaries needed for test execution.
WINDOWS_HOST_BINARIES = ["nanvixd.exe", "kernel.elf"]


class PosixTestsBuild(ZScript):
    """Build script for nanvix/posix-tests."""

    if IS_WINDOWS:
        # Windows sysroot verification only checks files present in the
        # Linux release tarball.  nanvixd.exe and kernel.elf are
        # downloaded separately by _download_windows_binaries().
        SYSROOT_REQUIRED_FILES: tuple[str, ...] = (
            "lib/libposix.a",
            "lib/user.ld",
        )
        SYSROOT_MULTI_PROCESS_FILES: tuple[str, ...] = ()

    def _make_args(self, *targets: str) -> list[str]:
        """Build the common make argument list."""
        sysroot = self.config.get(CFG_SYSROOT, "")
        if not sysroot:
            log.fatal(
                f"{CFG_SYSROOT} is not set.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first to download the sysroot.",
            )
        toolchain = self.config.get(CFG_TOOLCHAIN, "/opt/nanvix")

        args = [
            "make", "-C", "src",
            f"{_MAKE_VAR_SYSROOT}={sysroot}",
            f"{_MAKE_VAR_TOOLCHAIN}={toolchain}",
            f"{_MAKE_VAR_PLATFORM}={self.config.machine}",
            f"{_MAKE_VAR_PROCESS_MODE}={self.config.deployment_mode}",
            f"{_MAKE_VAR_MEMORY_SIZE}={self.config.memory_size}",
        ]

        args.extend(targets)
        return args

    # ---- Lifecycle hooks -------------------------------------------------

    def setup(self) -> None:
        """Download the Nanvix sysroot."""
        super().setup()
        if IS_WINDOWS:
            self._download_windows_binaries()

    def _has_native_toolchain(self) -> bool:
        """Check if the native cross-compilation toolchain is available."""
        toolchain = self.config.get(CFG_TOOLCHAIN, "/opt/nanvix")
        cc = Path(toolchain) / "bin" / "i686-nanvix-gcc"
        return cc.is_file()

    def build(self) -> None:
        """Cross-compile all POSIX test suites for Nanvix.

        Uses the native toolchain via Make if available, otherwise
        builds inside Docker (required on Windows or when the toolchain
        is not installed locally).
        """
        if IS_WINDOWS or not self._has_native_toolchain():
            self._docker_build()
        else:
            self.run(*self._make_args("all"), cwd=self.repo_root)

    def test(self) -> None:
        """Run the POSIX test suites.

        Without targets, runs the full suite (smoke + integration + functional).
        With targets (e.g. ``./z test -- test-smoke test-integration``), passes
        them directly to the Makefile.
        """
        if IS_WINDOWS:
            self._run_tests_native()
        else:
            targets = self.targets if self.targets else ["test"]
            self.run(*self._make_args(*targets), cwd=self.repo_root)

    def release(self) -> None:
        """Package the posix-tests release tarball and verify it."""
        if IS_WINDOWS:
            log.warning("Release packaging is not supported on Windows.")
            log.warning("Use a Linux host or CI to build release tarballs.")
            return
        self.run(*self._make_args("package"), cwd=self.repo_root)
        self.run(*self._make_args("verify-package"), cwd=self.repo_root)

    def clean(self) -> None:
        """Remove build artifacts."""
        if IS_WINDOWS:
            build_dir = self.repo_root / "build"
            if build_dir.is_dir():
                shutil.rmtree(build_dir)
                log.info("Removed build/")
        else:
            self.run("make", "-C", "src", "clean", cwd=self.repo_root)

    # ---- Windows: Docker build -------------------------------------------

    def _docker_build(self) -> None:
        """Build test suites via Docker on Windows.

        Invokes ``docker build`` directly instead of going through the
        host Makefile, which requires POSIX shell constructs.
        """
        docker_image = self._resolve_docker_image()
        build_dir = self.repo_root / "build"
        build_dir.mkdir(exist_ok=True)

        # Determine the sysroot path relative to the repo root.
        # nanvix-zutil places files in .nanvix/sysroot/; the old 'make init'
        # places them directly in .nanvix/.  Pass the correct path so the
        # Dockerfile can forward it to Make.
        sysroot_rel = ".nanvix/sysroot"
        if not (self.repo_root / sysroot_rel / "lib" / "libposix.a").is_file():
            sysroot_rel = ".nanvix"

        log.info(f"Building via Docker ({docker_image})...")
        subprocess.run(
            [
                "docker", "build",
                "--build-arg", f"BASE_IMAGE={docker_image}",
                "--build-arg", f"NANVIX_SYSROOT={sysroot_rel}",
                "--output", f"type=local,dest=build",
                ".",
            ],
            cwd=self.repo_root,
            check=True,
            env={**os.environ, "DOCKER_BUILDKIT": "1"},
        )

        # Count produced binaries.
        elfs = list(build_dir.glob("*.elf"))
        log.success(f"Built {len(elfs)} test binaries in build/")

    def _resolve_docker_image(self) -> str:
        """Resolve the Docker image tag from the Nanvix version.

        Derives the tag from the nanvix-version in nanvix.toml:
        ``0.12.432`` → ``nanvix/toolchain:v0.12.x-minimal``.
        Falls back to ``latest-minimal`` if the version is unavailable.
        """
        # Check for cached .docker-image (from 'make init').
        cached = self.repo_root / ".nanvix" / ".docker-image"
        if cached.is_file():
            tag = cached.read_text().strip()
            if tag:
                return tag

        # Derive from nanvix-version in manifest.
        version = getattr(self.manifest, "sysroot_ref", None)
        if version:
            ver = version.value.lstrip("v")
            parts = ver.split(".")
            if len(parts) >= 2:
                major_minor = f"{parts[0]}.{parts[1]}"
                return f"nanvix/toolchain:v{major_minor}.x-minimal"

        return DOCKER_IMAGE

    # ---- Windows: native test execution ----------------------------------

    def _run_tests_native(self) -> None:
        """Run tests natively on Windows using nanvixd.exe."""
        sysroot = self.config.get(CFG_SYSROOT, "")
        if not sysroot:
            log.fatal(
                f"{CFG_SYSROOT} is not set.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first.",
            )
        nanvixd = Path(sysroot) / "bin" / "nanvixd.exe"
        if not nanvixd.is_file():
            log.fatal(
                "nanvixd.exe not found in sysroot.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` to download Windows host binaries.",
            )
        build_dir = self.repo_root / "build"

        # --- Smoke tests ---
        print("Running smoke tests...")
        for suite in ALL_SUITES:
            binary = build_dir / f"{suite}.elf"
            if binary.is_file():
                print(f"OK   {suite} (binary exists)")
            else:
                print(f"SKIP {suite} (binary not found)")

        # --- Integration tests ---
        if self.config.deployment_mode == "standalone":
            print("Skipping integration tests for standalone mode.")
            return

        print("Running integration tests...")
        failed = []
        for suite in TESTABLE_SUITES:
            binary = build_dir / f"{suite}.elf"
            if not binary.is_file():
                print(f"SKIP {suite}")
                continue
            print(f"RUN  {suite}...")
            try:
                result = subprocess.run(
                    [str(nanvixd.resolve()), "--", str(binary.resolve())],
                    stdin=subprocess.DEVNULL,
                    timeout=120,
                )
                if result.returncode != 0:
                    print(f"FAIL {suite} (exit code {result.returncode})")
                    failed.append(suite)
                else:
                    print(f"OK   {suite}")
            except subprocess.TimeoutExpired:
                print(f"FAIL {suite} (timeout)")
                failed.append(suite)

        if failed:
            raise RuntimeError(
                f"{len(failed)} test suite(s) failed: {' '.join(failed)}"
            )
        print("\t\t*** POSIX tests PASSED ***")

    # ---- Windows: binary download ----------------------------------------

    def _download_windows_binaries(self) -> None:
        """Download native Windows host binaries from the Nanvix release.

        On Windows, tests run natively using nanvixd.exe. These binaries
        are distributed as part of the Windows-specific release assets.
        """
        from nanvix_zutil import CFG_GH_TOKEN

        sysroot_path = Path(self.config.get(CFG_SYSROOT))
        bin_dir = sysroot_path / "bin"

        # Skip if already present.
        required = ["nanvixd.exe"]
        if all((bin_dir / b).is_file() for b in required):
            log.info("Windows host binaries already present in sysroot")
            return

        # Resolve the release tag.
        tag = self.manifest.sysroot_ref.value
        if not tag.startswith("v"):
            tag = f"v{tag}"

        machine = self.config.machine
        mode = self.config.deployment_mode
        mem = self.config.memory_size
        asset_prefix = f"nanvix-windows-x86-{machine}-{mode}-release-{mem}"

        log.info(f"Downloading Windows host binaries ({asset_prefix})...")

        # Query GitHub releases API.
        api_url = f"https://api.github.com/repos/nanvix/nanvix/releases/tags/{tag}"
        try:
            req = urllib.request.Request(api_url)
            req.add_header("Accept", "application/vnd.github+json")
            gh_token = self.config.get(CFG_GH_TOKEN)
            if gh_token:
                req.add_header("Authorization", f"Bearer {gh_token}")
            with urllib.request.urlopen(req, timeout=30) as resp:
                release = json.loads(resp.read())
        except Exception as exc:
            log.warning(f"Cannot fetch release {tag}: {exc}")
            log.warning("Windows binaries not available — tests may not work.")
            return

        # Find matching Windows asset.
        asset_url = None
        asset_name = None
        for a in release.get("assets", []):
            name = a.get("name", "")
            if name.startswith(asset_prefix) and name.endswith(".zip"):
                asset_url = a["browser_download_url"]
                asset_name = name
                break

        if not asset_url:
            log.warning(
                f"No Windows asset matching '{asset_prefix}*.zip' in release {tag}"
            )
            return

        # Download to cache.
        cache_dir = self.nanvix_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        zip_path = cache_dir / asset_name

        if not zip_path.is_file():
            log.info(f"Downloading {asset_name}...")
            urllib.request.urlretrieve(asset_url, str(zip_path))

        # Extract host-native binaries into sysroot/bin/.
        bin_dir.mkdir(parents=True, exist_ok=True)
        wanted = set(WINDOWS_HOST_BINARIES)
        with zipfile.ZipFile(zip_path) as zf:
            for entry in zf.namelist():
                basename = Path(entry).name
                if basename in wanted:
                    data = zf.read(entry)
                    dest = bin_dir / basename
                    dest.write_bytes(data)
                    log.info(f"Extracted {basename} to sysroot/bin/")

        # Verify required binaries exist.
        missing = [b for b in required if not (bin_dir / b).is_file()]
        if missing:
            log.warning(
                f"Required Windows binaries missing after download: "
                f"{', '.join(missing)}"
            )
            log.warning("Tests may not work without these binaries.")
        else:
            log.success("Windows host binaries installed")


if __name__ == "__main__":
    PosixTestsBuild.main()
