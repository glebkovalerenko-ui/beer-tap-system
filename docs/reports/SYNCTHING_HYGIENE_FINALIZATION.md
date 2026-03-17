# Syncthing Hygiene Finalization

## 1. Problem

After Syncthing restoration, two hygiene issues remained:

- runtime artifact `.venv-display-agent` still existed inside the synced repo path
- Git working trees on Pi and hub showed false churn for `tap-display-client/src/App.svelte`

The scope of this pass was limited to removing runtime sync noise, stabilizing line-ending behavior, and confirming a fully clean Syncthing state without changing product logic.

## 2. What was done

### `.venv-display-agent`

- Kept `.venv-display-agent` excluded in `.stignore`
- Deployed the updated `.stignore` locally to Pi and hub
- Removed `.venv-display-agent` from the repo path on:
  - Windows
  - Pi
  - hub
- Rescanned all three Syncthing nodes

### Git line-ending hygiene

- Expanded `.gitattributes` to stabilize text checkout behavior:
  - `* text=auto`
  - `*.sh text eol=lf`
  - `*.py text eol=lf`
  - `*.js text eol=lf`
  - `*.svelte text eol=lf`
  - `.stignore text eol=lf`
- Set repo-local Git config:
  - Windows: `core.autocrlf=false`, `core.filemode=false`
  - Pi: `core.autocrlf=false`, `core.filemode=false`
  - hub: `core.autocrlf=false`, `core.filemode=false`
- Normalized `tap-display-client/src/App.svelte` to LF and refreshed the Git index view

## 3. Final Syncthing metrics

### Windows

- `db/status`: `state=idle`, `errors=0`, `pullErrors=0`, `needTotalItems=0`, `needDeletes=0`
- `db/need`: empty
- `db/remoteneed` for Pi: empty
- `db/remoteneed` for hub: empty
- completion:
  - Pi: `completion=100`, `needItems=0`
  - hub: `completion=100`, `needItems=0`

### Pi

- `db/status`: `state=idle`, `errors=0`, `pullErrors=0`, `needTotalItems=0`, `receiveOnlyTotalItems=0`
- `db/localchanged`: empty

### hub

- `db/status`: `state=idle`, `errors=0`, `pullErrors=0`, `needTotalItems=0`, `receiveOnlyTotalItems=0`
- `db/localchanged`: empty

### Runtime artifact confirmation

- `.venv-display-agent` is absent from the repo path on Windows, Pi, and hub
- `.venv-display-agent` is absent from live Syncthing `db/need` and `db/remoteneed`

## 4. Git hygiene result

### Resolved

- `tap-display-client/src/App.svelte` is no longer reported as modified on Pi
- `tap-display-client/src/App.svelte` is no longer reported as modified on hub
- `tap-display-client/src/App.svelte` is no longer reported as modified on Windows
- `git ls-files --eol` now reports `w/lf attr/text eol=lf` for `tap-display-client/src/App.svelte` on all three nodes

### Important boundary

The working trees are now clean with respect to the false product-file churn that was the target of this hygiene pass.

The remaining dirty entries are intentional uncommitted repo artifacts introduced by the recovery/hygiene work itself:

- `.gitattributes`
- `.stignore`
- `docs/reports/SYNCTHING_RESTORATION_RCA_AND_RECOVERY.md`
- `docs/reports/SYNCTHING_HYGIENE_FINALIZATION.md`

Those entries are not Syncthing drift. They are normal Git dirtiness from local uncommitted repo changes, and they cannot become clean on Pi/hub without a separate Git commit workflow, which was out of scope here.

## 5. Real sync sanity

- Created `backend/_syncthing_hygiene_probe.txt` on Windows and confirmed it appeared on Pi and hub
- Deleted the probe on Windows and confirmed it disappeared on Pi and hub
- Created a local-only probe on Pi and confirmed it did not appear on Windows or hub

## 6. Final verdict

`SYNCTHING CLEAN AND STABLE`
