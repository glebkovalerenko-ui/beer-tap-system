<script>
  import { onDestroy, onMount } from 'svelte';

  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';
  import { operatorConnectionStore } from '../../stores/operatorConnectionStore.js';
  import { systemStore } from '../../stores/systemStore.js';

  export let demoMode = false;
  export let online = typeof navigator !== 'undefined' ? navigator.onLine : true;
  export let nfcStatus = 'ok';

  function updateOnline() {
    online = navigator.onLine;
  }

  onMount(() => {
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
  });

  onDestroy(() => {
    window.removeEventListener('online', updateOnline);
    window.removeEventListener('offline', updateOnline);
  });

  $: nfcStatus = $nfcReaderStore.status;
  $: nfcHasWarning = nfcStatus === 'error' || nfcStatus === 'disconnected' || nfcStatus === 'recovering';
  $: operatorBackendWarning = $operatorConnectionStore.mode !== 'online' || $operatorConnectionStore.transport !== 'websocket';
  $: hasWarning = demoMode || !online || nfcHasWarning || operatorBackendWarning;
</script>

{#if hasWarning}
  <section class="banner" class:error={!online || nfcStatus === 'error' || $operatorConnectionStore.mode === 'offline'}>
    {#if demoMode}
      <strong>Demo mode:</strong> part of the data may be test data for a stable presentation.
    {/if}

    {#if !online}
      <span>Network is unavailable. Use only actions that do not require online confirmation.</span>
    {/if}

    {#if $operatorConnectionStore.mode !== 'online'}
      <span>
        Backend: {$operatorConnectionStore.mode === 'offline' ? 'offline' : 'degraded'}.
        {$operatorConnectionStore.reason || $systemStore.reason || 'Опасные действия временно переведены в read-only.'}
      </span>
    {/if}

    {#if $operatorConnectionStore.transport !== 'websocket' && $operatorConnectionStore.mode === 'online'}
      <span>Realtime переключён на {$operatorConnectionStore.transport === 'short_polling' ? 'short polling' : 'reduced polling'} до восстановления websocket.</span>
    {/if}

    {#if nfcStatus === 'disconnected'}
      <span>NFC reader is disconnected. Reconnect the device and the app will pick it up automatically.</span>
    {/if}

    {#if nfcStatus === 'recovering'}
      <span>NFC is recovering after a disconnect. App restart is not required.</span>
    {/if}

    {#if nfcStatus === 'error'}
      <span>NFC is unavailable because of a runtime error. Check the Admin App logs and PC/SC state.</span>
    {/if}
  </section>
{/if}

<style>
  .banner {
    margin: 0 12px;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid #c8ddff;
    background: #f1f7ff;
    color: #1f4f8f;
    display: flex;
    flex-wrap: wrap;
    gap: 8px 12px;
    font-size: 0.88rem;
  }

  .banner.error {
    border-color: #ffc9cf;
    background: #fff2f4;
    color: #8c1c2a;
  }
</style>
