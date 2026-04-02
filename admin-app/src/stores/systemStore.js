// @ts-nocheck
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';
import { normalizeSystemActionableStep, normalizeUserFacingBackendText } from '../lib/copyNormalization.js';
import { logError, normalizeError } from '../lib/errorUtils';
import { notifyForbiddenIfNeeded } from '../lib/forbidden.js';

function toErrorMessage(context, error) {
  logError(context, error);
  return normalizeError(error);
}

function findSubsystem(subsystems, names) {
  return (subsystems || []).find((item) => names.includes(item.name));
}

function normalizeSubsystemHealth(item, fallbackLabel) {
  return {
    name: item?.name || fallbackLabel.toLowerCase(),
    label: fallbackLabel,
    state: item?.state || 'unknown',
    detail: normalizeUserFacingBackendText(item?.detail || item?.state || 'Нет данных', item?.detail || item?.state || 'Нет данных'),
    devices: (item?.devices || []).map((device) => ({
      ...device,
      label: normalizeUserFacingBackendText(device?.label || '', device?.label || ''),
      detail: normalizeUserFacingBackendText(device?.detail || '', device?.detail || ''),
    })),
  };
}

function summarizeDevices(devices = [], fallbackLabel = 'устройств') {
  const problemDevices = devices.filter((device) => ['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes(device.state));
  if (!devices.length) return `Нет данных по ${fallbackLabel}`;
  if (!problemDevices.length) return `В работе: ${devices.length}`;
  return `Требуют внимания: ${problemDevices.length} из ${devices.length}`;
}

function deriveHealthSummary(summary, error = null) {
  const subsystems = summary?.subsystems || [];
  const backend = error
    ? { name: 'backend', label: 'Центральный контур', state: 'critical', detail: error, devices: [] }
    : normalizeSubsystemHealth(findSubsystem(subsystems, ['backend', 'api', 'server']), 'Центральный контур');
  const controllers = normalizeSubsystemHealth(findSubsystem(subsystems, ['controller', 'controllers']), 'Контроллеры');
  const displays = normalizeSubsystemHealth(findSubsystem(subsystems, ['display-agent', 'display_agent', 'display', 'displays']), 'Экраны');
  const readers = normalizeSubsystemHealth(findSubsystem(subsystems, ['reader', 'readers', 'nfc', 'nfc-reader', 'nfc_reader']), 'Считыватели');
  const sync = normalizeSubsystemHealth(findSubsystem(subsystems, ['sync', 'sync-service', 'sync_queue', 'queue']), 'Синхронизация');

  const primary = [backend, controllers, displays, readers, sync];
  const states = primary.map((item) => item.state);
  const overall = states.includes('critical') || states.includes('error')
    ? 'critical'
    : states.includes('warning') || states.includes('degraded') || states.includes('unknown') || states.includes('offline')
      ? 'warning'
      : 'ok';

  const primaryPills = [
    { key: 'backend', label: 'Центральный контур', state: backend.state, detail: backend.detail },
    { key: 'controllers', label: 'Контроллеры', state: controllers.state, detail: controllers.detail },
    { key: 'displays', label: 'Экраны', state: displays.state, detail: displays.detail },
    { key: 'readers', label: 'Считыватели', state: readers.state, detail: readers.detail },
    { key: 'sync', label: 'Синхронизация', state: sync.state, detail: sync.detail },
  ];

  const problemSubsystems = primary.filter((item) => ['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes(item.state));
  const problemDevices = subsystems.flatMap((subsystem) => (subsystem.devices || [])
    .filter((device) => ['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'].includes(device.state))
    .map((device) => ({
      ...device,
      subsystem: subsystem.label || subsystem.name,
    })));

  return {
    backend,
    controller: controllers,
    controllers,
    displayAgent: displays,
    displays,
    readers,
    sync,
    overall,
    primaryPills,
    sections: {
      overallStatus: {
        title: 'Общий статус',
        items: [backend, sync],
      },
      devices: {
        title: 'Устройства',
        items: [controllers, displays, readers],
        summary: [
          { key: 'controllers', label: 'Контроллеры', value: summarizeDevices(controllers.devices, 'контроллерам') },
          { key: 'displays', label: 'Экраны', value: summarizeDevices(displays.devices, 'экранам') },
          { key: 'readers', label: 'Считыватели', value: summarizeDevices(readers.devices, 'считывателям') },
        ],
      },
      syncStatus: {
        title: 'Синхронизация',
        items: [sync],
      },
      accumulatedIssues: {
        title: 'Накопившиеся проблемы',
        subsystemCount: problemSubsystems.length,
        deviceCount: problemDevices.length,
        subsystems: problemSubsystems,
        devices: problemDevices,
      },
    },
  };
}

const createSystemStore = () => {
  const { subscribe, update } = writable({
    emergencyStop: false,
    overallState: 'ok',
    generatedAt: null,
    openIncidentCount: 0,
    subsystems: [],
    health: deriveHealthSummary(null),
    mode: 'online',
    reason: null,
    queueSummary: null,
    staleSummary: null,
    blockedActions: {},
    actionableNextSteps: [],
    loading: false,
    isLoading: false,
    lastFetchedAt: null,
    staleTtlMs: 10000,
    error: null,
  });

  let pollingInterval = null;
  let systemStatusInFlight = null;
  const POLLING_RATE_MS = 10000;

  const applySummary = (summary) => update((store) => ({
    ...store,
    emergencyStop: Boolean(summary?.emergency_stop),
    overallState: summary?.overall_state || 'ok',
    generatedAt: summary?.generated_at || null,
    openIncidentCount: summary?.open_incident_count || 0,
    subsystems: summary?.subsystems || [],
    health: deriveHealthSummary(summary),
    mode: summary?.mode || 'online',
    reason: normalizeUserFacingBackendText(summary?.reason || null, null),
    queueSummary: summary?.queue_summary || null,
    staleSummary: summary?.stale_summary || null,
    blockedActions: summary?.blocked_actions || {},
    actionableNextSteps: (summary?.actionable_next_steps || []).map((step) => normalizeSystemActionableStep(step)),
    loading: false,
    isLoading: false,
    lastFetchedAt: Date.now(),
    error: null,
  }));

  const fetchSystemStatus = async ({ force = false, staleTtlMs = null } = {}) => {
    const token = get(sessionStore).token;
    if (!token) return;
    const state = get({ subscribe });
    const ttlMs = Number.isFinite(staleTtlMs) ? Number(staleTtlMs) : state.staleTtlMs;
    const hasFreshData = state.lastFetchedAt && (Date.now() - state.lastFetchedAt) < ttlMs;
    if (!force && hasFreshData && state.generatedAt) {
      return state;
    }
    if (systemStatusInFlight) {
      return systemStatusInFlight;
    }

    update((store) => ({ ...store, loading: true, isLoading: true }));
    try {
      systemStatusInFlight = invoke('get_operator_system_status', { token });
      const summary = await systemStatusInFlight;
      applySummary(summary);
      return summary;
    } catch (err) {
      const message = toErrorMessage('systemStore.fetchSystemStatus', err);
      update((store) => ({
        ...store,
        health: deriveHealthSummary({ subsystems: store.subsystems }, message),
        mode: 'backend_degraded',
        reason: message,
        loading: false,
        isLoading: false,
        error: message,
      }));
      return null;
    } finally {
      systemStatusInFlight = null;
    }
  };

  const setEmergencyStop = async (enabled) => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Требуется повторный вход в систему');
    update((store) => ({ ...store, loading: true, isLoading: true }));
    try {
      const summary = await invoke('set_emergency_stop', { token, value: enabled ? 'true' : 'false' });
      applySummary(summary);
    } catch (err) {
      notifyForbiddenIfNeeded(err);
      const message = toErrorMessage('systemStore.setEmergencyStop', err);
      update((store) => ({ ...store, loading: false, isLoading: false, error: message }));
      throw new Error(message);
    }
  };

  const startPolling = () => {
    if (pollingInterval) return;
    fetchSystemStatus();
    pollingInterval = setInterval(fetchSystemStatus, POLLING_RATE_MS);
  };

  const stopPolling = () => {
    if (!pollingInterval) return;
    clearInterval(pollingInterval);
    pollingInterval = null;
  };

  return { subscribe, setEmergencyStop, startPolling, stopPolling, fetchSystemStatus };
};

export const systemStore = createSystemStore();
