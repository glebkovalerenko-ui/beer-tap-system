import { getCriticalActionGuard } from '../criticalActionMatrix.js';
import { createQuickActionDescriptor, orderQuickActionDescriptors } from './quickActionDescriptors.js';
import { resolveActionBlockState } from './actionPolicyAdapter.js';

const TAP_QUICK_ACTION_ORDER = ['open', 'stop', 'toggle-lock', 'screen', 'keg', 'history'];

function withMeta(descriptor, meta = {}) {
  return {
    ...descriptor,
    ...meta,
  };
}

function resolvePolicyBackedState(policy, fallback = {}) {
  if (policy) {
    return resolveActionBlockState(policy);
  }

  return {
    disabled: Boolean(fallback.disabled),
    reason: fallback.reason || '',
    policy: {
      allowed: !fallback.disabled,
      rawAllowed: !fallback.disabled,
    },
  };
}

export function buildTapQuickActions({
  tap,
  session,
  permissions = {},
  canControl = false,
  canDisplayOverride = false,
}) {
  const tapName = tap?.display_name || 'tap';
  const isLocked = tap?.status === 'locked';
  const stopGuard = getCriticalActionGuard('stop_pour', permissions, {
    extraAllowed: canControl && Boolean(session),
    extraDeniedReason: session ? '' : 'No active session is available to stop on this tap.',
  });
  const lockGuard = getCriticalActionGuard('block_unblock_tap', permissions, {
    extraAllowed: canControl,
  });
  const screenGuard = getCriticalActionGuard('display_override', permissions, {
    extraAllowed: canDisplayOverride,
  });
  const kegGuard = getCriticalActionGuard('keg_connect_disconnect', permissions, {
    extraAllowed: canControl,
  });

  const stopState = resolvePolicyBackedState(tap?.safe_actions?.stop, stopGuard);
  const blockState = resolvePolicyBackedState(tap?.safe_actions?.block, lockGuard);
  const screenState = resolvePolicyBackedState(tap?.safe_actions?.screen, screenGuard);
  const kegState = resolvePolicyBackedState(tap?.safe_actions?.keg, kegGuard);
  const historyState = resolvePolicyBackedState(tap?.safe_actions?.history, { disabled: !tap?.tap_id });

  return orderQuickActionDescriptors([
    withMeta(createQuickActionDescriptor({
      id: 'open',
      title: 'Open',
      description: 'Open tap details without losing the workspace overview.',
      tone: 'primary',
    }), {
      event: 'open-detail',
      ariaLabel: `Open details for ${tapName}`,
      visible: true,
      guarded: false,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'stop',
      title: 'Stop',
      description: stopState.disabled
        ? (stopState.reason || 'Stopping the pour is currently unavailable.')
        : 'Stop the active pour on the selected tap.',
      disabled: stopState.disabled,
      tone: 'danger',
    }), {
      event: 'stop-pour',
      ariaLabel: `Stop the active pour on ${tapName}`,
      visible: stopGuard.visible,
      guarded: true,
      reason: stopState.reason || stopGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'toggle-lock',
      title: isLocked ? 'Unlock' : 'Lock',
      description: blockState.disabled
        ? (blockState.reason || 'Tap lock control is currently unavailable.')
        : (isLocked ? 'Return the tap to an active state.' : 'Block the tap until the issue is resolved.'),
      disabled: blockState.disabled,
    }), {
      event: 'toggle-lock',
      ariaLabel: `${isLocked ? 'Unlock' : 'Lock'} ${tapName}`,
      visible: lockGuard.visible,
      guarded: true,
      reason: blockState.reason || lockGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'screen',
      title: 'Screen',
      description: screenState.disabled
        ? (screenState.reason || 'Tap screen settings are currently unavailable.')
        : 'Open the guest-facing tap screen settings.',
      disabled: screenState.disabled,
    }), {
      event: 'display-settings',
      ariaLabel: `Open the screen settings for ${tapName}`,
      visible: screenGuard.visible,
      guarded: true,
      reason: screenState.reason || screenGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'keg',
      title: 'Keg',
      description: kegState.disabled
        ? (kegState.reason || 'Keg actions are currently unavailable.')
        : 'Open keg and beverage actions for this tap.',
      disabled: kegState.disabled,
    }), {
      event: 'open-detail',
      ariaLabel: `Open keg actions for ${tapName}`,
      visible: kegGuard.visible,
      guarded: true,
      reason: kegState.reason || kegGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'history',
      title: 'History',
      description: historyState.disabled
        ? (historyState.reason || 'Tap history is currently unavailable.')
        : 'Open the related sessions and recent events for this tap.',
      disabled: historyState.disabled,
    }), {
      event: 'open-history',
      ariaLabel: `Open session history for ${tapName}`,
      visible: Boolean(tap?.tap_id),
      guarded: historyState.disabled,
      reason: historyState.reason,
    }),
  ], TAP_QUICK_ACTION_ORDER).filter((action) => action.visible);
}
