<script>
  import { onDestroy, onMount } from 'svelte';

  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';
  import { operatorConnectionStore } from '../../stores/operatorConnectionStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { systemStore } from '../../stores/systemStore.js';
  import { tapStore } from '../../stores/tapStore.js';
  import { formatHealthPill, healthTone } from '../../lib/healthStatus.js';
  import { SHELL_COPY } from '../../lib/operatorLabels.js';

  export let showHealth = true;
  export let showOperational = true;

  let online = typeof navigator !== 'undefined' ? navigator.onLine : true;

  const warningStates = ['warning', 'degraded', 'unknown'];
  const errorStates = ['critical', 'error', 'offline'];

  function updateOnline() {
    online = navigator.onLine;
  }

  function nfcStateLabel(status) {
    if (status === 'ok') return 'Ready';
    if (status === 'recovering') return 'Recovering';
    if (status === 'disconnected') return 'Disconnected';
    if (status === 'scanning' || status === 'initializing') return 'Connecting';
    return 'Error';
  }

  function syncIndicator(summary = {}) {
    const unsynced = Number(summary.unsyncedFlowCount || 0);
    const offlineCount = Number(summary.readerOfflineCount || 0)
      + Number(summary.displayOfflineCount || 0)
      + Number(summary.controllerOfflineCount || 0);

    if (unsynced > 0) {
      return {
        text: SHELL_COPY.syncUnsynced(unsynced),
        tone: 'warn',
        title: SHELL_COPY.syncUnsyncedTitle,
      };
    }

    if (offlineCount > 0) {
      return {
        text: SHELL_COPY.syncOfflineQueue(offlineCount),
        tone: 'warn',
        title: SHELL_COPY.syncOfflineTitle,
      };
    }

    return {
      text: SHELL_COPY.syncClean,
      tone: 'ok',
      title: SHELL_COPY.syncCleanTitle,
    };
  }

  function connectionIndicator(connection = {}) {
    if (connection.mode === 'offline') {
      return {
        text: 'Backend: Offline',
        tone: 'error',
      title: connection.reason || 'Backend connection is lost and risky actions are blocked.',
      };
    }

    if (connection.mode !== 'online') {
      return {
        text: `Backend: ${connection.transport === 'websocket' ? 'Degraded' : 'Read-only'}`,
        tone: 'warn',
        title: connection.reason || 'Backend is currently in degraded mode.',
      };
    }

    if (connection.transport !== 'websocket') {
      return {
        text: connection.transport === 'short_polling' ? 'Realtime: Polling' : 'Realtime: Reduced',
        tone: 'warn',
        title: connection.reason || 'Realtime временно переведён на polling.',
      };
    }

    return {
      text: 'Realtime: Live',
      tone: 'ok',
      title: 'Data is updating over websocket.',
    };
  }

  onMount(() => {
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
  });

  onDestroy(() => {
    window.removeEventListener('online', updateOnline);
    window.removeEventListener('offline', updateOnline);
  });

  $: primaryHealthPills = $systemStore.health.primaryPills || [];
  $: syncPill = syncIndicator($tapStore.summary || {});
  $: connectionPill = connectionIndicator($operatorConnectionStore || {});
  $: nfcLabel = nfcStateLabel($nfcReaderStore.status);
</script>

<div class="pill-groups">
  {#if showOperational}
    <div class="pills secondary" aria-label="Operational workstation statuses">
      <span class="pill secondary-pill" class:ok={$shiftStore.isOpen} class:warn={!$shiftStore.isOpen}>
        Shift: {$shiftStore.isOpen ? 'Open' : 'Closed'}
      </span>
      <span class="pill secondary-pill" class:ok={online} class:error={!online}>
        Network: {online ? 'Online' : 'Offline'}
      </span>
      <span class="pill secondary-pill" class:ok={connectionPill.tone === 'ok'} class:warn={connectionPill.tone === 'warn'} class:error={connectionPill.tone === 'error'} title={connectionPill.title}>
        {connectionPill.text}
      </span>
      <span
        class="pill secondary-pill"
        class:ok={$nfcReaderStore.status === 'ok'}
        class:warn={$nfcReaderStore.status === 'recovering' || $nfcReaderStore.status === 'disconnected' || $nfcReaderStore.status === 'scanning' || $nfcReaderStore.status === 'initializing'}
        class:error={$nfcReaderStore.status === 'error'}
        title={$nfcReaderStore.message || $nfcReaderStore.error || 'NFC reader status'}
      >
        NFC: {nfcLabel}
      </span>
      <span class="pill secondary-pill" class:ok={syncPill.tone === 'ok'} class:warn={syncPill.tone === 'warn'} title={syncPill.title}>
        {syncPill.text}
      </span>
    </div>
  {/if}

  {#if showHealth}
    <div class="pills primary" aria-label="Key subsystem statuses">
      {#each primaryHealthPills as item (item.key)}
        <span class="pill" class:ok={healthTone(item.state) === 'ok'} class:warn={warningStates.includes(item.state)} class:error={errorStates.includes(item.state)} title={item.detail}>
          {formatHealthPill(item)}
        </span>
      {/each}
    </div>
  {/if}
</div>

<style>
  .pill-groups { display: grid; gap: 8px; }
  .pills { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .pill {
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 0.78rem;
    background: #eef2f8;
    color: #29405f;
    border: 1px solid #d7e2f1;
    line-height: 1.3;
  }
  .secondary .pill { opacity: 0.96; }
  .secondary-pill { background: #f8fafc; color: #475569; border-color: #e2e8f0; }
  .pill.ok { background: #e9f8ef; border-color: #bde8cc; color: #116d3a; }
  .pill.warn { background: #fff8e9; border-color: #ffe1a3; color: #8d5b00; }
  .pill.error { background: #ffeef0; border-color: #ffc6cc; color: #9e1f2c; }
</style>
