# Encoding Guard

## Why

The project had mojibake UI text and hidden Unicode control characters. This check blocks those issues before merge.

`scripts/encoding_guard.py` scans for:
- files that are not valid UTF-8,
- mojibake signatures (broken UTF-8/cp1251 mixes, replacement chars, corrupted Cyrillic pairs),
- Unicode bidi/control characters (`Cf` + common bidi controls).
- explicit bad markers: `\\u0432\\u0402`, `\\u0420\\u00A4`, `\\u0420\\u0452`, `\\u0420\\u045F`, `\\u00D0`, `\\u00D1`, `\\uFFFD`.

## Install Git hooks

```bash
bash scripts/install_git_hooks.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_git_hooks.ps1
```

## Run manually

```bash
python scripts/encoding_guard.py
```

Mode flags:

```bash
# staged files only (used by pre-commit)
python scripts/encoding_guard.py --staged

# CI pull_request diff
python scripts/encoding_guard.py --diff-base <base_sha>

# full repository scan
python scripts/encoding_guard.py --all
```

CI integration:
- `.github/workflows/quality.yml` runs encoding guard on every PR and on push to `main/master`.

## If issues are found

- Re-save files as UTF-8 (no BOM).
- Remove hidden bidi/control characters.
- Replace garbled strings with correct text.
- Re-run `python scripts/encoding_guard.py`.
