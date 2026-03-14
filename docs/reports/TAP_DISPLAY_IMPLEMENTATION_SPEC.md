# TAP_DISPLAY_IMPLEMENTATION_SPEC

Date: 2026-03-14  
Status: implementation foundation started in repository

## 1. Executive summary

Recommended MVP architecture:

- backend-authoritative display snapshot per `tap_id`;
- controller-authoritative runtime JSON on Raspberry Pi;
- local Python `tap-display-agent` serving `localhost` APIs and static display bundle;
- separate `tap-display-client` Svelte app rendered in Chromium kiosk mode.

Current implementation foundation in repo:

- backend snapshot/media/config APIs;
- controller shared device config + runtime snapshot publisher;
- local display agent with polling/cache/runtime bridge;
- display client bundle with MVP state renderer;
- Raspberry Pi deployment artifacts documented below.

## 2. Decisions frozen for MVP

- Browser does not call backend directly.
- Backend content changes are picked up by conditional polling with `ETag`, not SSE/WebSocket.
- Runtime state source of truth during pour is controller-local JSON at `/run/beer-tap/display-runtime.json`.
- Shared device config is `Pi-local env` style config at `/etc/beer-tap/device.env`.
- Layout is landscape-only for MVP, tuned for `1024x600` and safe at `800x480`.
- Content precedence is resolved server-side: `tap override > beverage default > system fallback`.
- Guest UI does not show `remaining keg volume` or `keg connected at` in MVP.

## 3. Runtime and content data flow

1. Admin edits beverage or tap display content in backend-facing admin surfaces.
2. Backend stores structured content and media metadata.
3. `GET /api/display/taps/{tap_id}/snapshot` returns the effective content snapshot with `content_version`.
4. `tap-display-agent` polls backend every 5 seconds with `If-None-Match`.
5. On `200`, the agent updates cached snapshot and downloads referenced assets.
6. Controller publishes runtime snapshot when state changes and during pour progress.
7. Browser polls:
   - `/local/display/bootstrap`
   - `/local/display/runtime`
8. UI precedence:
   - active local runtime
   - local blocked/service runtime
   - backend availability/service flags
   - branded idle content

## 4. Backend model and API spec

Implemented data model:

- `beverages` extended with:
  - `description_short`
  - `ibu`
  - `display_brand_name`
  - `accent_color`
  - `background_asset_id`
  - `logo_asset_id`
  - `text_theme`
  - `price_display_mode_default`
  - `updated_at`
- `media_assets`
- `tap_display_configs`

Implemented endpoints:

- `GET /api/display/taps/{tap_id}/snapshot`
- `POST /api/media-assets`
- `GET /api/media-assets`
- `GET /api/media-assets/{asset_id}/content`
- `PUT /api/beverages/{beverage_id}`
- `GET /api/taps/{tap_id}/display-config`
- `PUT /api/taps/{tap_id}/display-config`

Snapshot contract sections:

- `tap`
- `service_flags`
- `assignment`
- `presentation`
- `pricing`
- `theme`
- `copy`
- `content_version`
- `generated_at`

## 5. Content ownership model

`beverage` owns reusable guest-facing presentation:

- name
- brand/brewery
- style
- ABV
- optional IBU
- short description
- background
- logo
- accent color
- default price display mode

`tap` owns physical screen behavior:

- enabled flag
- idle instruction
- fallback title/subtitle
- maintenance title/subtitle
- tap-specific accent override
- tap-specific background override
- tap-specific price mode override

Deferred:

- per-keg overrides
- guest-facing keg stats
- device registry and scoped tokens

## 6. Display UX state spec

Implemented MVP state groups in client:

- `idle`
- `authorized`
- `denied`
- `pouring`
- `finished`
- `service`

Primary hierarchy:

- Idle:
  - large: beverage name
  - secondary: display price
  - small: style/ABV, brand, short description
  - CTA: `Приложите карту`
- Authorized:
  - large: `Откройте кран`
  - secondary: first name / readiness message
  - small: balance, price chip
- Denied:
  - large: deny headline
  - secondary: one next action
  - small: `Заберите карту`
- Pouring:
  - large: live ml
  - secondary: live rubles
  - small: projected remaining balance
- Finished:
  - large: final ml
  - secondary: final rubles
  - small: projected remaining balance + `Заберите карту`
- Service:
  - large: guest-safe status
  - secondary: next step
  - small: operator code

## 7. Visual system recommendations

- One landscape layout with branded and service variants.
- Accent-driven branded background with dark overlay.
- Service states suppress beverage branding.
- Large numeric hierarchy for ml and rubles.
- Progress visualization uses a single SVG ring.
- Safe text lengths:
  - beverage title: 2 lines
  - description: 2 lines
  - service headline: 2 lines

## 8. Degraded / no-connection behavior

- Agent marks backend link as lost if:
  - `last_success_at` is older than 15 seconds, or
  - there are 2 consecutive polling failures.
- No active runtime + backend lost:
  - UI shows explicit `Нет связи с системой`.
- Active `authorized` / `pouring` / `finished` runtime + backend lost:
  - UI continues to show local session
  - warning pill is shown
  - `finished` uses `Ожидается синхронизация`
- Missing runtime file:
  - browser falls back to idle or blocked neutral state depending on context.

## 9. MVP scope

Included in current implementation foundation:

- backend display snapshot layer
- media upload/list/content serving
- tap display config CRUD
- beverage display fields
- controller runtime snapshot publisher
- shared Pi config contract
- FastAPI display agent
- cached asset + snapshot bridge
- localhost-only browser contract
- Svelte display client bundle

Pilot hardening still to finish:

- systemd packaging on device
- Chromium kiosk validation on Pi
- operator-facing admin edit flows

## 10. Deferred scope

- SSE/WebSocket backend push
- browser-scoped backend auth
- per-keg content overrides
- guest touch controls
- multi-language runtime localization
- fleet diagnostics and screenshot capture
- operator/debug overlay as default mode

## 11. Risks and trade-offs

- Split authority is intentional:
  - backend for content
  - controller for live runtime
- Polling chosen over event infra:
  - simpler MVP
  - easy `ETag` invalidation
- Cached content can become stale:
  - mitigated by explicit no-connection state
- Raspberry Pi kiosk behavior varies by OS/browser build:
  - mitigated by separate services and restart policies

## 12. Phased execution plan

### Phase 0. Contracts freeze

- finalize runtime JSON contract
- finalize snapshot response contract
- finalize state precedence matrix

### Phase 1. Foundation

- shared Pi device config
- controller runtime publisher
- display agent config contract

### Phase 2. Backend display model

- migrations
- snapshot resolver
- media storage
- `ETag` support

### Phase 3. Admin content management

- beverage display fields UI
- tap display settings UI
- media picker/upload UI

### Phase 4. Display agent

- polling
- cache
- localhost APIs
- local asset serving

### Phase 5. Display client MVP

- state renderer
- brand/service variants
- numeric and progress animations

### Phase 6. Kiosk integration

- systemd units
- Chromium kiosk
- restart behavior

### Phase 7. Pilot QA

- monitor validation
- 7-inch validation
- readability and degraded-state validation

## 13. Task breakdown

- `[Backend]` Add display fields to beverage model and schema.
- `[Backend]` Add `media_assets`.
- `[Backend]` Add `tap_display_configs`.
- `[Backend]` Add display snapshot resolver and API.
- `[Backend]` Add `ETag` and conditional polling support.
- `[Controller]` Add shared env config loading.
- `[Controller]` Add display runtime publisher.
- `[Controller]` Add runtime publish points for idle/authorized/denied/pouring/finished/blocked.
- `[Agent]` Add backend poller, cache and localhost APIs.
- `[Agent]` Add local asset serving.
- `[Frontend]` Add Svelte kiosk client.
- `[Frontend]` Add degraded/no-connection warning handling.
- `[Infra]` Add systemd and kiosk startup artifacts.

## 14. Recommended implementation order

1. Freeze contracts.
2. Stabilize shared Pi config and runtime publisher.
3. Land backend snapshot layer.
4. Land display agent bridge.
5. Land display client.
6. Add admin edit flows.
7. Add kiosk boot integration.
8. Run pilot QA.

## 15. Final recommendation

Use the hybrid architecture already started in this repository:

- backend drives content and tap assignment changes;
- controller drives live guest session truth;
- display agent isolates credentials and caching from the browser;
- display client renders a small, state-driven interface optimized for the 7-inch tap screen.

This remains the strongest MVP path because it preserves local correctness during pour, keeps content centrally manageable, and exposes loss of connectivity honestly instead of hiding it.
