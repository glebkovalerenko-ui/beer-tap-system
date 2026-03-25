const ROLE_LABELS = Object.freeze({
  operator: 'Оператор',
  shift_lead: 'Старший смены',
  engineer_owner: 'Инженер / владелец',
});

const FRONT_PERMISSION_KEYS = Object.freeze([
  'taps_view',
  'taps_control',
  'sessions_view',
  'cards_lookup',
  'cards_open_active_session',
  'cards_history_view',
  'cards_top_up',
  'cards_block_manage',
  'cards_reissue_manage',
  'incidents_view',
  'incidents_manage',
  'inventory_view',
  'kegs_manage',
  'beverages_catalog_manage',
  'system_health_view',
  'system_engineering_actions',
  'maintenance_actions',
  'display_override',
  'settings_manage',
  'debug_tools',
  'role_switch',
]);

function normalizePermissions(claims) {
  if (Array.isArray(claims?.permissions)) {
    return new Set(claims.permissions.filter(Boolean).map((item) => String(item).trim()));
  }

  if (claims?.permissions && typeof claims.permissions === 'object') {
    return new Set(Object.entries(claims.permissions)
      .filter(([, enabled]) => Boolean(enabled))
      .map(([key]) => key));
  }

  return new Set();
}

export function mapBackendClaimsToFrontendPermissions(claims = {}) {
  const active = normalizePermissions(claims);
  return FRONT_PERMISSION_KEYS.reduce((acc, key) => {
    acc[key] = active.has(key);
    return acc;
  }, {});
}

export function mapBackendClaimsToRoleState(claims = {}) {
  const roleKey = String(claims.role || 'operator').trim() || 'operator';
  return {
    key: roleKey,
    label: ROLE_LABELS[roleKey] || roleKey,
    permissions: mapBackendClaimsToFrontendPermissions(claims),
    profile: {
      username: claims.username || null,
      full_name: claims.full_name || null,
      role: roleKey,
      permissions: Array.from(normalizePermissions(claims)),
    },
  };
}

export function decodeJwtClaims(token) {
  if (!token || typeof token !== 'string') {
    return null;
  }

  const parts = token.split('.');
  if (parts.length < 2) {
    return null;
  }

  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(atob(base64)
      .split('')
      .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`)
      .join(''));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export { FRONT_PERMISSION_KEYS };
