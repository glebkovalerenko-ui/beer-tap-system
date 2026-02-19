export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export const DEMO_MODE_ENABLED_BY_DEFAULT = String(import.meta.env.VITE_DEMO_MODE || '').toLowerCase() === 'true';
