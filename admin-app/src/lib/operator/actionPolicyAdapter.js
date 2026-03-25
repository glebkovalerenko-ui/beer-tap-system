const DEFAULT_POLICY = Object.freeze({
  allowed: true,
  confirm_required: false,
  second_approval_required: false,
  reason_code_required: false,
  disabled_reason: null,
  enabled: true,
  reason: null,
});

export function normalizeOperatorActionPolicy(candidate = null, overrides = {}) {
  const source = candidate ? { ...DEFAULT_POLICY, ...candidate } : { ...DEFAULT_POLICY, ...overrides };
  const rawAllowed = typeof candidate?.allowed === 'boolean'
    ? candidate.allowed
    : (typeof candidate?.enabled === 'boolean'
      ? candidate.enabled
      : (typeof overrides.allowed === 'boolean'
        ? overrides.allowed
        : (typeof overrides.enabled === 'boolean' ? overrides.enabled : true)));
  const secondApprovalRequired = Boolean(source.second_approval_required || overrides.second_approval_required);
  const allowed = Boolean(rawAllowed) && !secondApprovalRequired;
  const disabledReason = allowed
    ? null
    : (
      source.disabled_reason
      || source.reason
      || overrides.disabled_reason
      || (secondApprovalRequired ? 'Requires second approval in a different workflow.' : 'Action is unavailable.')
    );

  return {
    allowed,
    rawAllowed: Boolean(rawAllowed),
    confirmRequired: Boolean(source.confirm_required || overrides.confirm_required),
    secondApprovalRequired,
    reasonCodeRequired: Boolean(source.reason_code_required || overrides.reason_code_required),
    disabledReason,
  };
}

export function resolveActionBlockState(policy = null, readOnlyReason = '') {
  if (readOnlyReason) {
    const normalized = normalizeOperatorActionPolicy(policy, { allowed: false, disabled_reason: readOnlyReason });
    return {
      disabled: true,
      reason: readOnlyReason,
      policy: { ...normalized, allowed: false, disabledReason: readOnlyReason },
    };
  }

  const normalized = normalizeOperatorActionPolicy(policy);
  return {
    disabled: !normalized.allowed,
    reason: normalized.disabledReason || '',
    policy: normalized,
  };
}
