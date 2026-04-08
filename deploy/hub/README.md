# Hub Deploy

Canonical `cybeer-hub` repo path:

```bash
/home/cybeer/beer-tap-system
```

Do not run the backend stack from `/opt/beer-tap-system`.

Before enabling the hub stack, prepare `/home/cybeer/beer-tap-system/.env` from `.env.example` and set at least:

- `SECRET_KEY`
- `INTERNAL_API_KEY` and matching `INTERNAL_TOKEN` if the Pi controller still reads the legacy name
- `DISPLAY_API_KEY` when the tap-display path is deployed
- `BOOTSTRAP_AUTH_PASSWORD` if `ENABLE_BOOTSTRAP_AUTH=true`
- `CORS_ALLOWED_ORIGINS` for the actual admin-app web origin(s)

See `SECURITY_BASELINE.md` in the repo root for the controlled-pilot baseline.

## Units

- `beer-tap-system.service`: boot-time Docker Compose stack rooted at `/home/cybeer/beer-tap-system`
- `beer-tap-sync-reconcile.timer`: periodically checks Syncthing folder `beer-tap-system-dev`
- `beer-tap-sync-reconcile.service`: applies a fresh backend snapshot only when Syncthing is idle and clean

## Install

```bash
sudo install -m 0755 deploy/hub/beer-tap-sync-reconcile.sh /usr/local/bin/beer-tap-sync-reconcile.sh
sudo install -m 0644 deploy/hub/beer-tap-system.service /etc/systemd/system/beer-tap-system.service
sudo install -m 0644 deploy/hub/beer-tap-sync-reconcile.service /etc/systemd/system/beer-tap-sync-reconcile.service
sudo install -m 0644 deploy/hub/beer-tap-sync-reconcile.timer /etc/systemd/system/beer-tap-sync-reconcile.timer
sudo systemctl daemon-reload
sudo systemctl enable --now beer-tap-system.service beer-tap-sync-reconcile.timer
```
