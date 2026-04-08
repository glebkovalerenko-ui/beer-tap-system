# Security Baseline

- Last reviewed against repository state: 2026-04-08
- Scope: minimal auth/secrets hardening for controlled pilot

## What This Is

This is not a production security manual and not an enterprise IAM design.

It is the minimum auth/secrets baseline that lets this repository move from obvious dev/demo defaults to a controlled-pilot posture:

- no silent fallback `SECRET_KEY`
- no silent demo internal token fallback
- no prefilled `fake_password` UX
- no wildcard-only CORS contract
- no unauthenticated controller sync path

## Required Secrets And Tokens

Hub/backend:

- `SECRET_KEY`
  Must be set to a non-placeholder value.
- `INTERNAL_API_KEY`
  Required for controller/internal token auth on backend routes.
- `INTERNAL_TOKEN`
  Keep equal to `INTERNAL_API_KEY` only for legacy Pi compatibility if the controller still reads the legacy name.
- `DISPLAY_API_KEY`
  Required on the backend side when the tap-display path is deployed.
- `BOOTSTRAP_AUTH_PASSWORD`
  Required only when `ENABLE_BOOTSTRAP_AUTH=true`.
- `CORS_ALLOWED_ORIGINS`
  Must list the actual admin-app web origin(s) for pilot/browser use.

Pi/controller:

- `INTERNAL_TOKEN`
  Must match hub `INTERNAL_API_KEY` or one entry from `INTERNAL_API_KEYS`.

Pi/display-agent:

- `DISPLAY_API_KEY`
  Must match backend `DISPLAY_API_KEY` or one entry from `DISPLAY_API_KEYS`.

## What Changed From Dev/Demo Defaults

- `SECRET_KEY` no longer silently falls back to a dev value in normal startup.
- `ALLOW_INSECURE_DEV_SECRET_KEY=true` is now the only explicit escape hatch for local-only insecure startup.
- internal controller auth no longer silently accepts `demo-secret-key`.
- `ALLOW_LEGACY_DEMO_INTERNAL_TOKEN=true` is now explicit opt-in instead of default behavior.
- `/api/sync/pours` now requires internal auth.
- `/api/controllers/register` now requires internal auth.
- `/api/system/states/all` is no longer an open debug endpoint.
- bootstrap operator login is now explicit:
  `ENABLE_BOOTSTRAP_AUTH=true` plus `BOOTSTRAP_AUTH_PASSWORD`.
- admin-app login no longer ships with a prefilled `fake_password`.
- backend CORS is controlled by `CORS_ALLOWED_ORIGINS` and defaults to localhost dev origins instead of `*`.

## Allowed Pilot-Mode Behavior

- Bootstrap local operator accounts are still allowed for controlled pilot and local development.
- Those accounts remain config-backed bootstrap users, not a full user-management system.
- Shared bootstrap password across `admin`, `shift_lead`, and `operator` is still acceptable for a tightly controlled pilot if it is explicitly configured and kept off demo defaults.
- Internal/display auth is still token-based and manually coordinated between hub and Pi device env files.

## Explicitly Not Production-Grade

- No external IdP, SSO, OAuth provider, or lifecycle-managed user directory.
- No per-user password reset, lockout, recovery, or audited credential rotation workflow.
- No formal secret manager integration.
- No mTLS or device identity attestation between hub and Pi devices.
- No comprehensive network hardening or security monitoring story.

## Verification Checklist

- Set `SECRET_KEY`, `INTERNAL_API_KEY`, `INTERNAL_TOKEN`, and `BOOTSTRAP_AUTH_PASSWORD` in hub `.env`.
- Set `DISPLAY_API_KEY` on hub and Pi if the display path is deployed.
- Set `INTERNAL_TOKEN` and `DISPLAY_API_KEY` in `/etc/beer-tap/device.env` on the Pi.
- Confirm backend starts without `ALLOW_INSECURE_DEV_SECRET_KEY=true`.
- Confirm `POST /api/token` works only when `ENABLE_BOOTSTRAP_AUTH=true` and `BOOTSTRAP_AUTH_PASSWORD` is configured.
- Confirm controller `authorize-pour`, `flow-events`, and `sync/pours` work with `X-Internal-Token`.
- Confirm display snapshot/media requests work with `X-Display-Token`.
- Confirm browser/admin-app origin is included in `CORS_ALLOWED_ORIGINS`.
- Confirm `ALLOW_LEGACY_DEMO_INTERNAL_TOKEN` is left `false` in pilot.
