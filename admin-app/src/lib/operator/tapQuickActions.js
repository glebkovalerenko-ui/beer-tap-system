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
  const tapName = tap?.display_name || 'кран';
  const isLocked = tap?.status === 'locked';
  const stopGuard = getCriticalActionGuard('stop_pour', permissions, {
    extraAllowed: canControl && Boolean(session),
    extraDeniedReason: session ? '' : 'На этом кране нет активного визита, который можно остановить.',
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
      title: 'Открыть',
      description: 'Открыть детали крана, не теряя общий обзор рабочей зоны.',
      tone: 'primary',
    }), {
      event: 'open-detail',
      ariaLabel: `Открыть детали для ${tapName}`,
      visible: true,
      guarded: false,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'stop',
      title: 'Остановить',
      description: stopState.disabled
        ? (stopState.reason || 'Остановить налив сейчас нельзя.')
        : 'Остановить текущий налив на выбранном кране.',
      disabled: stopState.disabled,
      tone: 'danger',
    }), {
      event: 'stop-pour',
      ariaLabel: `Остановить текущий налив на ${tapName}`,
      visible: stopGuard.visible,
      guarded: true,
      reason: stopState.reason || stopGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'toggle-lock',
      title: isLocked ? 'Разблокировать' : 'Заблокировать',
      description: blockState.disabled
        ? (blockState.reason || 'Управление блокировкой сейчас недоступно.')
        : (isLocked ? 'Вернуть кран в рабочее состояние.' : 'Заблокировать кран до устранения проблемы.'),
      disabled: blockState.disabled,
    }), {
      event: 'toggle-lock',
      ariaLabel: `${isLocked ? 'Разблокировать' : 'Заблокировать'} ${tapName}`,
      visible: lockGuard.visible,
      guarded: true,
      reason: blockState.reason || lockGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'screen',
      title: 'Экран',
      description: screenState.disabled
        ? (screenState.reason || 'Настройки экрана крана сейчас недоступны.')
        : 'Открыть настройки гостевого экрана крана.',
      disabled: screenState.disabled,
    }), {
      event: 'display-settings',
      ariaLabel: `Открыть настройки экрана для ${tapName}`,
      visible: screenGuard.visible,
      guarded: true,
      reason: screenState.reason || screenGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'keg',
      title: 'Кега',
      description: kegState.disabled
        ? (kegState.reason || 'Действия с кегой сейчас недоступны.')
        : 'Открыть действия по кеге и напитку для этого крана.',
      disabled: kegState.disabled,
    }), {
      event: 'open-detail',
      ariaLabel: `Открыть действия по кеге для ${tapName}`,
      visible: kegGuard.visible,
      guarded: true,
      reason: kegState.reason || kegGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'history',
      title: 'История',
      description: historyState.disabled
        ? (historyState.reason || 'История по крану сейчас недоступна.')
        : 'Открыть связанный визит и недавние события по этому крану.',
      disabled: historyState.disabled,
    }), {
      event: 'open-history',
      ariaLabel: `Открыть историю визита для ${tapName}`,
      visible: Boolean(tap?.tap_id),
      guarded: historyState.disabled,
      reason: historyState.reason,
    }),
  ], TAP_QUICK_ACTION_ORDER).filter((action) => action.visible);
}
