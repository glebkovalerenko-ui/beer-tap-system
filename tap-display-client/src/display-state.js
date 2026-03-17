const DEFAULT_RUNTIME = {
  phase: "idle",
  reason_code: null,
  current_volume_ml: 0,
  current_cost_cents: 0,
};

const WARNING_CODE_BACKEND_UNREACHABLE = "backend_unreachable";
const ACTIVE_RUNTIME_WARNING_PHASES = new Set(["authorized", "pouring", "finished"]);
const FAST_POLL_PHASES = new Set(["authorizing", "authorized", "pouring", "finished"]);
const BLOCKED_SERVICE_CODES = new Set([
  "maintenance",
  "processing_sync",
  "emergency_stop",
  "authorize_invalid_contract",
  "controller_runtime_stale",
  "flow_timeout",
]);
const TAP_SERVICE_CODES_BY_STATUS = {
  cleaning: "cleaning",
  empty: "empty",
  locked: "locked",
  processing_sync: "processing_sync",
};

export const DISPLAY_STATE_PRECEDENCE = [
  "runtime_denied",
  "controller_runtime_stale",
  "runtime_blocked",
  "bootstrap_missing_backend_lost",
  "emergency_stop",
  "runtime_authorizing",
  "runtime_authorized",
  "runtime_pouring",
  "runtime_finished",
  "tap_service_state",
  "backend_link_lost",
  "booting",
  "idle",
];

export function isFastRuntimePhase(phase) {
  return FAST_POLL_PHASES.has(phase);
}

export function getSnapshotCopy(snapshot) {
  return snapshot?.copy ?? snapshot?.copy_block ?? {};
}

function resolveBlockedServiceCode(reasonCode) {
  return BLOCKED_SERVICE_CODES.has(reasonCode) ? reasonCode : "maintenance";
}

function resolveTapServiceCode(snapshot) {
  if (!snapshot) return null;
  if (snapshot.service_flags?.emergency_stop) return "emergency_stop";
  if (!snapshot.tap?.enabled) return "maintenance";

  const tapStatus = snapshot.tap?.status ?? "active";
  if (tapStatus !== "active") {
    return TAP_SERVICE_CODES_BY_STATUS[tapStatus] ?? "maintenance";
  }

  if (!snapshot.assignment?.has_assignment) {
    return "no_keg";
  }

  return null;
}

export function resolveDisplayState({ bootstrap, runtimePayload, bootstrapError, runtimeError }) {
  const snapshot = bootstrap?.snapshot ?? null;
  const runtime = runtimePayload?.runtime ?? DEFAULT_RUNTIME;
  const health = runtimePayload?.health ?? {};
  const backendLinkLost = Boolean(bootstrap?.backend?.link_lost || health.backend_link_lost || bootstrapError);
  const controllerRuntimeStale = Boolean(health.controller_runtime_stale || runtimeError);
  const runtimePhase = runtime.phase ?? "idle";
  const progress = runtime.max_volume_ml ? Math.min(runtime.current_volume_ml / runtime.max_volume_ml, 1) : 0;
  const warning = backendLinkLost && ACTIVE_RUNTIME_WARNING_PHASES.has(runtimePhase)
    ? WARNING_CODE_BACKEND_UNREACHABLE
    : null;

  if (runtimePhase === "denied") {
    return { kind: "denied", code: runtime.reason_code ?? "authorize_rejected", runtime, snapshot, progress, warning };
  }

  if (controllerRuntimeStale) {
    return { kind: "service", code: "controller_runtime_stale", runtime, snapshot, progress, warning: null };
  }

  if (runtimePhase === "blocked") {
    return {
      kind: "service",
      code: resolveBlockedServiceCode(runtime.reason_code),
      runtime,
      snapshot,
      progress,
      warning: null,
    };
  }

  if (!snapshot && backendLinkLost) {
    return { kind: "service", code: "no_connection", runtime, snapshot, progress, warning: null };
  }

  if (runtimePhase === "authorizing") {
    return { kind: "authorized", code: "authorizing", runtime, snapshot, progress, warning: null };
  }

  if (runtimePhase === "authorized") {
    return { kind: "authorized", code: "authorized", runtime, snapshot, progress, warning };
  }

  if (runtimePhase === "pouring") {
    return { kind: "pouring", code: "pouring", runtime, snapshot, progress, warning };
  }

  if (runtimePhase === "finished") {
    return { kind: "finished", code: "finished", runtime, snapshot, progress, warning };
  }

  const tapServiceCode = resolveTapServiceCode(snapshot);
  if (tapServiceCode) {
    return { kind: "service", code: tapServiceCode, runtime, snapshot, progress, warning: null };
  }

  if (backendLinkLost) {
    return { kind: "service", code: "no_connection", runtime, snapshot, progress, warning: null };
  }

  if (!snapshot) {
    return { kind: "service", code: "booting", runtime, snapshot, progress, warning: null };
  }

  return { kind: "idle", code: "idle", runtime, snapshot, progress, warning: null };
}
