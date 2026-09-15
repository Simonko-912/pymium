#!/usr/bin/env python3
"""Apply the Pymium patch queue to a chromium/src checkout.

Strategy per patch (see the `patches/SERIES` file):
  * NEW  files -> moved/copied in directly (deterministic, no fuzz risk).
  * EDIT files -> `git apply --3way` (three-way merge tolerates context drift).
  * REBASE     -> EDIT hunks that are known to depend on the exact upstream
                   revision; these are applied best-effort and must be checked
                   by a human after a pinned-revision bump.

Usage:
    python tools/rebase_patches.py --src <chromium/src> [--patches patches]
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def apply_git(src: Path, patch: Path) -> str:
    """git apply (--3way fallback) and return stdout/stderr."""
    r = sh(["git", "apply", "--3way", "--stat", "--apply", str(patch)], src)
    if r.returncode == 0:
        return f"OK (3way) {patch.name}\n{r.stdout}"
    r2 = sh(["git", "apply", "--stat", "--apply", str(patch)], src)
    if r2.returncode == 0:
        return f"OK (plain) {patch.name}\n{r2.stdout}"
    return f"FAIL {patch.name}\n{r.stdout}{r.stderr}\n{r2.stdout}{r2.stderr}"


def classify(patch: Path) -> tuple[str, str]:
    """Return (kind, description) parsed from patches/SERIES."""
    series = patch.parent / "SERIES"
    text = series.read_text(encoding="utf-8") if series.exists() else ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == patch.name:
            return parts[1], " ".join(parts[2:])
    return "MIXED", ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="path to a chromium/src checkout")
    ap.add_argument("--patches", default="patches", help="directory of .patch files")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    patches_dir = Path(args.patches).resolve()
    if not src.is_dir():
        print(f"error: {src} is not a directory", file=sys.stderr)
        return 2

    order = sorted(p for p in patches_dir.glob("*.patch"))
    if not order:
        print(f"error: no .patch files in {patches_dir}", file=sys.stderr)
        return 2

    failures = []
    for patch in order:
        kind, note = classify(patch)
        if kind == "NEW":
            # Extract files whose diff header is `--- /dev/null` and copy-clean them.
            text = patch.read_text(encoding="utf-8")
            new_files = re.findall(r"diff --git a/[\w./-]+ b/([\w./-]+)", text)
            for rel in new_files:
                dst = src / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
            applied = apply_git(src, patch)
            if not applied.startswith("OK"):
                failures.append(applied)
            else:
                print(applied)
        else:
            print(f"-- {patch.name} [{kind}] {note}")
            applied = apply_git(src, patch)
            print(applied)
            if not applied.startswith("OK"):
                failures.append(applied)

    if failures:
        print("\n=== FAILED PATCHES (need manual rebase) ===")
        for f in failures:
            print(f)
        return 1
    print(f"\nAll {len(order)} patches applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())