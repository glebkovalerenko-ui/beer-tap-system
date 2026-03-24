/** @typedef {{ tap_id: string|number, display_name?: string }} TapLike */

/**
 * @param {TapLike[]} taps
 * @param {Set<string|number>} requestedTapConfigIds
 */
export function getPendingDisplayConfigTaps(taps, requestedTapConfigIds) {
  return taps.filter((tap) => !requestedTapConfigIds.has(tap.tap_id));
}

/** @param {string} state */
export function runtimeClass(state) {
  if (['critical', 'error', 'offline'].includes(state)) return 'critical';
  if (['warning', 'degraded', 'unknown'].includes(state)) return 'warning';
  return 'ok';
}
