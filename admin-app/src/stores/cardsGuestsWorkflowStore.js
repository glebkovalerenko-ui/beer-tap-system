import { writable } from 'svelte/store';

function derivePermissions(permissions = {}) {
  return {
    canAccessCardsGuests: Boolean(permissions.cards_lookup),
    canOpenVisit: Boolean(permissions.cards_open_active_session),
    canViewHistory: Boolean(permissions.cards_history_view),
    canTopUp: Boolean(permissions.cards_top_up),
    canToggleBlock: Boolean(permissions.cards_block_manage),
    canReissue: Boolean(permissions.cards_reissue_manage),
  };
}

function createCardsGuestsWorkflowStore() {
  const { subscribe, update } = writable({
    pendingScenario: '',
    selectedLookup: null,
    selectedGuestId: null,
    reissueStatus: '',
    permissions: derivePermissions(),
    permissionStamp: '',
  });

  return {
    subscribe,
    setPermissions(rawPermissions = {}) {
      const nextStamp = JSON.stringify(rawPermissions || {});
      update((state) => {
        if (state.permissionStamp === nextStamp) return state;
        return { ...state, permissions: derivePermissions(rawPermissions), permissionStamp: nextStamp };
      });
    },
    setPendingScenario(pendingScenario = '') {
      update((state) => ({ ...state, pendingScenario }));
    },
    setSelectedLookup(selectedLookup = null) {
      update((state) => ({ ...state, selectedLookup }));
    },
    setSelectedGuestId(selectedGuestId = null) {
      update((state) => ({ ...state, selectedGuestId }));
    },
    setReissueStatus(reissueStatus = '') {
      update((state) => ({ ...state, reissueStatus }));
    },
    resetWorkflow() {
      update((state) => ({
        ...state,
        pendingScenario: '',
        selectedLookup: null,
        selectedGuestId: null,
        reissueStatus: '',
      }));
    },
  };
}

export const cardsGuestsWorkflowStore = createCardsGuestsWorkflowStore();
