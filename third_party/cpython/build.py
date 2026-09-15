#!/usr/bin/env python3
"""Standalone build helper for the Pymium CPython embed.

Normally invoked by `bootstrap.{ps1,sh}` with `--mode interpret,build,verify`
from the chromium/src checkout after the patch queue has been applied. Kept as a
boundary reference rather than wiring into //third_party/cpython/BUILD.gn so a
plain `gn gen` never needs a Python to produce Python (ARCHITECTURE.md section
4.1 rationale 2).

The real fork replaces RUNMODE with the DEPS'd tarball path; the scaffold only
documents the shape.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def interpret(workdir: Path) -> None:
    ver = Path(workdir) / "third_party" / "cpython" / "version.gni"
    if not ver.exists():
        print(f"note: no {ver} yet; fork must pin pymium_cpython_version")
        # With no pinned version the scaffold falls back to the system Python
        # at build time only, so the demo/ scripts can still be authored.
        subprocess.run([sys.executable, "--version"], check=False)


def build(workdir: Path) -> None:
    print(f"building vendored cpython under {workdir / 'third_party' / 'cpython'}")
    print("placeholder: real fork runs configure/make or uses the GN static "
          "source_set in BUILD.gn.")


def verify(workdir: Path) -> None:
    print("verify: Py_InitializeEx smoke test would run here")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, default=Path.cwd())
    ap.add_argument("--mode", default="interpret",
                    choices=["interpret", "build", "verify"])
    args = ap.parse_args(argv)
    return {
        "interpret": lambda: interpret(args.workdir),
        "build": lambda: build(args.workdir),
        "verify": lambda: verify(args.workdir),
    }[args.mode]()


if __name__ == "__main__":
    sys.exit(main())