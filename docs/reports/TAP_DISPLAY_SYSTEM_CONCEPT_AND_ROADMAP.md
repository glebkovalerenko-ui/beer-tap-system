# TAP_DISPLAY_SYSTEM_CONCEPT_AND_ROADMAP

Date: 2026-03-14
Status: design package, repository analysis complete, no implementation in this step

## 1. Goal and product purpose

Tap Display System is a guest-facing and operator-useful screen mounted on each tap/controller pair.

Its purpose is to:

- reduce guest hesitation at the tap;
- make the next action obvious at every step;
- show trustworthy live pour feedback during the session;
- present the beverage in a branded but reusable way;
- expose service and failure states clearly without needing bartender explanation.

Primary product outcomes:

- faster first-time self-pour onboarding;
- fewer accidental or confused interactions;
- better perceived product quality at the tap;
- lower operator load for routine guidance;
- cleaner communication during unavailable or maintenance states.

Non-goals for the first version:

- no full operator workstation on the tap display;
- no manual editing on the display itself;
- no separate hand-crafted page per tap;
- no attempt to turn the screen into a full POS, loyalty, or campaign platform.

## 2. Fit with current repository

### Current repository facts that matter

The current repository already contains most of the operational backbone required for a display subsystem:

- Backend is visit-centric and backend-authoritative for operational state.
- `tap -> keg -> beverage` is already the core inventory/content chain.
- `visit.active_tap_id` is already used as the active tap lock during an authorized pour.
- Controller already knows the live local state that a guest display needs most:
  - card present or absent;
  - authorize success or deny reason;
  - current poured volume in ml from the flow sensor;
  - current estimated cost;
  - `processing_sync`, `CARD_MUST_BE_REMOVED`, and emergency-stop situations.
- Backend already returns clamp data on authorize:
  - `min_start_ml`;
  - `max_volume_ml`;
  - `price_per_ml_cents`;
  - `balance_cents`;
  - `allowed_overdraft_cents`;
  - `safety_ml`.
- Backend already exposes useful read models:
  - `/api/taps`;
  - `/api/visits/active/...`;
  - `/api/pours/live-feed`;
  - controller flow-event ingestion.
- Admin App already has a natural operational surface for tap/keg/beverage management in `TapsKegs`.
- Russian labels, money formatting, volume formatting, and state naming patterns already exist in Admin App and controller display helpers.

### Recommended content binding

Display content should not live on a single entity only.

Recommended binding:

- `beverage` is the primary owner of reusable guest-facing product presentation;
- `tap` is the owner of physical-screen behavior, fallback content, and per-location overrides;
- `keg` should not be the primary owner in MVP.

Reasoning:

- Beverage identity is stable across many physical kegs and across tap reassignments.
- Tap identity is stable for the physical screen and is where fallback or maintenance behavior belongs.
- Keg is operationally ephemeral. Making it the primary content owner would create duplication and cleanup problems.

### What can be reused immediately

- Existing `tap -> keg -> beverage` nesting in backend responses.
- Existing authorize/sync state machine.
- Existing `tap_id` controller identity pattern.
- Existing `flow_events` concept for live operational telemetry.
- Existing Admin App `TapsKegs` route for operational content management entry points.
- Existing Russian formatting helpers and UI naming conventions.
- Existing internal-token mechanism for device-originated backend traffic.

### What is missing today

- No display-specific backend model.
- No image/media storage model or upload flow.
- No display-specific aggregated API.
- No read-only scoped device token for a browser-based screen.
- No local display runtime bridge from controller to browser.
- No server-side `controller -> tap` mapping.
- No preview flow for display content in Admin App.
- No Raspberry Pi kiosk boot/autostart setup for a guest-facing screen.
- `TAP_ID` currently exists as a hardcoded constant in `rpi-controller/config.py`, not as a robust device config contract.

### Conclusion

Tap Display System fits the current repository well, but it should be added as a new display layer around existing tap, visit, and controller runtime state. It should not be bolted directly into the current terminal log output and should not be implemented as a pure backend-hosted page with no local state bridge.

## 3. Recommended architecture

### Final architectural choice

Recommended architecture:

- separate lightweight display web client;
- browser in kiosk mode on Raspberry Pi;
- local display agent on the Pi;
- backend-managed content and configuration;
- controller-local runtime state as the source of truth for live session states.

This is intentionally a hybrid:

- kiosk browser is the shell;
- display client is a separate frontend app;
- backend owns reusable content and configuration;
- local Pi runtime owns the real-time interaction state.

### Why this is the best fit

Pure backend-driven remote rendering is too weak for this project because the most important states are local and time-sensitive:

- card detected;
- authorize denied reason;
- real-time volume while pouring;
- session-complete state before sync settles;
- `processing_sync` and local offline tolerance.

The controller already knows these states before the backend can expose them cleanly. The display should therefore consume local runtime state and centralized content separately.

### Recommended component model

#### Backend

Backend should add a display content layer, not a second runtime authority.

Recommended backend responsibilities:

- store beverage presentation content;
- store tap display fallback/override config;
- store media asset metadata and serve images;
- expose aggregated display content snapshot per tap;
- expose content version/hash for cache invalidation;
- keep business rules and official operational state where they already live.

Recommended new backend read model:

- `GET /api/display/taps/{tap_id}/snapshot`

That endpoint should return only what the display needs:

- tap identity and status;
- assigned keg and beverage;
- beverage presentation fields;
- tap-level fallback/override fields;
- relevant global flags like emergency stop;
- content version/hash.

It should not expose broad operational objects or require the display client to stitch together multiple internal endpoints.

#### Display agent on Raspberry Pi

Recommended new local service on Pi:

- `tap-display-agent`

Responsibilities:

- serve the display web client on `localhost`;
- read live runtime state from the controller;
- fetch and cache backend content snapshot and assets;
- keep backend credentials out of the browser;
- expose a minimal local API for the browser.

Recommended local browser-visible endpoints:

- `GET /local/display/bootstrap`
- `GET /local/display/runtime`
- optional `GET /local/display/events` for SSE in later phases

#### Controller runtime state bridge

Recommended MVP approach:

- controller publishes an atomic local JSON snapshot when display-relevant state changes.

Example fields:

- `tap_id`
- `phase`
- `reason_code`
- `card_present`
- `guest_first_name`
- `balance_cents_at_authorize`
- `price_per_ml_cents`
- `max_volume_ml`
- `current_volume_ml`
- `current_cost_cents`
- `projected_remaining_balance_cents`
- `session_short_id`
- `updated_at`

This is deliberately simple and debuggable.

Future upgrade path:

- local SSE stream;
- Unix socket or in-process pub/sub;
- richer telemetry and health reporting.

#### Display web client

Recommended stack:

- Svelte + Vite static bundle.

Why:

- team already uses Svelte;
- screen surface is small and state-driven;
- animations can stay lightweight;
- bundle can be built once and served locally without Node runtime on Pi.

The browser should load a local URL, not a remote backend page:

- `http://127.0.0.1:18181/display`

#### Tap identification

Short term:

- keep `tap_id` as local device configuration shared by controller and display agent.

Recommended config source:

- one Pi-local config file or env file consumed by both services.

Do not keep display bootstrap logic dependent on a hardcoded Python constant in only one process.

Long term:

- add a backend device registry and explicit `display_device/controller -> tap` binding.

### Architecture options evaluation

| Option | Verdict | Notes |
| --- | --- | --- |
| Browser in kiosk mode + backend-hosted page only | Not recommended as final runtime architecture | Good for quick demo, weak for offline tolerance, leaks backend auth into browser, poor source of live local state |
| Separate frontend bundle running locally on Pi | Recommended | Best balance of resilience, reuse, and clean separation |
| Backend-driven remote page with no local agent | Reject for production | Too dependent on network and backend freshness |
| Native app on Pi | Not recommended now | Higher implementation and maintenance cost with no strong advantage for current scope |

### Content/config flow

Recommended flow:

1. Admin edits beverage presentation and tap display settings in Admin App.
2. Backend persists structured content and media metadata.
3. Display agent fetches the content snapshot for its `tap_id`.
4. Display agent caches JSON and image assets locally.
5. Browser renders:
   - local runtime state from controller;
   - latest known centrally managed content from backend cache.

### Security recommendation

Do not let the kiosk browser call existing broad backend endpoints directly with `X-Internal-Token`.

Reasons:

- current internal token is effectively device-powerful, not read-only display-scoped;
- a browser on a physical device is not a safe secret boundary;
- display only needs a narrow read model.

Recommended security model:

- browser talks only to `localhost`;
- display agent talks to backend;
- long term, display agent uses a read-only device token with display scope.

### Auto-start on Raspberry Pi

Recommended boot model:

- controller as a `systemd` service;
- display agent as a `systemd` service;
- Chromium launched in kiosk mode on autologin session;
- browser points to local display URL;
- screen blanking disabled;
- browser crash should auto-restart or reopen on session restart.

Practical startup recommendation:

- use Raspberry Pi OS kiosk/browser session for Chromium fullscreen launch;
- keep browser launch separate from controller service supervision;
- prefer a dedicated display user/session if deployment discipline allows it.

### Kiosk mode recommendation

Recommended Chromium behavior:

- fullscreen kiosk;
- no first-run prompts;
- no session restore prompts;
- no crash bubbles;
- no visible address bar or tabs;
- cursor hidden where possible;
- automatic reopen to the same local URL.

## 4. Data model proposal

### Core modeling principle

Use layered ownership and precedence:

1. tap-level override if explicitly set;
2. beverage-level presentation default;
3. system default fallback copy/theme.

Do not model dynamic session state in content tables. Dynamic state should stay runtime-derived.

### MVP model

#### `beverages` extension

Recommended new or clarified fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `description_short` | text nullable | short guest-facing copy, max 160 chars |
| `ibu` | numeric nullable | optional detailed info absent today |
| `display_brand_name` | varchar nullable | guest-facing brand label; fallback to `brewery` |
| `accent_color` | varchar nullable | theme accent |
| `background_asset_id` | UUID nullable | hero/background image |
| `logo_asset_id` | UUID nullable | brand/logo image |
| `text_theme` | enum/string nullable | light/dark/auto overlay hint |

Notes:

- `name`, `style`, `abv`, `sell_price_per_liter`, and `brewery` already exist and should be reused.
- This keeps reusable beverage presentation attached to the product, not the physical keg.

#### New `tap_display_configs`

One row per tap.

Recommended fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `tap_id` | FK/PK | one-to-one with tap |
| `enabled` | bool | feature toggle for the screen |
| `idle_instruction` | varchar/text nullable | default idle prompt |
| `fallback_title` | varchar nullable | shown when no keg/beverage assigned |
| `fallback_subtitle` | text nullable | secondary fallback copy |
| `maintenance_title` | varchar nullable | override for service mode |
| `maintenance_subtitle` | text nullable | operator-facing/guest-facing short note |
| `override_accent_color` | varchar nullable | tap-specific override |
| `override_background_asset_id` | UUID nullable | tap-specific override |
| `show_price_mode` | enum nullable | `per_100ml`, `per_liter`, `auto` |
| `updated_at` | timestamp | audit/support |

This is the correct home for physical-screen behavior and fallback copy.

#### New `media_assets`

Recommended MVP image model:

| Field | Type | Purpose |
| --- | --- | --- |
| `asset_id` | UUID PK | stable reference |
| `kind` | enum | `background`, `logo` |
| `storage_key` | varchar | path/object key |
| `mime_type` | varchar | validation |
| `width` | int | rendering hints |
| `height` | int | rendering hints |
| `checksum` | varchar | cache invalidation |
| `created_at` | timestamp | audit |

Storage can be local disk in MVP behind a storage adapter, with future migration to object storage if needed.

### Future-ready model

Future expansion should not require undoing the MVP shape. Additive future entities are enough.

Recommended future entities:

| Entity | Purpose |
| --- | --- |
| `display_themes` | reusable theme presets shared across beverages or taps |
| `keg_display_overrides` | exceptional per-keg promo or batch override |
| `display_devices` | actual hardware/display registry with token, hostname, last_seen |
| `display_copy_templates` | reusable localized copy blocks by state |
| `display_content_versions` | audit/versioning/publish workflow if content complexity grows |

### What should not be modeled in MVP

- no full WYSIWYG layout editor;
- no arbitrary page-builder schema;
- no separate CMS entity per tap screen state;
- no persistent guest/session snapshot table for rendering;
- no per-keg content as the default source.

### Recommended storage location

Canonical storage:

- structured content in backend/Postgres;
- image binaries in backend-managed file storage;
- latest snapshot and assets cached locally on Pi by display agent.

## 5. Content management proposal

### Where operators should edit content

Recommended editing split:

- beverage presentation data in Beverage management;
- tap fallback/override settings in Tap management;
- images uploaded through a shared media picker/library used by both.

### Recommended Admin App placement

#### Beverage editor

Best place for:

- guest-facing beverage title;
- brand/brewery label;
- style, ABV, IBU;
- short description;
- background image;
- logo;
- accent color.

Reason:

- this content follows the liquid, not the metal hardware;
- it updates automatically when a different keg of the same beverage is assigned to a tap;
- it avoids duplicating the same beer presentation on many taps.

#### Tap display settings

Best place for:

- fallback when the tap has no keg;
- maintenance/service override copy;
- optional tap-specific theme override;
- whether the display is enabled;
- price-display preference if venue wants per-tap variation;
- preview of the tap screen using current assignment.

Reason:

- this content belongs to the physical screen and local operational context.

### What should not be the main editing home

`kegs` should not be the main editing place for display content.

Reason:

- kegs are physical inventory instances;
- content would be duplicated and forgotten after replacement;
- bar operators would create data chaos when swapping inventory quickly.

### Separate display/content section?

Recommendation:

- not for MVP.

Why:

- the bar staff mental model is already centered around:
  - beverage catalog;
  - keg inventory;
  - tap assignment.
- a separate standalone display CMS would create a second workflow detached from the actual tap assignment moment.

Long-term exception:

- if the product grows into multi-venue content operations, campaigns, approval workflow, or template libraries, a dedicated display content section becomes justified.

### Data hygiene rules

Recommended operational rules:

- beverage presentation is the default source of guest-facing product content;
- tap override must be visibly marked as an override;
- no per-keg override in MVP;
- maintenance/error wording should stay mostly system-generated, with only short optional override fields;
- keep one background and one logo slot per beverage in MVP to avoid a mini-CMS explosion.

## 6. UX/UI concept

### Screen design constraints

The screen is mounted at the tap, viewed quickly, and often mid-action.

Design implications:

- glanceable in 1 to 3 seconds for the main action;
- readable on a 7-inch screen from short standing distance;
- must remain usable on common small-screen landscape resolutions;
- should avoid dense text blocks;
- should keep operator diagnostics secondary and guest instructions primary.

Recommended design baseline:

- landscape first;
- must remain clear at both `1024x600`-class and `800x480`-class layouts;
- no critical text at the extreme edges.

### Screen states

#### 1. Idle: ready to pour

Show:

- beverage name;
- derived display price;
- optional style and ABV;
- brand/brewery;
- strong next instruction.

Recommended primary instruction:

- `Приложите карту`

#### 2. Card detected / authorized

Show:

- greeting using first name only;
- current balance;
- confirmation that pouring is allowed;
- next action instruction.

Recommended primary instruction:

- `Откройте кран`

Privacy recommendation:

- show first name only by default;
- do not show full FIO or phone number on a public-facing screen.

#### 3. Card detected / denied

Show a short, explicit reason and one clear next step.

Recommended deny messages:

- `Недостаточно средств`
- `Карта не активна`
- `Карта утеряна`
- `Нет активного визита`

Recommended next-step messages:

- `Пополните баланс`
- `Обратитесь к оператору`
- `Заберите карту`

#### 4. Pouring

This is the most important runtime state.

Primary information:

- current volume in ml.

Secondary information:

- current cost in rubles;
- projected remaining balance;
- animated pour indicator.

Recommended emphasis:

- volume is the largest element on screen;
- cost is the second largest;
- projected balance is smaller.

Recommended wording:

- `Налито`
- `Сумма`
- `Остаток после списания`

To stay honest, the balance label may use a subtle approximate hint if needed:

- `Остаток после списания`
- or `Остаток ~`

#### 5. Finished

Show:

- final volume;
- final session cost;
- projected remaining balance;
- short completion message.

Recommended instruction:

- `Налив завершён`
- `Заберите карту`

#### 6. Error / unavailable / maintenance

Must be visually distinct from normal beverage branding.

Recommended states:

- no keg assigned;
- tap locked;
- cleaning / service;
- emergency stop;
- backend unavailable;
- processing sync.

Use guest-safe wording first, tiny operator hint second.

Example:

- headline: `Кран недоступен`
- subline: `Обратитесь к оператору`
- tiny operator code: `no_keg`, `processing_sync`, `backend_unreachable`

### Information hierarchy

Recommended rule:

- one primary message or number at a time;
- at most three meaningful data points visible in the main content block;
- background art must never compete with action text.

State-specific hierarchy:

| State | Largest element | Secondary | Smallest |
| --- | --- | --- | --- |
| Idle | Beverage name | Price | Style/ABV/instruction |
| Authorized | Greeting or `Можно наливать` | Balance | Instruction |
| Pouring | Volume ml | Cost | Balance |
| Finished | Final volume | Final cost | Completion cue |
| Error | Status headline | Next step | Operator code |

### Typography

Recommended direction:

- readable sans-serif with strong Cyrillic support;
- tabular numerals for volume and money;
- medium and bold weights only for MVP.

Recommended font family direction:

- `Onest`, `Golos Text`, or a similar Cyrillic-friendly sans.

Recommended sizing intent:

- beverage/state headline: very large;
- live volume: largest element on screen;
- subcopy: one short line;
- operator diagnostics: intentionally small and low-emphasis.

Avoid:

- all-caps for long Russian labels;
- condensed typefaces;
- light weights on images;
- more than two font families.

### Animation

Recommended animation system:

- calm ambient motion in idle;
- stronger but simple motion during pouring;
- fast state transitions without playful over-animation.

Recommended MVP animation types:

- animated progress ring or vertical fill tied to poured volume;
- numeric count-up for volume and cost;
- subtle fade/slide state changes.

Do not use in MVP:

- full-screen video backgrounds;
- heavy canvas effects;
- more than one decorative animation layer at once.

### Visual design principles

Recommended rules:

- use beverage color as accent, not as the only contrast layer;
- always place a dark or light overlay over background images;
- reserve a dedicated system palette for service/error states;
- maintain strong numeric emphasis and clean spacing.

Contrast target:

- body-sized text should meet at least standard accessible contrast;
- small text on top of images should use stronger contrast targets.

### Price display recommendation

Backend stores price per liter, but guest-facing display should use a more glanceable presentation.

Recommended default display:

- `X ₽ / 100 мл`

Reason:

- faster mental parsing at the tap;
- better correlation with the live running cost;
- less visual width than full ruble-per-liter emphasis.

Venue-specific override can still allow per-liter display if required.

### Guest instruction guidelines

Instruction copy should be:

- one action at a time;
- 2 lines max;
- short verbs first;
- consistent between states.

Recommended copy set:

- `Приложите карту`
- `Откройте кран`
- `Заберите карту`
- `Пополните баланс`
- `Обратитесь к оператору`
- `Кран недоступен`
- `Подождите`
- `Налив завершён`

Avoid:

- paragraphs;
- multi-step instructions in one screen;
- operator jargon as the main guest message.

## 7. Industry recommendations / best practices

The recommendations below align with four practical sources of truth:

- kiosk deployment guidance for Raspberry Pi;
- digital signage readability rules;
- contrast/accessibility guidance for text on variable backgrounds;
- self-pour industry patterns that emphasize live volume/cost feedback at the tap.

### What to do

- Keep the display single-purpose and state-driven.
- Make the next action obvious in every state.
- Use large live numerals for volume and cost during pouring.
- Use first-name greeting only, not full identity.
- Keep content centrally managed and automatically switched by tap assignment.
- Cache last known content locally on the Pi.
- Keep browser credentials local-only through a display agent.
- Use a clear service palette and wording for unavailable states.
- Use subtle animations that support the action, not entertainment.
- Design every screen assuming it is read in seconds, not minutes.

### What not to do

- Do not expose a shared backend internal token directly in the browser.
- Do not render the live guest display only from backend polling.
- Do not make `keg` the primary content owner.
- Do not overload a 7-inch screen with style, ABV, IBU, description, price, balance, and diagnostics all at once.
- Do not use photo backgrounds without a contrast overlay.
- Do not rely on color alone for status meaning.
- Do not promise a numeric `you can pour X ml` figure as a primary guest-facing truth in MVP.
- Do not create a separate mini-CMS for every tap before the operational model is proven.

### Common pitfalls

- treating a safe backend clamp as a guest guarantee;
- mixing guest instructions and operator diagnostics at the same visual weight;
- forgetting offline/stale-content behavior while the controller itself remains operational;
- letting tap overrides silently drift away from beverage defaults;
- using beautiful but low-contrast art that becomes unreadable in real bar lighting.

## 8. MVP scope

The first version should include only the parts that create a correct, supportable, guest-visible system.

Required MVP scope:

- one display per tap/controller;
- separate display web client running in Chromium kiosk mode;
- local display agent on the Pi;
- shared local device config containing `tap_id`;
- backend display content snapshot per tap;
- beverage-level presentation defaults;
- tap-level fallback and override config;
- image upload for a constrained image set;
- local caching of last known content/assets;
- Russian guest-facing copy;
- idle ready state;
- authorized card state;
- denied card states for the main business reasons;
- pouring state with live volume in ml;
- live cost in rubles during pouring;
- projected remaining balance during and after pour;
- finished state;
- unavailable / no keg / cleaning / maintenance / processing-sync states;
- auto-start on Raspberry Pi boot;
- crash/restart resilience good enough for pilot use.

Recommended MVP simplification:

- one reusable template engine;
- one main visual layout with state variants;
- one background image and one logo slot per beverage;
- one tap-level override layer only.

## 9. Deferred scope

The following should be postponed intentionally:

- per-keg content overrides;
- video backgrounds;
- full display WYSIWYG editor;
- touch interaction or on-screen buttons for guests;
- deep remote diagnostics and screenshot fleet management;
- multi-language runtime localization engine;
- fully official post-sync balance confirmation animation;
- campaign banners, QR upsell, rating prompts, cross-sell modules;
- full preview simulator for every runtime scenario inside Admin App;
- numeric guest-facing `available ml` promise as a primary screen element.

### Recommendation on "how much can the guest still pour"

Current repository analysis shows that the system already computes a backend-authoritative safety clamp:

- `max_volume_ml = floor((balance + overdraft) / price_per_ml_cents) - safety_ml`

This is operationally useful for valve control.

It should not be promoted as a primary guest-facing promise in MVP.

Reasoning:

- it is a safety limit, not a comfort estimate;
- it includes rounding and safety subtraction;
- tail flow and post-authorize edge cases can still make the display semantics confusing;
- on a small fast-action screen it competes with more important live data.

Recommended MVP use of that value:

- enforce it in controller logic;
- optionally use it as a hidden cap for the pouring animation/progress geometry;
- do not show `Вам доступно X мл` as a big guest-facing number.

## 10. Risks and trade-offs

### Technical risks

- Chromium kiosk behavior differs across Raspberry Pi OS versions and display stacks.
- Current controller config hardcodes `TAP_ID`; rollout needs a real device-config contract.
- Splitting content state and runtime state adds integration work.
- Asset caching and invalidation can become a source of stale UI if not versioned.
- Direct browser-to-backend auth would be a security mistake if not mediated.

### Product risks

- Showing guest balance publicly may raise privacy concerns.
- Overly branded layouts can reduce readability in real bar lighting.
- Guests may misread projected balance or allowed volume as an official settled statement.
- Too much detail on a 7-inch screen degrades the core action flow.

### Operational risks

- Staff may create inconsistent content if overrides are too flexible.
- Poor image hygiene will quickly make the system look broken or amateur.
- Empty/no-keg taps need strong fallback defaults or they will show blank/awkward states.
- Hardware replacement becomes painful if device identity and `tap_id` are not standardized.

### Main trade-offs

| Trade-off | Chosen side | Why |
| --- | --- | --- |
| Local runtime truth vs pure backend rendering | Local runtime truth | better resilience and correct live behavior |
| Beverage + tap model vs single-entity model | Beverage + tap | reflects actual ownership and reduces duplication |
| Separate display agent vs browser talking directly to backend | Separate agent | better security, caching, and local state integration |
| Minimal visuals vs rich branded visuals | Minimal-first branded | guest clarity matters more than decoration |
| Show clamp number vs hide it | Hide as primary UI | operationally useful, product-wise misleading |

## 11. Roadmap

### Phase 1. Foundation contracts

- replace hardcoded `TAP_ID` with shared Pi-local config;
- define local controller-to-display runtime snapshot contract;
- define backend display snapshot contract;
- freeze the first state machine for display rendering.

### Phase 2. Backend content layer

- add database migrations for display content and media metadata;
- add media storage abstraction;
- add aggregated display snapshot endpoint;
- add content version/hash support for caching.

### Phase 3. Admin App content management

- extend Beverage management with Display presentation fields;
- add Tap Display Settings UI;
- add image upload/picker flow;
- add simple tap preview card using current assignment.

### Phase 4. Pi display runtime

- add `tap-display-agent`;
- add local cache for JSON and assets;
- add local runtime API for the browser;
- wire controller runtime state publishing to the agent.

### Phase 5. Display UI MVP

- build display client screens for all MVP states;
- tune layout for 7-inch landscape;
- add performance-safe animations;
- test on monitor first, then actual Raspberry Pi display.

### Phase 6. Pilot hardening

- add autostart and watchdog behavior on Pi;
- verify stale-cache behavior;
- verify crash recovery;
- run real-bar readability/content QA;
- capture support feedback from operators.

### Phase 7. Post-MVP expansion

- add device registry and read-only display tokens;
- add richer preview tooling;
- consider per-keg overrides only after the base model proves stable;
- consider fleet management and diagnostics if deployment count grows.

## 12. Task breakdown

- `[Backend]` Add `tap_display_configs` migration and ORM model.
- `[Backend]` Extend `beverages` with display presentation fields.
- `[Backend]` Add `media_assets` table and image-serving path.
- `[Backend]` Add display snapshot resolver for `tap_id`.
- `[Backend]` Add display-scoped API contract separate from broad internal endpoints.
- `[Backend]` Add content version/hash for local cache invalidation.
- `[Backend]` Add optional backend device registry for future read-only display tokens.
- `[Admin App]` Extend Beverage UI with Display section.
- `[Admin App]` Add shared media picker/upload component.
- `[Admin App]` Add Tap Display Settings modal/drawer from `TapCard`.
- `[Admin App]` Add fallback/maintenance copy editing at tap level.
- `[Admin App]` Add preview thumbnail for idle and unavailable states.
- `[Pi]` Introduce shared device config file/env contract for controller and display agent.
- `[Pi]` Add controller runtime display snapshot publisher.
- `[Pi]` Add `tap-display-agent` service serving static client and local API.
- `[Pi]` Implement local cache for display snapshot JSON and assets.
- `[Frontend]` Create `tap-display-client` Svelte app.
- `[Frontend]` Implement state renderer for idle/authorized/denied/pouring/finished/error.
- `[Frontend]` Implement lightweight animation system and numeric transitions.
- `[Frontend]` Implement stale/offline fallback UI.
- `[Infra]` Add Raspberry Pi autostart instructions and service definitions.
- `[QA]` Create test matrix for monitor mode and real 7-inch hardware.
- `[QA]` Add verification scenarios for no keg, cleaning, insufficient funds, lost card, backend unavailable, and processing sync.
- `[QA]` Add content QA checklist for image contrast and text length.

## 13. Recommended implementation order

1. Standardize Pi-local device configuration and remove the hardcoded `TAP_ID` assumption as the only source of truth.
2. Define the local runtime snapshot contract from controller to display layer.
3. Add the backend display content model and aggregated snapshot endpoint.
4. Add Admin App editing for beverage presentation and tap-level fallback/override settings.
5. Build the display agent that serves the client locally and keeps backend auth out of the browser.
6. Build the display client screens and wire them to local runtime plus cached backend content.
7. Add Raspberry Pi kiosk autostart and crash-recovery behavior.
8. Run pilot QA on a normal monitor, then on the real 7-inch display, then in a live bar workflow.

Why this order is correct:

- UI should not be built before contracts are stable.
- local runtime bridging is more foundational than visuals.
- content management must exist before the screen can be maintained operationally.
- kiosk boot polish should come after the display actually renders meaningful states.

## 14. Final recommendation

The best implementation path is:

- a separate kiosk display web client;
- served locally on each Raspberry Pi by a small display agent;
- rendered in Chromium kiosk mode;
- driven by local controller runtime state for live session behavior;
- driven by backend-managed beverage and tap content for branding and configuration.

Content ownership should be split as follows:

- `beverage` owns reusable guest-facing presentation;
- `tap` owns fallback and physical-screen overrides;
- `keg` stays operational and only becomes an override layer later if the product proves it is needed.

For MVP, the screen should focus on:

- idle product presentation;
- name and balance after card authorization;
- live volume in ml;
- live cost in rubles;
- projected remaining balance;
- clear finish and error states.

The system should not show a large numeric `available ml` promise in MVP. The backend clamp should remain an operational safety mechanism, not a guest-facing headline.

This recommendation is the strongest fit for the current repository because it:

- reuses the existing visit/tap/keg/beverage architecture;
- respects the controller as the true source of fast local runtime state;
- keeps content centrally managed from backend/Admin App;
- avoids putting privileged backend credentials in the browser;
- stays maintainable for real bar operations instead of creating a separate content-management silo.
