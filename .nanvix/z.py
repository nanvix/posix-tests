# Copyright(c) The Maintainers of Nanvix.
# Licensed under the MIT License.

"""Nanvix build script for posix-tests.

Usage:
    ./z setup     # Download Nanvix sysroot
    ./z build     # Cross-compile all test suites
    ./z test      # Run test suite (smoke + integration + functional)
    ./z release   # Package release tarball
    ./z clean     # Remove build artifacts

Options:
    --with-nanvix PATH  Use local Nanvix binaries from PATH instead of
                        the downloaded sysroot binaries. PATH should point
                        to a Nanvix build directory containing bin/ and lib/.
                        The path is persisted in .nanvix/env.json, so it
                        only needs to be passed once. Pass again to change
                        it. Works on both Linux and Windows.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from nanvix_zutil import (
    CFG_SYSROOT,
    EXIT_MISSING_DEP,
    TOOLCHAIN_CONTAINER_PATH,
    ZScript,
    log,
    make_initrd,
    run,
)
from nanvix_zutil.helpers import InitRdArgs
from nanvix_zutil.paths import (
    bin_out,
    nanvix_root,
    repo_root,
    test_out,
)

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Makefile variable names (build-system-specific).
_MAKE_VAR_TOOLCHAIN = "NANVIX_TOOLCHAIN"
_MAKE_VAR_PLATFORM = "PLATFORM"
_MAKE_VAR_PROCESS_MODE = "PROCESS_MODE"
_MAKE_VAR_MEMORY_SIZE = "MEMORY_SIZE"

# The pinned SDK manifest advertises features.dynamic_loader=false.
SDK_DYNAMIC_LOADER = False

BASE_SUITES = [
    "c-bindings",
    "echo-c",
    "echo-cpp",
    "file-c",
    "hello-c",
    "hello-cpp",
    "memory-c",
    "misc-c",
    "network-c",
    "noop-c",
    "noop-cpp",
    "thread-c",
]

DYNAMIC_LOADER_SUITES = [
    "dlfcn-c",
    "dlfcn-global-c",
    "dlfcn-needed-c",
    "dlfcn-pie-c",
]

ALL_SUITES = BASE_SUITES + (DYNAMIC_LOADER_SUITES if SDK_DYNAMIC_LOADER else [])

# Suites that can run via plain nanvixd invocation (no special infra).
TESTABLE_SUITES = [
    "c-bindings",
    "echo-c",
    "echo-cpp",
    "hello-c",
    "hello-cpp",
    "memory-c",
    "misc-c",
    "noop-c",
    "noop-cpp",
    "thread-c",
]

# These suites need services that are only present in standalone runtimes.
STANDALONE_INFRASTRUCTURE_SUITES = ["file-c", "network-c"]

# Suites that require ramfs-bundled shared libraries and only run in standalone mode.
STANDALONE_ONLY_SUITES = ["dlfcn-c", "dlfcn-pie-c"] if SDK_DYNAMIC_LOADER else []

# Suites that require host networking (passed as -allow-host-networking to nanvixd).
SUITES_REQUIRING_NETWORKING: set[str] = {
    "network-c",
}

# Shared libraries that must be bundled into the ramfs for specific suites.
# Maps suite name to a list of (source_filename_in_build_dir, ramfs_target_path).
SUITE_RAMFS_LIBS: dict[str, list[tuple[str, str]]] = {
    "dlfcn-c": [("libmul.so", "lib/libmul.so")],
    "dlfcn-pie-c": [("libmul-pie.so", "lib/libmul-pie.so")],
}

# Docker image for cross-compilation.
DOCKER_IMAGE = (
    "ghcr.io/nanvix/nanvix-sdk-c-clang"
    "@sha256:f61737cb0780e6a2058c6d0bdf8ae5562db18de437173b2bcbbe6973abd3689f"
)

# Windows host-native binaries needed for test execution.
WINDOWS_HOST_BINARIES = [
    "nanvixd.exe",
    "kernel.elf",
    "mkimage.exe",
    "mkramfs.exe",
    "procd.elf",
    "memd.elf",
    "vfsd.elf",
]

# Config key for persisting the --with-nanvix path in env.json.
_CFG_LOCAL_NANVIX = "local_nanvix_path"

# ---------------------------------------------------------------------------
# Early --with-nanvix extraction
# ---------------------------------------------------------------------------
# The nanvix-zutil CLI inspects sys.argv to find the subcommand *before*
# calling PosixTestsBuild.main().  The shell wrappers (z.sh / z.ps1) strip
# --with-nanvix PATH from argv and pass it via the WITH_NANVIX
# environment variable.  Pick it up here at import time.

_EARLY_LOCAL_NANVIX: str | None = os.environ.get("WITH_NANVIX") or None


class PosixTestsBuild(ZScript):
    """Build script for nanvix/posix-tests."""

    _local_nanvix_path: str | None = None

    SYSROOT_REQUIRED_FILES: tuple[str, ...] = (
        "bin/nanvixd.elf",
        "bin/kernel.elf",
        "bin/mkramfs.elf",
    )

    # The base setup flow overlays host-native Windows tools before verification.
    SYSROOT_REQUIRED_FILES_WINDOWS: tuple[str, ...] = (
        "bin/nanvixd.exe",
        "bin/kernel.elf",
        "bin/mkramfs.exe",
    )

    SYSROOT_MULTI_PROCESS_FILES: tuple[str, ...] = ()

    # ---- CLI entry point -------------------------------------------------

    @classmethod
    def main(cls) -> None:
        """Pre-parse ``--with-nanvix`` and delegate to ZScript.main()."""
        if _EARLY_LOCAL_NANVIX is not None:
            cls._local_nanvix_path = _EARLY_LOCAL_NANVIX
        super().main()

    # ---- Local Nanvix overlay --------------------------------------------

    def _overlay_local_nanvix(self) -> None:
        """Copy local Nanvix runtime binaries into the sysroot.

        When ``--with-nanvix PATH`` is supplied (or was previously
        persisted in config), this method copies runtime binaries
        (nanvixd, kernel, …) from the local Nanvix build directory into
        the configured runtime sysroot.
        Build-time headers, libraries, startup objects, and linker scripts
        always come from the pinned SDK image.

        The path is persisted in ``.nanvix/env.json`` on first use so
        that later commands pick it up automatically.

        Works on both Linux (ELF binaries) and Windows (.exe binaries).
        """
        # CLI flag takes precedence; fall back to persisted config.
        nanvix_path = self._local_nanvix_path or self.config.get(_CFG_LOCAL_NANVIX, "")
        if not nanvix_path:
            return

        nanvix_path = os.path.abspath(os.path.expanduser(nanvix_path))
        if not os.path.isdir(nanvix_path):
            log.warning(f"--with-nanvix path no longer exists: {nanvix_path}")
            return

        # Persist so subsequent commands reuse the same path.
        if self.config.get(_CFG_LOCAL_NANVIX, "") != nanvix_path:
            self.config.set(_CFG_LOCAL_NANVIX, nanvix_path)
            self.config.save()

        sysroot = self.config.get(CFG_SYSROOT, "")
        if not sysroot:
            return

        nanvix_dir = Path(nanvix_path)
        sysroot_path = Path(sysroot)

        log.info(f"Overlaying local Nanvix binaries from {nanvix_dir}")

        # -- Binaries ------------------------------------------------------
        bin_src = nanvix_dir / "bin"
        bin_dst = sysroot_path / "bin"
        bin_dst.mkdir(parents=True, exist_ok=True)

        if IS_WINDOWS:
            binaries = [
                "nanvixd.exe",
                "kernel.elf",
                "mkimage.exe",
                "mkramfs.exe",
                "procd.elf",
                "memd.elf",
                "vfsd.elf",
            ]
        else:
            binaries = [
                "nanvixd.elf",
                "kernel.elf",
                "mkimage.elf",
                "mkramfs.elf",
                "linuxd.elf",
                "uservm.elf",
                "procd.elf",
                "memd.elf",
                "vfsd.elf",
            ]

        for name in binaries:
            src = bin_src / name
            if src.is_file():
                shutil.copy2(src, bin_dst / name)
                log.info(f"  Copied {name}")

    # ---- Helpers ---------------------------------------------------------

    def _make_args(self, *targets: str) -> list[str]:
        """Build the common make argument list."""
        toolchain_p = str(TOOLCHAIN_CONTAINER_PATH)

        args = [
            "make",
            "-C",
            "src",
            f"{_MAKE_VAR_TOOLCHAIN}={toolchain_p}",
            f"{_MAKE_VAR_PLATFORM}={self.config.machine}",
            f"{_MAKE_VAR_PROCESS_MODE}={self.config.deployment_mode}",
            f"{_MAKE_VAR_MEMORY_SIZE}={self.config.memory_size}",
            f"DYNAMIC_LOADER={'true' if SDK_DYNAMIC_LOADER else 'false'}",
        ]

        args.extend(targets)
        return args

    def _has_native_toolchain(self) -> bool:
        """Check if the native cross-compilation toolchain is available."""
        toolchain = str(TOOLCHAIN_CONTAINER_PATH)
        sdk_manifest = Path(toolchain) / "nanvix-sdk.json"
        cc = Path(toolchain) / "bin" / "clang"
        cxx = Path(toolchain) / "bin" / "clang++"
        return sdk_manifest.is_file() and cc.is_file() and cxx.is_file()

    # ---- Lifecycle hooks -------------------------------------------------

    def setup(self) -> bool:
        """Download the Nanvix runtime sysroot."""
        local_nanvix = self._local_nanvix_path
        if local_nanvix:
            local_nanvix = os.path.abspath(os.path.expanduser(local_nanvix))

        if local_nanvix and os.path.isdir(local_nanvix):
            # Use local Nanvix binaries instead of downloading the sysroot.
            log.info(f"Using local Nanvix from {local_nanvix}")

            from nanvix_zutil import Sysroot

            sysroot_dir = nanvix_root() / "sysroot"
            if sysroot_dir.exists():
                shutil.rmtree(sysroot_dir)
            sysroot_dir.mkdir(parents=True)

            local = Path(local_nanvix)

            # Copy binaries.
            bin_dst = sysroot_dir / "bin"
            bin_dst.mkdir()
            if IS_WINDOWS:
                bin_names = [
                    "nanvixd.exe",
                    "kernel.elf",
                    "mkimage.exe",
                    "mkramfs.exe",
                    "procd.elf",
                    "memd.elf",
                    "vfsd.elf",
                ]
            else:
                bin_names = [
                    "nanvixd.elf",
                    "kernel.elf",
                    "mkimage.elf",
                    "mkramfs.elf",
                    "linuxd.elf",
                    "uservm.elf",
                    "procd.elf",
                    "memd.elf",
                    "vfsd.elf",
                ]
            for name in bin_names:
                src = local / "bin" / name
                if src.is_file():
                    shutil.copy2(src, bin_dst / name)
                    log.info(f"  Copied bin/{name}")

            self.sysroot = Sysroot(sysroot_dir.resolve())
            self.sysroot.verify(self.sysroot_required_files())
            self.config.set(CFG_SYSROOT, str(self.sysroot.path))
            self.config.set(_CFG_LOCAL_NANVIX, local_nanvix)
            self.config.save()
            used_fallback = False
        else:
            used_fallback = super().setup()

        if IS_WINDOWS:
            self._download_windows_binaries()

        # Overlay local Nanvix binaries last so they take precedence.
        self._overlay_local_nanvix()
        return used_fallback

    def build(self) -> None:
        """Cross-compile all POSIX test suites for Nanvix.

        Uses the native toolchain via Make if available, otherwise
        builds inside Docker (required on Windows or when the toolchain
        is not installed locally).
        """
        self._overlay_local_nanvix()
        if IS_WINDOWS or not self._has_native_toolchain():
            self._docker_build()
        else:
            run(*self._make_args("all"), cwd=repo_root(), docker=self.docker)
        self._stage_release_outputs()

    def _stage_release_outputs(self) -> None:
        """Stage build/<suite>.elf for release and host-side tests.

        The inherited ``ZScript.release()`` packages ``release_dir()``
        into ``dist_dir()``; copying the per-suite ELFs into
        ``bin_out()`` is what makes them appear in the tarball, while
        ``test_out()`` is transferred to Windows CI. Missing suites are
        tolerated here; downstream consumers can fail loudly.
        """
        build_dir = repo_root() / "build"
        if not build_dir.is_dir():
            return
        destinations = (bin_out(), test_out())
        for dest in destinations:
            dest.mkdir(parents=True, exist_ok=True)
        copied = 0
        for suite in ALL_SUITES:
            src = build_dir / f"{suite}.elf"
            if src.is_file():
                for dest in destinations:
                    shutil.copy2(src, dest / src.name)
                copied += 1
        log.info(f"Staged {copied} test ELFs for release and host-side testing")

    def test(self) -> None:
        """Run the POSIX test suites.

        Runs test binaries from the ``build/`` directory using
        ``nanvixd`` from the sysroot.
        """
        self._overlay_local_nanvix()
        self._run_tests_native()

    def clean(self) -> None:
        """Remove build artifacts."""
        if IS_WINDOWS:
            build_dir = repo_root() / "build"
            if build_dir.is_dir():
                shutil.rmtree(build_dir)
                log.info("Removed build/")
        else:
            run("make", "-C", "src", "clean", cwd=repo_root())

    # ---- Docker build ----------------------------------------------------

    def _docker_build(self) -> None:
        """Build test suites via Docker.

        Invokes ``docker build`` directly instead of going through the
        host Makefile, which requires POSIX shell constructs.  Forwards
        the build configuration (platform, process mode, memory size)
        as Docker build args.
        """
        docker_image = self._resolve_docker_image()
        build_dir = repo_root() / "build"
        build_dir.mkdir(exist_ok=True)

        log.info(f"Building via Docker ({docker_image})...")
        os.environ.setdefault("DOCKER_BUILDKIT", "1")
        run(
            "docker",
            "build",
            "--build-arg",
            f"BASE_IMAGE={docker_image}",
            "--build-arg",
            f"PLATFORM={self.config.machine}",
            "--build-arg",
            f"PROCESS_MODE={self.config.deployment_mode}",
            "--build-arg",
            f"MEMORY_SIZE={self.config.memory_size}",
            "--output",
            "type=local,dest=build",
            ".",
            cwd=repo_root(),
        )

        # Count produced binaries.
        elfs = list(build_dir.glob("*.elf"))
        log.success(f"Built {len(elfs)} test binaries in build/")

    def _resolve_docker_image(self) -> str:
        """Resolve the Docker image tag for cross-compilation.

        Returns the content-addressed Nanvix C/Clang SDK image.
        """
        return DOCKER_IMAGE

    # ---- Native test execution -------------------------------------------

    def _run_tests_native(self) -> None:
        """Run test binaries from ``build/`` using ``nanvixd``."""
        sysroot = self.config.get(CFG_SYSROOT, "")
        if not sysroot:
            log.fatal(
                f"{CFG_SYSROOT} is not set.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first.",
            )
        sysroot_path = Path(sysroot)
        nanvixd_name = "nanvixd.exe" if IS_WINDOWS else "nanvixd.elf"
        nanvixd = sysroot_path / "bin" / nanvixd_name
        if not nanvixd.is_file():
            log.fatal(
                f"{nanvixd_name} not found in sysroot.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first.",
            )
        mkramfs_name = "mkramfs.exe" if IS_WINDOWS else "mkramfs.elf"
        mkramfs = sysroot_path / "bin" / mkramfs_name
        if not mkramfs.is_file():
            log.fatal(
                f"{mkramfs_name} not found in sysroot.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z setup` first.",
            )
        build_dirs = (repo_root() / "build", test_out())
        build_dir = next(
            (
                candidate
                for candidate in build_dirs
                if any((candidate / f"{suite}.elf").is_file() for suite in BASE_SUITES)
            ),
            None,
        )
        if build_dir is None:
            searched = ", ".join(str(path) for path in build_dirs)
            log.fatal(
                f"No POSIX test binaries found in: {searched}.",
                code=EXIT_MISSING_DEP,
                hint="Run `./z build` or download the Linux test artifacts first.",
            )

        # --- Smoke tests ---
        print("Running smoke tests...")
        for suite in ALL_SUITES:
            binary = build_dir / f"{suite}.elf"
            if binary.is_file():
                print(f"OK   {suite} (binary exists)")
            else:
                print(f"SKIP {suite} (binary not found)")

        # --- Integration tests ---
        print("Running integration tests...")
        if self.config.deployment_mode == "standalone":
            self._run_tests_standalone(build_dir, sysroot_path, nanvixd, mkramfs)
        else:
            self._run_tests_non_standalone(build_dir, sysroot_path, nanvixd, mkramfs)

    def _run_tests_standalone(
        self,
        build_dir: Path,
        sysroot_path: Path,
        nanvixd: Path,
        mkramfs: Path,
    ) -> None:
        """Run integration tests in standalone mode using make_initrd.

        Creates an initrd bundling each test ELF with system daemons
        via make_initrd, and a ramfs providing /tmp for any test I/O.
        The ELF is temporarily copied to the repo root because
        make_initrd resolves binary paths relative to it.
        """
        failed: list[str] = []
        for suite in (
            TESTABLE_SUITES + STANDALONE_INFRASTRUCTURE_SUITES + STANDALONE_ONLY_SUITES
        ):
            binary = build_dir / f"{suite}.elf"
            if not binary.is_file():
                print(f"SKIP {suite}")
                continue
            print(f"RUN  {suite}...")
            repo_elf = repo_root() / binary.name
            copied_elf = False
            initrd: Path | None = None
            try:
                if binary.resolve() != repo_elf.resolve():
                    if repo_elf.exists():
                        raise FileExistsError(
                            f"refusing to clobber existing {repo_elf}"
                        )
                    shutil.copy2(binary, repo_elf)
                    copied_elf = True
                if binary.name == "misc-c.elf":
                    # misc-c.elf is a special case that needs the test
                    # environment variable set to pass its internal checks.
                    initrd = make_initrd(
                        self,
                        repo_elf,
                        test_out(),
                        args=InitRdArgs(app_env=["NANVIX_TEST=1"]),
                    )
                else:
                    initrd = make_initrd(self, repo_elf, test_out())
                with tempfile.TemporaryDirectory(prefix=f"posix_test_{suite}_") as tmp:
                    tmp_path = Path(tmp)
                    ramfs_dir = tmp_path / "ramfs"
                    ramfs_dir.mkdir()
                    (ramfs_dir / "tmp").mkdir()

                    # Bundle shared libraries required by this suite.
                    libs_missing = False
                    for src_name, ramfs_path in SUITE_RAMFS_LIBS.get(suite, []):
                        src_lib = build_dir / src_name
                        if not src_lib.is_file():
                            print(f"FAIL {suite}: missing shared library {src_lib}")
                            failed.append(suite)
                            libs_missing = True
                            break
                        dst_lib = ramfs_dir / ramfs_path
                        dst_lib.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_lib, dst_lib)
                    if libs_missing:
                        continue

                    ramfs_img = tmp_path / "rootfs.img"

                    run(
                        str(mkramfs),
                        "-o",
                        str(ramfs_img),
                        str(ramfs_dir),
                        timeout=60,
                    )

                    cmd = [
                        str(nanvixd),
                        "-bin-dir",
                        str(sysroot_path / "bin"),
                        "-ramfs",
                        str(ramfs_img),
                    ]
                    if suite in SUITES_REQUIRING_NETWORKING:
                        cmd.append("-allow-host-networking")
                    cmd.extend(["--", str(initrd)])
                    log.info(f"$ {' '.join(cmd)}")
                    subprocess.run(
                        cmd,
                        cwd=repo_root(),
                        stdin=subprocess.DEVNULL,
                        text=True,
                        check=True,
                        timeout=120,
                    )
                print(f"OK   {suite}")
            except FileExistsError as exc:
                print(f"FAIL {suite} ({exc})")
                failed.append(suite)
            except subprocess.CalledProcessError as exc:
                print(f"FAIL {suite} (exit code {exc.returncode})")
                failed.append(suite)
            except subprocess.TimeoutExpired as exc:
                print(f"FAIL {suite} (timed out after {exc.timeout}s)")
                failed.append(suite)
            except SystemExit as exc:
                print(f"FAIL {suite} (SystemExit code={exc.code})")
                failed.append(suite)
            finally:
                if initrd is not None and initrd.exists():
                    initrd.unlink()
                if copied_elf and repo_elf.exists():
                    repo_elf.unlink()

        if failed:
            sys.exit(f"{len(failed)} test suite(s) failed: {' '.join(failed)}")
        print("\t\t*** POSIX tests PASSED ***")

    def _run_tests_non_standalone(
        self,
        build_dir: Path,
        sysroot_path: Path,
        nanvixd: Path,
        mkramfs: Path,
    ) -> None:
        """Run integration tests in single-process mode.

        Uses nanvixd directly with a ramfs providing /tmp for any
        test I/O. No initrd is needed as daemons are managed by the
        hypervisor.
        """
        failed: list[str] = []
        for suite in STANDALONE_INFRASTRUCTURE_SUITES:
            print(
                f"SKIP {suite} "
                "(Nanvix v0.20.0 single-process runtime lacks required services)"
            )
        for suite in TESTABLE_SUITES:
            binary = build_dir / f"{suite}.elf"
            if not binary.is_file():
                print(f"SKIP {suite}")
                continue
            print(f"RUN  {suite}...")
            try:
                with tempfile.TemporaryDirectory(prefix=f"posix_test_{suite}_") as tmp:
                    tmp_path = Path(tmp)
                    ramfs_dir = tmp_path / "ramfs"
                    ramfs_dir.mkdir()
                    (ramfs_dir / "tmp").mkdir()
                    ramfs_img = tmp_path / "rootfs.img"

                    run(
                        str(mkramfs),
                        "-o",
                        str(ramfs_img),
                        str(ramfs_dir),
                        timeout=60,
                    )

                    cmd = [
                        str(nanvixd),
                        "-bin-dir",
                        str(sysroot_path / "bin"),
                        "-ramfs",
                        str(ramfs_img),
                    ]
                    if suite in SUITES_REQUIRING_NETWORKING:
                        cmd.append("-allow-host-networking")
                    cmd.append("--")
                    cmd.append(str(binary))
                    # nanvixd packs args and env vars into a separate
                    # positional argument after the binary path:
                    #   nanvixd ... -- <binary> "<args>;<env vars>"
                    # For env-only, use ";KEY=VALUE".
                    if suite == "misc-c":
                        cmd.append(";NANVIX_TEST=1")
                    log.info(f"$ {' '.join(cmd)}")
                    subprocess.run(
                        cmd,
                        cwd=repo_root(),
                        stdin=subprocess.DEVNULL,
                        text=True,
                        check=True,
                        timeout=120,
                    )
                print(f"OK   {suite}")
            except subprocess.CalledProcessError as exc:
                print(f"FAIL {suite} (exit code {exc.returncode})")
                failed.append(suite)
            except subprocess.TimeoutExpired as exc:
                print(f"FAIL {suite} (timed out after {exc.timeout}s)")
                failed.append(suite)
            except SystemExit as exc:
                print(f"FAIL {suite} (SystemExit code={exc.code})")
                failed.append(suite)

        if failed:
            sys.exit(f"{len(failed)} test suite(s) failed: {' '.join(failed)}")
        print("\t\t*** POSIX tests PASSED ***")

    # ---- Windows: binary download ----------------------------------------

    def _download_windows_binaries(self) -> None:
        """Download native Windows host binaries from the Nanvix release.

        On Windows, tests run natively using nanvixd.exe. These binaries
        are distributed as part of the Windows-specific release assets.
        """
        from nanvix_zutil import CFG_GH_TOKEN

        sysroot_path = Path(self.config.get(CFG_SYSROOT) or "")
        bin_dir = sysroot_path / "bin"

        # Skip if already present.
        required = WINDOWS_HOST_BINARIES
        if all((bin_dir / b).is_file() for b in required):
            log.info("Windows host binaries already present in sysroot")
            return

        # Resolve the release tag.
        tag = str(self.manifest.sysroot_ref.value)
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

        if not asset_url or not asset_name:
            log.warning(
                f"No Windows asset matching '{asset_prefix}*.zip' in release {tag}"
            )
            return

        # Download to cache.
        cache_dir = nanvix_root() / "cache"
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

        # Verify all required binaries exist.
        missing = [b for b in required if not (bin_dir / b).is_file()]
        if missing:
            log.fatal(
                f"Required Windows binaries missing after download: "
                f"{', '.join(missing)}",
                code=EXIT_MISSING_DEP,
                hint="Check the Nanvix release page for Windows assets.",
            )

        log.success("Windows host binaries installed")


if __name__ == "__main__":
    PosixTestsBuild.main()
