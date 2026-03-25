import { createQuickActionDescriptor, orderQuickActionDescriptors } from '../../operator/quickActionDescriptors.js';

function withReason(descriptor, reason) {
  return {
    ...descriptor,
    reason,
  };
}

export function buildQuickActions({ lookup, actionGuards }) {
  const guards = actionGuards || {};

  return orderQuickActionDescriptors([
    withReason(createQuickActionDescriptor({
      id: 'top-up',
      title: 'Top up',
      description: guards.topUp?.disabled
        ? (guards.topUp.reason || 'Top-up is unavailable right now.')
        : 'Quickly add funds after checking the card and guest context.',
      disabled: Boolean(guards.topUp?.disabled),
    }), guards.topUp?.reason),
    withReason(createQuickActionDescriptor({
      id: 'toggle-block',
      title: guards.toggleBlock?.isActive ? 'Block' : 'Unblock',
      description: guards.toggleBlock?.disabled
        ? (guards.toggleBlock.reason || 'Block status is unavailable right now.')
        : 'Change guest active status from the operator workflow.',
      disabled: Boolean(guards.toggleBlock?.disabled),
    }), guards.toggleBlock?.reason),
    withReason(createQuickActionDescriptor({
      id: 'reissue',
      title: lookup?.is_lost ? 'Restore / reissue' : 'Mark lost / reissue',
      description: guards.reissue?.disabled
        ? (guards.reissue.reason || 'Reissue flow is unavailable right now.')
        : 'Continue the lost-card or reissue workflow without leaving the operator context.',
      disabled: Boolean(guards.reissue?.disabled),
      tone: lookup?.is_lost ? 'danger' : 'neutral',
    }), guards.reissue?.reason),
    withReason(createQuickActionDescriptor({
      id: 'open-history',
      title: 'History',
      description: guards.openHistory?.disabled
        ? (guards.openHistory.reason || 'History is unavailable right now.')
        : 'Open the card and guest history to explain the latest event.',
      disabled: Boolean(guards.openHistory?.disabled),
    }), guards.openHistory?.reason),
    withReason(createQuickActionDescriptor({
      id: 'open-visit',
      title: 'Active session',
      description: guards.openVisit?.disabled
        ? (guards.openVisit.reason || 'Active session is unavailable right now.')
        : 'Jump straight into the active session linked to this card.',
      disabled: Boolean(guards.openVisit?.disabled),
    }), guards.openVisit?.reason),
  ], ['top-up', 'toggle-block', 'reissue', 'open-history', 'open-visit']);
}
