# TAP_DISPLAY_FOUNDATION_ARCHITECTURE_AUDIT

Date: 2026-03-14
Scope: architecture and scope audit of the already-implemented Tap Display foundation
Mode: analysis only, no feature expansion performed
Follow-up corrections: `docs/reports/TAP_DISPLAY_FOUNDATION_CORRECTIONS.md`

## 1. Executive summary

The Tap Display foundation is based on the right high-level architecture:

- backend-owned content snapshot
- controller-owned live runtime snapshot
- local display agent as the browser/backend boundary
- separate kiosk UI client

That architectural split is sound and matches the previously agreed concept well. The main issue is not the chosen architecture, but the quality of several implementation details that were landed all at once.

Current verdict:

- the foundation is directionally correct;
- most major components should be kept;
- no large rollback is needed;
- further feature development should pause until a small set of contract, security, and runtime-precedence problems are corrected.

The most important problems found are:

1. The display agent still uses the same broad internal token model as the controller, and backend internal-token access is accepted by the shared `get_current_user` path for all protected endpoints.
2. The display client’s state-precedence logic does not correctly surface stale-controller runtime during active session states.
3. Media handling is under-validated and under-hardened for long-term maintenance.
4. Raspberry Pi kiosk startup is only pilot-grade and is not yet resilient enough to call production ready.

## 2. Scope comparison with original concept

### What matches the original concept

The implementation strongly matches the proposed architecture in these areas:

- `beverage` is the primary content owner for reusable guest-facing presentation.
- `tap_display_configs` is used as the tap-level override/fallback layer.
- `keg` was not made the primary display content owner.
- backend exposes a dedicated aggregated snapshot endpoint: `GET /api/display/taps/{tap_id}/snapshot`.
- controller publishes a local JSON runtime snapshot rather than pushing display logic into backend-only polling.
- a separate `tap-display-agent` exists and the browser talks to `localhost`, not directly to backend.
- a separate Svelte kiosk client exists instead of reusing the Admin App.
- Raspberry Pi deployment artifacts were added for controller, agent, and kiosk launch.

### What diverges or is incomplete

- The security model is only partially aligned with the concept. The browser is isolated from backend credentials, which is good, but the agent still uses a broad internal token instead of a display-scoped read-only credential.
- The client does not fully implement the intended service-state precedence. Active branded states can win over `controller_runtime_stale`, which is the opposite of the spec intent.
- Tap status handling is incomplete in the client. `cleaning` is handled, but other non-active tap statuses are not clearly mapped into service states.
- Admin App changes only cover a minimal beverage creation surface. The agreed tap-level display settings and media-management workflow are not present yet.
- Deployment artifacts exist, but Chromium lifecycle/restart behavior is not yet hardened to the level described in the concept package.

### Components introduced too early

Nothing in the implementation is fundamentally off-architecture, but a few pieces arrived before the surrounding hardening was ready:

- partial Admin App display fields
- kiosk deployment artifacts
- media upload surface without full validation and lifecycle rules

These are not wrong additions. They were simply landed before the surrounding operational and security polish was complete.

## 3. Backend architecture review

### Models

#### `beverages` display fields

Assessment:

- Ownership is correct.
- The chosen fields are a good MVP set.
- Keeping reusable branding/presentation on `beverage` matches the agreed model and avoids per-keg duplication.

What is good:

- `description_short`, `display_brand_name`, `accent_color`, `background_asset_id`, `logo_asset_id`, `text_theme`, and `price_display_mode_default` belong at beverage level.
- The extension is additive and future-friendly.
- The model does not leak dynamic session state into content tables.

What is missing or weak:

- There are no real enum/check constraints for `text_theme`, `price_display_mode_default`, or asset `kind`.
- `accent_color` is a free-form string with no format validation.
- `updated_at` exists, but there is no stronger content lifecycle/version model beyond snapshot hashing.

Conclusion:

- ownership model is correct;
- entity placement is correct;
- stronger validation is needed before the data model can be considered robust.

#### `tap_display_configs`

Assessment:

- This is the correct home for physical-screen behavior and fallback content.
- One-row-per-tap is a good MVP shape.

What is good:

- `enabled`, idle/fallback/maintenance copy, tap accent override, background override, and tap price mode all belong here.
- The table is simple and additive.
- `tap_id` as PK cleanly expresses one-to-one ownership.

What is weak:

- `show_price_mode` is also free-form.
- There is no validation for copy length, tone, or override hygiene.
- There is no explicit distinction between “unset” and “intentionally blank” copy beyond nullable fields.

Conclusion:

- correct entity;
- good MVP scope;
- needs input validation but not redesign.

#### `media_assets`

Assessment:

- The table itself is a correct MVP abstraction.
- The implementation around it is less mature than the schema.

What is good:

- generic asset table is better than embedding file paths directly into beverage/tap tables;
- stable `asset_id` + `storage_key` + checksum is a reasonable base;
- future storage migration remains possible.

What is weak:

- width/height are modeled but never populated by upload flow;
- there is no reference counting, cleanup, or orphan-management strategy;
- there is no MIME/kind/size validation policy in the upload path;
- missing-file behavior is not hardened.

Conclusion:

- the table should stay;
- the upload/content implementation needs refactoring and hardening.

### Content ownership questions

1. Is the content ownership model correct?

Yes, mostly. `beverage` as reusable presentation owner and `tap` as override/fallback owner is the right split.

2. Is any data incorrectly attached to the wrong entity?

No major misplacement was found. The implementation correctly avoided putting primary presentation on `keg`.

3. Is anything missing that will clearly be needed later?

Yes:

- display-scoped device identity / token model
- stronger field validation
- asset lifecycle management
- explicit runtime/service precedence tests across backend-agent-client boundaries

4. Is anything introduced that will likely cause maintenance issues?

Yes:

- stringly typed display modes/themes/kinds
- media upload without strong validation
- no orphan cleanup for assets

### API design

#### Snapshot endpoint

Assessment:

- The snapshot concept is implemented correctly at a high level.
- The payload shape is clean and deliberately display-oriented.
- `ETag` support is correctly aligned to `content_version`, not `generated_at`.

What is good:

- the client does not need to stitch together broad backend internals;
- the endpoint returns only display-facing content slices;
- content precedence is resolved server-side;
- `304 Not Modified` behavior is implemented.

What is weak:

- service-state semantics are not fully encoded in a way that guarantees consistent client handling for all tap statuses;
- the endpoint is still protected by the same broad auth mechanism as the rest of the backend, so the clean API boundary is not matched by an equally clean trust boundary.

Overall backend API verdict:

- clean and minimal enough for MVP;
- architecturally correct;
- security and validation layers need refactoring.

### Migration safety

Assessment:

- The migration is additive and low-risk compared with structural rewrites.
- It should migrate safely on the current repository shape.

What is good:

- no destructive change to existing operational entities;
- new tables are isolated;
- beverage changes are additive with server defaults where needed.

What to watch:

- free-form string fields mean invalid states can still enter the DB after migration;
- media storage lives partly in DB and partly on disk without transactional coupling.

## 4. Controller runtime integration review

### Overall assessment

This is one of the strongest parts of the implementation.

What is correct:

- display runtime is kept separate from backend business authority;
- the runtime publisher is a side effect, not a new control authority;
- snapshot writes are atomic;
- runtime publishing is injected into `FlowManager` rather than tangled into hardware abstractions;
- tests exist and passed for idle, denied, and finished runtime publication.

Why this is safe for pouring logic

- core pour control still depends on existing authorization, valve, sensor, and sync logic;
- display publishing does not feed back into valve control;
- file publication failure would degrade display state, not authorize a pour.

Residual concerns:

- runtime snapshots are written during the pour loop, so publication frequency is tied to the control loop cadence;
- because the output path is under `/run`, this is acceptable on Pi tmpfs, but it is still worth rate-limiting or change-detecting later if log/IO churn becomes noticeable.

Contract stability:

- the runtime payload is simple and understandable;
- the state names are stable enough for MVP;
- schema versioning exists in payload and is a good sign.

Controller integration verdict:

- safe enough for further use;
- clean separation achieved;
- keep the pattern.

## 5. Display agent architecture review

### Overall assessment

The display agent is the correct abstraction.

It solves the right problems:

- keeps backend credentials out of the browser;
- combines backend content with controller-local runtime;
- caches snapshot JSON and assets;
- exposes a narrow localhost API for the kiosk client.

### Responsibility boundaries

Good:

- content polling and caching live in the agent;
- live runtime reading stays local;
- browser only reads `localhost` endpoints.

Weak:

- the agent does not yet own a display-scoped identity;
- cache cleanup is incomplete;
- there are no tests for agent polling, stale detection, or asset rewrite behavior.

### Polling strategy

- 5-second backend polling with conditional `ETag` is reasonable for MVP.
- This is a good tradeoff versus premature event infrastructure.

### Cache invalidation

Mostly correct:

- snapshot cache uses `ETag`;
- asset cache keys include checksum in filename;
- changed assets will re-download when snapshot changes.

Missing:

- old cached assets are never garbage-collected;
- there is no explicit repair path if DB metadata exists but on-disk cache is inconsistent beyond returning 404.

### Security model

Partially correct:

- browser is isolated from backend credentials;
- agent is localhost-bound by default;
- this is much better than direct browser-to-backend access.

But the most important gap is still here:

- the agent loads `INTERNAL_TOKEN` / `INTERNAL_API_KEY` from the shared device env;
- it sends that token as `X-Internal-Token`;
- backend treats valid internal tokens as authenticated for the shared protected-path mechanism.

That means the browser is isolated, but the agent is still effectively using a device-powerful credential model, not a display-scoped read-only one.

Agent verdict:

- correct abstraction;
- acceptable MVP shortcut on auth scope;
- should be kept, but its credential model should be refactored before wider rollout.

## 6. Display client architecture review

### Overall assessment

The client architecture is viable for MVP, but the implementation is too monolithic and contains one important state-precedence bug.

What is good:

- separate app from Admin App is the right choice;
- local polling of bootstrap and runtime matches the agent contract;
- screen states map cleanly to the intended UX model;
- the bundle builds successfully.

What is weak:

- `src/App.svelte` currently contains nearly all state resolution, view switching, and styling in one file;
- this is acceptable for a first MVP pass, but it is not the right long-term structure;
- more importantly, stale-controller handling is ordered incorrectly.

### Important bug: stale controller runtime precedence

The client computes `controllerRuntimeStale`, but active runtime branches for `authorized`, `pouring`, and `finished` return before the stale-runtime branch is checked.

Effect:

- a stale active session can keep rendering as a valid branded session instead of degrading to a service state;
- this diverges from the implementation spec and weakens operational honesty.

### Screen-state support

Supported well enough:

- idle
- authorizing
- authorized
- denied
- pouring
- finished
- generic service states

Incomplete or weak:

- non-cleaning tap statuses are not fully expressed as service states;
- precedence between backend loss, stale controller runtime, tap status, and branded content should be encoded more explicitly and tested.

Performance for Raspberry Pi:

- acceptable for MVP;
- the build size is modest;
- polling cadence is reasonable for this screen class.

Client verdict:

- safe to keep;
- should be refactored before feature growth;
- stale-state precedence must be corrected before continuing.

## 7. Deployment model review

### Overall assessment

Deployment artifacts are pilot viable, not production viable.

What is good:

- controller and display agent both have `systemd` units;
- both units restart automatically;
- a kiosk launch script exists and targets the local display URL.

What is weak:

- Chromium is launched by desktop autostart, not by a supervised service;
- there is no restart loop for the browser itself;
- there is no explicit dependency/wait logic ensuring the agent is ready before Chromium first opens;
- screen blanking / power-management hardening is not present in the provided artifacts;
- actual Pi-specific kiosk behavior still needs validation.

Deployment verdict:

- good enough for pilot/prototype bring-up;
- not yet hardened enough for production.

## 8. Security assessment

### Serious concerns

1. Shared internal-token trust is too broad.

- The display agent uses the same device env token style as the controller.
- Backend accepts internal token auth inside the shared `get_current_user` dependency.
- This means the display path is not read-only scoped at the auth layer.

2. Demo-token fallback remains active unless explicitly disabled/configured.

- `demo-secret-key` compatibility remains part of the allowed-key path.
- That is useful for local development, but risky if configuration hygiene slips on a real device.

### Moderate concerns

3. Media upload is not strongly validated.

- No clear file-type, size, or content validation policy is enforced in the upload path.

4. Asset/content storage is not transactionally coupled.

- File save happens before DB persistence is finalized.
- DB failure can leave orphaned files.

### What is done right

- browser does not call backend directly;
- browser does not receive the backend token;
- agent binds to localhost by default;
- media assets are served through backend and agent, not shared as raw disk paths.

Security verdict:

- architecture improved security versus direct browser/backend access;
- current credential scope is still too broad and should be treated as a priority fix.

## 9. Complexity vs MVP analysis

Overall assessment:

- moderately complex but acceptable

Why:

- the separate agent is justified, not overengineering;
- split authority between backend content and controller runtime is the correct complexity for this use case;
- the main problem is not that too many components exist, but that several were landed without enough hardening at the boundaries.

What is lean:

- snapshot-based backend API
- local runtime JSON contract
- Svelte kiosk client
- polling + `ETag` instead of event infrastructure

What feels early:

- partial admin surface before the whole content workflow is ready
- deployment artifacts before kiosk resilience is fully validated
- media-management surface before validation/lifecycle rules were defined

## 10. Component classification

| Component | Classification | Notes |
| --- | --- | --- |
| `beverages` display fields | MUST KEEP | Correct ownership and good MVP shape; add validation rather than redesign. |
| `tap_display_configs` model and CRUD | MUST KEEP | Correct tap-level override layer and aligned with agreed design. |
| `media_assets` table | MUST KEEP | Correct abstraction for reusable media metadata. |
| media upload/list/content endpoints | SHOULD BE REFACTORED | Useful, but validation, error handling, and asset lifecycle are under-hardened. |
| display snapshot endpoint | MUST KEEP | Cleanest part of the backend display contract; correct abstraction. |
| shared Pi `device.env` contract | MUST KEEP | Necessary improvement over a hardcoded `TAP_ID`; should eventually become a shared utility or device registry. |
| controller runtime JSON publisher | MUST KEEP | Clean, safe, and well-aligned with the concept. |
| `flow_manager` display publishing hooks | MUST KEEP | Separation from valve/business logic is acceptable; keep and lightly harden. |
| `tap-display-agent` service | MUST KEEP | Correct abstraction and important security boundary for the browser. |
| display-agent auth model using broad internal token | ARCHITECTURALLY RISKY | Works for MVP, but not aligned with long-term read-only display identity. |
| global backend acceptance of internal token via shared auth dependency | SHOULD BE REFACTORED | Too much backend power behind one device token. |
| legacy demo internal-token fallback | SHOULD BE ROLLED BACK | Fine for local dev only; too risky as a deployable default path. |
| `tap-display-client` app | MUST KEEP | Correct app boundary and acceptable MVP performance. |
| monolithic `tap-display-client/src/App.svelte` implementation | SHOULD BE REFACTORED | Scales poorly and already hides a precedence bug. |
| stale-runtime handling in display client | SHOULD BE REFACTORED | Important behavioral bug; must be fixed before more features are added. |
| Raspberry Pi `systemd` units for controller and agent | MUST KEEP | Good base for pilot deployment. |
| Chromium kiosk autostart artifacts | GOOD BUT OPTIONAL | Useful for pilot setup, but not resilient enough yet for production claims. |
| minimal Admin App beverage display fields | GOOD BUT OPTIONAL | Low-risk and aligned with ownership model, but incomplete and not yet the real operator workflow. |
| implementation-spec documentation | GOOD BUT OPTIONAL | Helpful and mostly accurate, but the code currently diverges in a few important details. |

## 11. Identified risks

1. Display auth scope is too broad and still tied to the generic internal-device credential model.
2. A stale active controller runtime can remain visually indistinguishable from a healthy active session.
3. Media uploads can drift into inconsistent states because validation and cleanup are incomplete.
4. Browser crash/startup ordering is not resilient enough for unattended production deployment.
5. Display-related data fields are too stringly typed, which will increase support burden as more content is entered.
6. The current Admin App additions can create false confidence that content operations are “done” even though tap-level settings and media workflows are still missing.
7. Agent/client/deployment integration has limited automated test coverage.

## 12. Recommended corrections

Priority 1, before more Tap Display feature work:

1. Refactor the display auth path.
   - Separate display-agent read access from broad controller/internal access.
   - Remove deployable reliance on `demo-secret-key`.
   - Narrow where `X-Internal-Token` is accepted.

2. Fix and freeze the client state-precedence matrix.
   - `controller_runtime_stale` must override branded active-session rendering.
   - Tap statuses beyond `cleaning` should be explicitly mapped.
   - Add tests for precedence across runtime, backend loss, and tap status.

3. Harden media handling.
   - Validate asset kind, MIME type, file size, and allowed extensions.
   - Decide whether width/height will be populated or dropped from MVP.
   - Handle missing files and orphan cleanup explicitly.

Priority 2, before pilot rollout:

4. Harden kiosk deployment.
   - Add browser restart strategy or supervision.
   - Verify startup ordering against agent readiness.
   - Add Pi-specific screen/power-management hardening.

5. Add missing integration tests.
   - agent polling and stale detection
   - client state precedence
   - degraded/offline scenarios

Priority 3, maintainability cleanup:

6. Add stronger schema validation for display-specific enums and color fields.
7. Split the client into smaller state/render modules before the screen logic grows further.
8. Decide whether Admin App display work stays minimal for now or is completed properly with tap-level settings and media management.

## 13. Final verdict

Foundation needs refactoring before continuing

Why:

- the underlying architecture is good and should be preserved;
- most of the foundation is worth keeping;
- there is no need for a broad rollback;
- however, the security scope, stale-runtime handling, and deployment hardening are important enough that continued feature expansion would build on unstable assumptions.

Recommended next move:

- pause new Tap Display features;
- fix the priority-1 corrections above;
- then continue from the existing architecture rather than replacing it.
