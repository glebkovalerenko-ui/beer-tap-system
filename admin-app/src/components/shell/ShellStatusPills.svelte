<script>
  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { onMount, onDestroy } from 'svelte';

  let online = typeof navigator !== 'undefined' ? navigator.onLine : true;

  const updateOnline = () => {
    online = navigator.onLine;
  };

  onMount(() => {
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
  });

  onDestroy(() => {
    window.removeEventListener('online', updateOnline);
    window.removeEventListener('offline', updateOnline);
  });
</script>

<div class="pills">
  <span class="pill" class:ok={$shiftStore.isOpen} class:warn={!$shiftStore.isOpen}>Смена: {$shiftStore.isOpen ? 'Открыта' : 'Закрыта'}</span>
  <span class="pill" class:ok={online} class:error={!online}>Сеть: {online ? 'Online' : 'Offline'}</span>
  <span class="pill" class:ok={$nfcReaderStore.status === 'ok'} class:error={$nfcReaderStore.status === 'error'}>NFC: {$nfcReaderStore.status === 'ok' ? 'Готов' : 'Ошибка'}</span>
</div>

<style>
  .pills { display: flex; gap: 8px; align-items: center; }
  .pill {
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 0.78rem;
    background: #eef2f8;
    color: #29405f;
    border: 1px solid #d7e2f1;
  }
  .pill.ok { background: #e9f8ef; border-color: #bde8cc; color: #116d3a; }
  .pill.warn { background: #fff8e9; border-color: #ffe1a3; color: #8d5b00; }
  .pill.error { background: #ffeef0; border-color: #ffc6cc; color: #9e1f2c; }
</style>
