# Encoding Guard

## Why

The project had mojibake UI text and hidden Unicode control characters. This check blocks those issues before merge.

`scripts/encoding_guard.py` scans for:
- files that are not valid UTF-8,
- mojibake markers (`РІР‚`, `Р Сџ`, `Р С’`, `Гѓ`, `Г‚`, `пїЅ`, etc.),
- Unicode bidi/control characters (`Cf` + common bidi controls).

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

## If issues are found

- Re-save files as UTF-8 (no BOM).
- Remove hidden bidi/control characters.
- Replace garbled strings with correct text.
- Re-run `python scripts/encoding_guard.py`.
