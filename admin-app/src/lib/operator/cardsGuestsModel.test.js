import test from 'node:test';
import assert from 'node:assert/strict';

import { buildCardsGuestsViewModel, resolveScenarioActionHandler } from './cardsGuestsModel.js';

test('buildCardsGuestsViewModel selects guest by selectedLookup fallback and limits pours', () => {
  const model = buildCardsGuestsViewModel({
    guests: [{ guest_id: 10, first_name: 'Ivan', last_name: 'Petrov', phone_number: '+79990000000', cards: [{ card_uid: 'uid-1' }] }],
    activeVisits: [{ visit_id: 'v-1', guest_id: 10 }],
    pours: [
      { id: 1, guest: { guest_id: 10 }, tap: { display_name: 'A' } },
      { id: 2, guest: { guest_id: 10 }, tap: { display_name: 'B' } },
      { id: 3, guest: { guest_id: 10 }, tap: { display_name: 'C' } },
      { id: 4, guest: { guest_id: 10 }, tap: { display_name: 'D' } },
      { id: 5, guest: { guest_id: 10 }, tap: { display_name: 'E' } },
      { id: 6, guest: { guest_id: 10 }, tap: { display_name: 'F' } },
      { id: 7, guest: { guest_id: 10 }, tap: { display_name: 'G' } },
    ],
    phoneQuery: '',
    selectedGuestId: null,
    selectedLookup: { guest: { guest_id: 10 } },
    permissions: { canTopUp: false, canToggleBlock: false, canReissue: false, canOpenVisit: true, canViewHistory: true },
  });

  assert.equal(model.selectedGuest?.guest_id, 10);
  assert.equal(model.selectedVisit?.visit_id, 'v-1');
  assert.equal(model.recentGuestPours.length, 6);
  assert.equal(model.lastTapLabel, 'A');
});

test('resolveScenarioActionHandler maps action routing branches', () => {
  assert.equal(resolveScenarioActionHandler('top-up'), 'open-top-up');
  assert.equal(resolveScenarioActionHandler('open-history'), 'open-history');
  assert.equal(resolveScenarioActionHandler('toggle-block'), 'toggle-block');
  assert.equal(resolveScenarioActionHandler('reissue'), 'reissue');
  assert.equal(resolveScenarioActionHandler('unknown'), 'none');
});
