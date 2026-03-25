import { guestStore } from './guestStore.js';
import { incidentStore } from './incidentStore.js';
import { shiftStore } from './shiftStore.js';
import { systemStore } from './systemStore.js';
import { tapStore } from './tapStore.js';
import { visitStore } from './visitStore.js';

export const OPERATOR_SHELL_SHARED_DATA = Object.freeze([
  'taps',
  'active_visits',
  'current_shift',
  'system_health',
]);

export const OPERATOR_SHELL_REFETCH_POLICY = Object.freeze({
  mandatoryReasons: ['manual-refresh', 'incident-action', 'shift-open-close'],
  defaultReason: 'route-enter',
});

function mustForceRefetch(reason) {
  return OPERATOR_SHELL_REFETCH_POLICY.mandatoryReasons.includes(reason);
}

export async function ensureOperatorShellData({ reason = OPERATOR_SHELL_REFETCH_POLICY.defaultReason, force = false } = {}) {
  const shouldForce = force || mustForceRefetch(reason);
  return Promise.allSettled([
    tapStore.fetchTaps({ force: shouldForce }),
    visitStore.fetchActiveVisits({ force: shouldForce }),
    shiftStore.fetchCurrent({ force: shouldForce }),
    systemStore.fetchSystemStatus({ force: shouldForce }),
  ]);
}

export async function ensureCardsGuestsData({ reason = OPERATOR_SHELL_REFETCH_POLICY.defaultReason, force = false } = {}) {
  const shouldForce = force || mustForceRefetch(reason);
  return Promise.allSettled([
    guestStore.fetchGuests({ force: shouldForce }),
    visitStore.fetchActiveVisits({ force: shouldForce }),
  ]);
}

export async function ensureIncidentsData({ reason = OPERATOR_SHELL_REFETCH_POLICY.defaultReason, force = false } = {}) {
  const shouldForce = force || mustForceRefetch(reason);
  return Promise.allSettled([
    incidentStore.fetchIncidents({ force: shouldForce }),
    tapStore.fetchTaps({ force: shouldForce }),
    visitStore.fetchActiveVisits({ force: shouldForce }),
    systemStore.fetchSystemStatus({ force: shouldForce }),
  ]);
}
