#!/usr/bin/env bash
# Bootstraps a Pymium checkout on Linux/macOS.
# Mirrors bootstrap.ps1: depot_tools, generate .gclient for the fork, fetch.
# The fork already contains the Chromium-path Pymium files, so no patch queue
# is applied.
set -euo pipefail

FORK_URL="${PYMIUM_FORK_URL:-https://github.com/Simonko-912/pymium.git}"
REVISION="${PYMIUM_REVISION:-}"
NO_FETCH="${PYMIUM_NO_FETCH:-0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/src"
DEPOT="$ROOT/depot_tools"

for t in git python3; do command -v "$t" >/dev/null || { echo "missing $t" >&2; exit 1; }; done

# 1) depot_tools
[ -d "$DEPOT" ] || git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git "$DEPOT"
export PATH="$DEPOT:$PATH"
export DEPOT_TOOLS_WIN_TOOLCHAIN="${DEPOT_TOOLS_WIN_TOOLCHAIN:-}"

# 2) Chromium checkout (single-repo: the fork IS chromium/src + Pymium files)
if [ "$NO_FETCH" != "1" ]; then
  cat > "$ROOT/.gclient" <<EOF
solutions = [
  { "name"        : "src",
    "url"         : "$FORK_URL",
    "deps_file"   : "DEPS",
    "managed"     : False,
    "custom_deps" : {},
  },
]
EOF
  if [ ! -d "$SRC/.git" ]; then
    echo "==> Fetching Chromium (multi-GB, may take a long time)"
    "$DEPOT/fetch" --nohooks --no-history chromium
  fi
  [ -n "$REVISION" ] && git -C "$SRC" checkout "$REVISION"
  "$DEPOT/gclient" sync --with_branch_heads --with_tags
fi

# 3) Build config
mkdir -p "$SRC/out/pymium"
cp "$ROOT/conf/gn_args.txt" "$SRC/out/pymium/args.gn"

echo "Next: cd $SRC && gn gen out/pymium && autoninja -C out/pymium chrome"