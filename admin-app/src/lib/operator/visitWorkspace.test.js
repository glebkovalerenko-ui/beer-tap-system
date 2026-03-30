import test from 'node:test';
import assert from 'node:assert/strict';

import { buildVisitLauncherCandidates, resolveVisitFocusTarget } from './visitWorkspace.js';

test('buildVisitLauncherCandidates prioritizes guests with active visits', () => {
  const candidates = buildVisitLauncherCandidates({
    query: 'ив',
    guests: [
      { guest_id: 'guest-1', first_name: 'Иван', last_name: 'Петров', phone_number: '+7999', balance: 500, cards: [{ card_uid: 'CARD-1' }] },
      { guest_id: 'guest-2', first_name: 'Ирина', last_name: 'Иванова', phone_number: '+7888', balance: 250, cards: [] },
    ],
    activeVisits: [
      { visit_id: 'visit-1', guest_id: 'guest-2', active_tap_id: 3 },
    ],
  });

  assert.equal(candidates.length, 2);
  assert.equal(candidates[0].guestId, 'guest-2');
  assert.equal(candidates[0].actionLabel, 'Продолжить визит');
  assert.equal(candidates[1].actionLabel, 'Открыть визит');
});

test('buildVisitLauncherCandidates requires enough query context', () => {
  assert.deepEqual(buildVisitLauncherCandidates({ query: 'и', guests: [{ guest_id: 'guest-1' }] }), []);
});

test('resolveVisitFocusTarget returns the matching visit from the current workspace list', () => {
  const target = resolveVisitFocusTarget(
    [
      { visit_id: 'visit-1', guest_full_name: 'Первый' },
      { visit_id: 'visit-2', guest_full_name: 'Второй' },
    ],
    'visit-2',
  );

  assert.deepEqual(target, { visit_id: 'visit-2', guest_full_name: 'Второй' });
});
