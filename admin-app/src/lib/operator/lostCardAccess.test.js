import test from 'node:test';
import assert from 'node:assert/strict';

import { buildLostCardAccess, canManageLostCards, canViewLostCards } from './lostCardAccess.js';

test('canViewLostCards allows lookup-capable roles to open the screen', () => {
  assert.equal(canViewLostCards({ cards_lookup: true }), true);
  assert.equal(canViewLostCards({ cards_lookup: false, cards_reissue_manage: true }), true);
  assert.equal(canViewLostCards({ cards_lookup: false, cards_reissue_manage: false }), false);
});

test('canManageLostCards requires reissue permission for restore actions', () => {
  assert.equal(canManageLostCards({ cards_reissue_manage: true }), true);
  assert.equal(canManageLostCards({ cards_lookup: true, cards_reissue_manage: false }), false);
});

test('buildLostCardAccess returns screen and mutation capabilities from one source', () => {
  assert.deepEqual(
    buildLostCardAccess({ cards_lookup: true, cards_reissue_manage: false }),
    {
      canView: true,
      canManage: false,
    },
  );
});
