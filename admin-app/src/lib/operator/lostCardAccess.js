export function canViewLostCards(permissions = {}) {
  return Boolean(permissions.cards_lookup || permissions.cards_reissue_manage);
}

export function canManageLostCards(permissions = {}) {
  return Boolean(permissions.cards_reissue_manage);
}

export function buildLostCardAccess(permissions = {}) {
  return {
    canView: canViewLostCards(permissions),
    canManage: canManageLostCards(permissions),
  };
}
