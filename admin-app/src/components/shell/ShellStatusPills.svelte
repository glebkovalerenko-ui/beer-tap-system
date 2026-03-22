<script>
  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { systemStore } from '../../stores/systemStore.js';
  import { onMount, onDestroy } from 'svelte';

  let online = typeof navigator !== 'undefined' ? navigator.onLine : true;

  const updateOnline = () => {
    online = navigator.onLine;
  };

  $: nfcLabel =
    $nfcReaderStore.status === 'ok'
      ? 'Готов'
      : $nfcReaderStore.status === 'recovering'
        ? 'Восстанавливается'
        : $nfcReaderStore.status === 'disconnected'
          ? 'Отключён'
          : $nfcReaderStore.status === 'scanning' || $nfcReaderStore.status === 'initializing'
            ? 'Подключается'
            : 'Ошибка';

  onMount(() => {
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
  });

  onDestroy(() => {
    window.removeEventListener('online', updateOnline);
    window.removeEventListener('offline', updateOnline);
  });
</script>

<div class="pill-groups">
  <div class="pills primary" aria-label="Ключевые статусы системы">
    {#each $systemStore.health.primaryPills as item (item.key)}
      <span class="pill" class:ok={item.state === 'ok'} class:warn={['warning', 'degraded', 'unknown'].includes(item.state)} class:error={['critical', 'error', 'offline'].includes(item.state)} title={item.detail}>
        {item.label}: {item.state === 'ok' ? 'В норме' : item.detail}
      </span>
    {/each}
  </div>

  <div class="pills secondary" aria-label="Локальные статусы рабочего места">
    <span class="pill secondary-pill" class:ok={$shiftStore.isOpen} class:warn={!$shiftStore.isOpen}>Смена: {$shiftStore.isOpen ? 'Открыта' : 'Закрыта'}</span>
    <span class="pill secondary-pill" class:ok={online} class:error={!online}>Браузер: {online ? 'Онлайн' : 'Офлайн'}</span>
    <span
      class="pill secondary-pill"
      class:ok={$nfcReaderStore.status === 'ok'}
      class:warn={$nfcReaderStore.status === 'recovering' || $nfcReaderStore.status === 'disconnected' || $nfcReaderStore.status === 'scanning' || $nfcReaderStore.status === 'initializing'}
      class:error={$nfcReaderStore.status === 'error'}
    >
      NFC: {nfcLabel}
    </span>
  </div>
</div>

<style>
  .pill-groups { display: grid; gap: 6px; }
  .pills { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .pill {
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 0.78rem;
    background: #eef2f8;
    color: #29405f;
    border: 1px solid #d7e2f1;
  }
  .secondary .pill { opacity: 0.92; }
  .secondary-pill { background: #f8fafc; color: #475569; border-color: #e2e8f0; }
  .pill.ok { background: #e9f8ef; border-color: #bde8cc; color: #116d3a; }
  .pill.warn { background: #fff8e9; border-color: #ffe1a3; color: #8d5b00; }
  .pill.error { background: #ffeef0; border-color: #ffc6cc; color: #9e1f2c; }
</style>
