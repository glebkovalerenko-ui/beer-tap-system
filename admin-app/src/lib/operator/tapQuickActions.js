import { getCriticalActionGuard } from '../criticalActionMatrix.js';
import { createQuickActionDescriptor, orderQuickActionDescriptors } from './quickActionDescriptors.js';

const TAP_QUICK_ACTION_ORDER = ['open', 'stop', 'toggle-lock', 'screen', 'keg', 'history'];

function withMeta(descriptor, meta = {}) {
  return {
    ...descriptor,
    ...meta,
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
    extraDeniedReason: session ? '' : 'На кране нет активной сессии для остановки налива.',
  });
  const lockGuard = getCriticalActionGuard('block_unblock_tap', permissions, {
    extraAllowed: canControl && Boolean(tap?.keg_id),
    extraDeniedReason: tap?.keg_id ? '' : 'На кране нет кеги, поэтому блокировка сейчас недоступна.',
  });
  const screenGuard = getCriticalActionGuard('display_override', permissions, {
    extraAllowed: canDisplayOverride,
  });
  const kegGuard = getCriticalActionGuard('keg_connect_disconnect', permissions, {
    extraAllowed: canControl,
  });

  return orderQuickActionDescriptors([
    withMeta(createQuickActionDescriptor({
      id: 'open',
      title: 'Открыть',
      description: 'Открыть карточку крана и перейти к деталям.',
      tone: 'primary',
    }), {
      event: 'open-detail',
      ariaLabel: `Открыть карточку крана ${tapName}`,
      visible: true,
      guarded: false,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'stop',
      title: 'Стоп',
      description: stopGuard.allowed
        ? 'Остановить активный налив на выбранном кране.'
        : (stopGuard.reason || 'Остановка налива сейчас недоступна.'),
      disabled: stopGuard.disabled,
      tone: 'danger',
    }), {
      event: 'stop-pour',
      ariaLabel: `Остановить налив на ${tapName}`,
      visible: stopGuard.visible,
      guarded: true,
      reason: stopGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'toggle-lock',
      title: isLocked ? 'Разблокировать' : 'Блокировать',
      description: lockGuard.allowed
        ? (isLocked ? 'Вернуть кран в рабочий режим.' : 'Остановить доступ к крану до решения проблемы.')
        : (lockGuard.reason || 'Блокировка крана сейчас недоступна.'),
      disabled: lockGuard.disabled,
    }), {
      event: 'toggle-lock',
      ariaLabel: `${isLocked ? 'Разблокировать' : 'Заблокировать'} ${tapName}`,
      visible: lockGuard.visible,
      guarded: true,
      reason: lockGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'screen',
      title: 'Экран',
      description: screenGuard.allowed
        ? 'Посмотреть и при необходимости скорректировать экран крана.'
        : (screenGuard.reason || 'Настройка экрана сейчас недоступна.'),
      disabled: screenGuard.disabled,
    }), {
      event: 'display-settings',
      ariaLabel: `Открыть экран крана ${tapName}`,
      visible: screenGuard.visible,
      guarded: true,
      reason: screenGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'keg',
      title: 'Кега',
      description: kegGuard.allowed
        ? 'Перейти к действиям по кеге и напитку на этом кране.'
        : (kegGuard.reason || 'Действия по кеге сейчас недоступны.'),
      disabled: kegGuard.disabled,
    }), {
      event: 'open-detail',
      ariaLabel: `Открыть карточку крана ${tapName} для работы с кегой`,
      visible: kegGuard.visible,
      guarded: true,
      reason: kegGuard.reason,
    }),
    withMeta(createQuickActionDescriptor({
      id: 'history',
      title: 'История',
      description: 'Открыть сессии и последние события по этому крану.',
    }), {
      event: 'open-history',
      ariaLabel: `Открыть историю по крану ${tapName}`,
      visible: Boolean(tap?.tap_id),
      guarded: false,
    }),
  ], TAP_QUICK_ACTION_ORDER).filter((action) => action.visible);
}
