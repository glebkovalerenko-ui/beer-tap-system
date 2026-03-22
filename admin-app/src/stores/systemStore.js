// @ts-nocheck
import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { sessionStore } from './sessionStore.js';
import { logError, normalizeError } from '../lib/errorUtils';

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
    label: item?.label || fallbackLabel,
    state: item?.state || 'unknown',
    detail: item?.detail || item?.state || 'Нет данных',
    devices: item?.devices || [],
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
    ? { name: 'backend', label: 'Бэкенд', state: 'critical', detail: error, devices: [] }
    : normalizeSubsystemHealth(findSubsystem(subsystems, ['backend', 'api', 'server']), 'Бэкенд');
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
    { key: 'backend', label: 'Бэкенд', state: backend.state, detail: backend.detail },
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
    loading: false,
    error: null,
  });

  let pollingInterval = null;
  const POLLING_RATE_MS = 10000;

  const applySummary = (summary) => update((store) => ({
    ...store,
    emergencyStop: Boolean(summary?.emergency_stop),
    overallState: summary?.overall_state || 'ok',
    generatedAt: summary?.generated_at || null,
    openIncidentCount: summary?.open_incident_count || 0,
    subsystems: summary?.subsystems || [],
    health: deriveHealthSummary(summary),
    loading: false,
    error: null,
  }));

  const fetchSystemStatus = async () => {
    const token = get(sessionStore).token;
    if (!token) return;
    try {
      const summary = await invoke('get_system_status', { token });
      applySummary(summary);
    } catch (err) {
      const message = toErrorMessage('systemStore.fetchSystemStatus', err);
      update((store) => ({ ...store, health: deriveHealthSummary({ subsystems: store.subsystems }, message), loading: false, error: message }));
    }
  };

  const setEmergencyStop = async (enabled) => {
    const token = get(sessionStore).token;
    if (!token) throw new Error('Требуется повторный вход в систему');
    update((store) => ({ ...store, loading: true }));
    try {
      const summary = await invoke('set_emergency_stop', { token, value: enabled ? 'true' : 'false' });
      applySummary(summary);
    } catch (err) {
      const message = toErrorMessage('systemStore.setEmergencyStop', err);
      update((store) => ({ ...store, loading: false, error: message }));
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
