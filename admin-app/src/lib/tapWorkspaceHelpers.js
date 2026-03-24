/** @typedef {{ tap_id?: string|number, operations?: { activeSessionSummary?: { visitId?: string|number } } }} TapLike */
/** @typedef {{ visitId?: string|number, tapId?: string|number, tap?: TapLike }} TapWorkspaceOpenHistoryPayload */

/**
 * @param {TapWorkspaceOpenHistoryPayload} detail
 */
export function resolveSessionHistoryTargets(detail) {
  const visitId = detail.visitId || detail.tap?.operations?.activeSessionSummary?.visitId || null;
  const tapId = detail.tap?.tap_id || detail.tapId || null;
  return { visitId, tapId };
}
