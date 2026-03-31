# Hub Deploy

Canonical `cybeer-hub` repo path:

```bash
/home/cybeer/beer-tap-system
```

Do not run the backend stack from `/opt/beer-tap-system`.

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
