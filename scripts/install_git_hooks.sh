#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOK_PATH="$REPO_ROOT/.git/hooks/pre-commit"

cat > "$HOOK_PATH" <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if command -v python >/dev/null 2>&1; then
  python "$REPO_ROOT/scripts/encoding_guard.py" --staged
else
  echo "[pre-commit] warning: python not found; skipping scripts/encoding_guard.py"
fi
HOOK

chmod +x "$HOOK_PATH"
echo "Installed pre-commit hook: $HOOK_PATH"
