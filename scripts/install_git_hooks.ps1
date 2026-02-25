$ErrorActionPreference = 'Stop'

$repoRoot = (& git rev-parse --show-toplevel) 2>$null
if (-not $repoRoot) {
  $repoRoot = (Get-Location).Path
}

$hookPath = Join-Path $repoRoot '.git/hooks/pre-commit'
$hookContent = @'
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if command -v python >/dev/null 2>&1; then
  python "$REPO_ROOT/scripts/encoding_guard.py"
else
  echo "[pre-commit] warning: python not found; skipping scripts/encoding_guard.py"
fi
'@

Set-Content -Path $hookPath -Value $hookContent -Encoding UTF8
Write-Host "Installed pre-commit hook: $hookPath"
