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

from nanvix_zutil import CFG_SYSROOT, CFG_TOOLCHAIN, EXIT_MISSING_DEP, ZScript, log

# Makefile variable names (build-system-specific).
_MAKE_VAR_SYSROOT = "NANVIX_SYSROOT"
_MAKE_VAR_TOOLCHAIN = "NANVIX_TOOLCHAIN"
_MAKE_VAR_PLATFORM = "PLATFORM"
_MAKE_VAR_PROCESS_MODE = "PROCESS_MODE"
_MAKE_VAR_MEMORY_SIZE = "MEMORY_SIZE"


class PosixTestsBuild(ZScript):
    """Build script for nanvix/posix-tests."""

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

    def setup(self) -> None:
        """Download the Nanvix sysroot."""
        super().setup()

    def build(self) -> None:
        """Cross-compile all POSIX test suites for Nanvix."""
        self.run(*self._make_args("all"), cwd=self.repo_root)

    def test(self) -> None:
        """Run the POSIX test suites.

        Without targets, runs the full suite (smoke + integration + functional).
        With targets (e.g. ``./z test -- test-smoke test-integration``), passes
        them directly to the Makefile.
        """
        targets = self.targets if self.targets else ["test"]
        self.run(*self._make_args(*targets), cwd=self.repo_root)

    def release(self) -> None:
        """Package the posix-tests release tarball and verify it."""
        self.run(*self._make_args("package"), cwd=self.repo_root)
        self.run(*self._make_args("verify-package"), cwd=self.repo_root)

    def clean(self) -> None:
        """Remove build artifacts."""
        self.run("make", "-C", "src", "clean", cwd=self.repo_root)


if __name__ == "__main__":
    PosixTestsBuild.main()
