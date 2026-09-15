<#
.SYNOPSIS
Bootstraps a Pymium checkout: installs depot_tools, generates a .gclient for
the fork, fetches the Chromium sources and writes an args.gn.

The single-repo layout means the Chromium-path files (build/config/pymium.gni,
content/renderer/pymium_embed.*, third_party/**) are already committed to the
fork, so no patch queue is applied.

.PARAMETER ForkUrl
Git URL of the Pymium fork of chromium/src. Defaults to $env:PYMIUM_FORK_URL
or your fork at github.com/Simonko-912.
.PARAMETER Revision
Optional pinned chromium/src revision to check out before writing args.gn.
.PARAMETER NoFetch
Skip the expensive `fetch` step and sync an existing src/ checkout instead.
#>
param(
  [string]$ForkUrl = $env:PYMIUM_FORK_URL,
  [string]$Revision = "",
  [switch]$NoFetch
)

$ErrorActionPreference = "Stop"

if (-not $ForkUrl) {
  $ForkUrl = "https://github.com/Simonko-912/pymium.git"
  Write-Host "WARN: PYMIUM_FORK_URL not set, using your fork at $ForkUrl"
}

function Require-Tool {
  param([string]$Name, [string]$Probe)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required tool: $Name ($Probe)"
  }
}

Require-Tool "git"   "https://git-scm.com/downloads"
Require-Tool "python" "python3 (ensure it is on PATH, not the MS Store alias)"

$root = $PSScriptRoot
$src  = Join-Path $root "src"

# 1) depot_tools -----------------------------------------------------------
$depot = Join-Path $root "depot_tools"
if (-not (Test-Path $depot)) {
  Write-Host "==> Cloning depot_tools"
  git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git $depot
}
$env:PATH = "$depot;$env:PATH"
if (-not $env:DEPOT_TOOLS_WIN_TOOLCHAIN) {
  $env:DEPOT_TOOLS_WIN_TOOLCHAIN = "0"  # use locally installed VS
}

if (-not $NoFetch) {
  # 2) Chromium checkout ----------------------------------------------------
  New-Item -ItemType Directory -Force -Path $root | Out-Null
  $gclient = @"
solutions = [
  { "name"        : "src",
    "url"         : "$ForkUrl",
    "deps_file"   : "DEPS",
    "managed"     : False,
    "custom_deps" : {},
  },
]
"@
  Set-Content -Path (Join-Path $root ".gclient") -Value $gclient -Encoding ascii

  if (-not (Test-Path (Join-Path $src ".git"))) {
    Write-Host "==> Fetching Chromium (this downloads many GB and takes a while)"
    & "$depot\fetch" --nohooks --no-history chromium
    if ($LASTEXITCODE -ne 0) { throw "fetch failed" }
  }
  if ($Revision) {
    Write-Host "==> Checking out pinned revision $Revision"
    & git -C $src checkout $Revision
  }
  Write-Host "==> Running hooks"
  & "$depot\gclient" sync --with_branch_heads --with_tags
  if ($LASTEXITCODE -ne 0) { throw "gclient sync failed" }
}

# 3) args.gn -----------------------------------------------------------------
$out = Join-Path $src "out\pymium"
New-Item -ItemType Directory -Force -Path $out | Out-Null
Copy-Item (Join-Path $root "conf\gn_args.txt") (Join-Path $out "args.gn")

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Next:"
Write-Host "  cd $src"
Write-Host "  gn gen out/pymium"
Write-Host "  autoninja -C out/pymium chrome"
Write-Host ""
Write-Host "Note: the Pymium source files are already committed to the fork --"
Write-Host "no patch queue needs applying."