<script>
  export let demoMode = false;
  import { onDestroy, onMount } from 'svelte';
  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';

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
  $: hasWarning = demoMode || !online || nfcHasWarning;
</script>

{#if hasWarning}
  <section class="banner" class:error={!online || nfcStatus === 'error'}>
    {#if demoMode}
      <strong>Демо-режим:</strong> часть данных может быть тестовой для стабильного показа.
    {/if}

    {#if !online}
      <span>Сеть недоступна. Используйте действия, не требующие онлайн-подтверждения.</span>
    {/if}

    {#if nfcStatus === 'disconnected'}
      <span>NFC-считыватель отключен. Подключите устройство, приложение подхватит его автоматически.</span>
    {/if}

    {#if nfcStatus === 'recovering'}
      <span>NFC восстанавливается после потери подключения. Перезапуск приложения не требуется.</span>
    {/if}

    {#if nfcStatus === 'error'}
      <span>NFC недоступен из-за ошибки runtime. Проверьте лог Admin App и состояние PC/SC.</span>
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
