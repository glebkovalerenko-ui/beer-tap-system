import test from "node:test";
import assert from "node:assert/strict";

import { DISPLAY_STATE_PRECEDENCE, resolveDisplayState } from "../src/display-state.js";

function makeSnapshot(overrides = {}) {
  const {
    tap = {},
    service_flags: serviceFlags = {},
    assignment = {},
    ...rest
  } = overrides;

  return {
    tap: {
      enabled: true,
      status: "active",
      ...tap,
    },
    service_flags: {
      emergency_stop: false,
      ...serviceFlags,
    },
    assignment: {
      has_assignment: true,
      ...assignment,
    },
    copy: {},
    presentation: {},
    pricing: {},
    theme: {},
    ...rest,
  };
}

function makeRuntimePayload(overrides = {}) {
  return {
    runtime: {
      phase: "idle",
      reason_code: null,
      current_volume_ml: 0,
      current_cost_cents: 0,
      ...overrides.runtime,
    },
    health: {
      backend_link_lost: false,
      controller_runtime_stale: false,
      ...overrides.health,
    },
  };
}

test("documents the frozen precedence order", () => {
  assert.deepEqual(DISPLAY_STATE_PRECEDENCE.slice(0, 6), [
    "runtime_denied",
    "controller_runtime_stale",
    "runtime_blocked",
    "bootstrap_missing_backend_lost",
    "emergency_stop",
    "tap_service_state",
  ]);
});

test("controller runtime stale overrides branded active runtime", () => {
  const state = resolveDisplayState({
    bootstrap: { snapshot: makeSnapshot(), backend: { link_lost: false } },
    runtimePayload: makeRuntimePayload({
      runtime: { phase: "authorized" },
      health: { controller_runtime_stale: true },
    }),
    bootstrapError: null,
    runtimeError: null,
  });

  assert.equal(state.kind, "service");
  assert.equal(state.code, "controller_runtime_stale");
});

test("blocked runtime keeps explicit service code", () => {
  const state = resolveDisplayState({
    bootstrap: { snapshot: makeSnapshot(), backend: { link_lost: false } },
    runtimePayload: makeRuntimePayload({
      runtime: { phase: "blocked", reason_code: "flow_timeout" },
    }),
    bootstrapError: null,
    runtimeError: null,
  });

  assert.equal(state.kind, "service");
  assert.equal(state.code, "flow_timeout");
});

test("tap statuses beyond cleaning are mapped into service states", () => {
  const locked = resolveDisplayState({
    bootstrap: { snapshot: makeSnapshot({ tap: { status: "locked" } }), backend: { link_lost: false } },
    runtimePayload: makeRuntimePayload(),
    bootstrapError: null,
    runtimeError: null,
  });
  const empty = resolveDisplayState({
    bootstrap: { snapshot: makeSnapshot({ tap: { status: "empty" } }), backend: { link_lost: false } },
    runtimePayload: makeRuntimePayload(),
    bootstrapError: null,
    runtimeError: null,
  });
  const processingSync = resolveDisplayState({
    bootstrap: { snapshot: makeSnapshot({ tap: { status: "processing_sync" } }), backend: { link_lost: false } },
    runtimePayload: makeRuntimePayload(),
    bootstrapError: null,
    runtimeError: null,
  });

  assert.equal(locked.code, "locked");
  assert.equal(empty.code, "empty");
  assert.equal(processingSync.code, "processing_sync");
});

test("backend link loss keeps active authorized state but adds warning", () => {
  const state = resolveDisplayState({
    bootstrap: { snapshot: makeSnapshot(), backend: { link_lost: true } },
    runtimePayload: makeRuntimePayload({
      runtime: { phase: "authorized" },
      health: { backend_link_lost: true },
    }),
    bootstrapError: null,
    runtimeError: null,
  });

  assert.equal(state.kind, "authorized");
  assert.equal(state.warning, "backend_unreachable");
});

test("missing snapshot plus backend loss becomes no_connection service state", () => {
  const state = resolveDisplayState({
    bootstrap: { snapshot: null, backend: { link_lost: true } },
    runtimePayload: makeRuntimePayload(),
    bootstrapError: "bootstrap_http_503",
    runtimeError: null,
  });

  assert.equal(state.kind, "service");
  assert.equal(state.code, "no_connection");
});
