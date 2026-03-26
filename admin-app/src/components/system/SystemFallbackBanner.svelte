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
      <strong>Демо-режим:</strong> часть данных может быть тестовой для стабильного показа.
    {/if}

    {#if !online}
      <span>Сеть недоступна. Выполняйте только те действия, которым не нужно онлайн-подтверждение.</span>
    {/if}

    {#if $operatorConnectionStore.mode !== 'online'}
      <span>
        Backend {$operatorConnectionStore.mode === 'offline' ? 'недоступен' : 'работает нестабильно'}.
        {$operatorConnectionStore.reason || $systemStore.reason || 'Опасные действия временно доступны только для просмотра.'}
      </span>
    {/if}

    {#if $operatorConnectionStore.transport !== 'websocket' && $operatorConnectionStore.mode === 'online'}
      <span>Обновление данных переключено на {$operatorConnectionStore.transport === 'short_polling' ? 'повторную синхронизацию' : 'редкую синхронизацию'} до восстановления websocket.</span>
    {/if}

    {#if nfcStatus === 'disconnected'}
      <span>NFC-считыватель отключён. Подключите устройство, и приложение подхватит его автоматически.</span>
    {/if}

    {#if nfcStatus === 'recovering'}
      <span>NFC-считыватель восстанавливает связь после отключения. Перезапуск приложения не нужен.</span>
    {/if}

    {#if nfcStatus === 'error'}
      <span>NFC-считыватель недоступен из-за ошибки среды. Проверьте журнал Admin App и состояние PC/SC.</span>
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
