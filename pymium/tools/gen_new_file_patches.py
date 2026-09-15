#!/usr/bin/env python3
"""Regenerate the NEW-file patches (0002..0004) as reference copies.

In the single-repo layout the Chromium-path files (build/config/pymium.gni,
content/renderer/pymium_embed.*, third_party/cpython/*, the blink python
runtime) are committed directly to the fork and ARE the source of truth. The
patches under pymium/patches/ are regenerated from them purely as reference
documentation — they are never applied, because the files already live in the
tree.

Usage: python pymium/tools/gen_new_file_patches.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # pymium/
FORK_ROOT = ROOT.parent                         # repo root = chromium/src layout
PATCHES = ROOT / "patches"

# patch filename -> fork-root-relative globs (source of truth)
SPLIT = [
    (
        "0002-blink-python-runtime.patch",
        [
            "third_party/blink/renderer/bindings/core/python/*.h",
            "third_party/blink/renderer/bindings/core/python/*.cc",
        ],
    ),
    (
        "0003-cpython-and-gn.patch",
        [
            "build/config/pymium.gni",
            "third_party/cpython/*",
            "third_party/blink/renderer/bindings/core/python/BUILD.gn",
        ],
    ),
    (
        "0004-content-renderer-init.patch",
        [
            "content/renderer/pymium_embed.*",
        ],
    ),
]


def diff_new_file(repo_rel: str) -> str:
    target = FORK_ROOT / repo_rel
    if not target.is_file():
        raise FileNotFoundError(repo_rel)
    proc = subprocess.run(
        ["git", "diff", "--no-index", "--", "/dev/null", repo_rel],
        cwd=str(FORK_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout


def main() -> int:
    for patch_name, globs in SPLIT:
        body = []
        for glob in globs:
            matches = sorted(FORK_ROOT.glob(glob))
            if not matches:
                print(f"warning: no files for {glob}", file=sys.stderr)
            for match in matches:
                rel = match.relative_to(FORK_ROOT).as_posix()
                body.append(diff_new_file(rel))
        (PATCHES / patch_name).write_text(
            "\n".join(body) + "\n", encoding="utf-8"
        )
        print(f"wrote {patch_name} ({sum(len(b) for b in body)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())