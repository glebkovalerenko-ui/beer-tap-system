<script>
  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';

  $: isReady = $nfcReaderStore.status === 'ok';
  $: isWarning =
    $nfcReaderStore.status === 'initializing' ||
    $nfcReaderStore.status === 'scanning' ||
    $nfcReaderStore.status === 'disconnected' ||
    $nfcReaderStore.status === 'recovering';
</script>

<div class="status-widget">
  <div class="header">
    <h4>Считыватель NFC</h4>
  </div>
  <div class="body">
    <div class="status-indicator" class:ok={isReady} class:warn={isWarning} class:error={$nfcReaderStore.status === 'error'}></div>

    <div class="info">
      {#if $nfcReaderStore.status === 'initializing'}
        <span class="status-text">Инициализация</span>
        <span class="detail">Запускаем NFC-подсистему...</span>
      {:else if $nfcReaderStore.status === 'scanning'}
        <span class="status-text warn-text">Поиск считывателя</span>
        <span class="detail">{$nfcReaderStore.message || 'Идет поиск NFC-считывателя.'}</span>
      {:else if $nfcReaderStore.status === 'disconnected'}
        <span class="status-text warn-text">Считыватель отключен</span>
        <span class="detail">{$nfcReaderStore.message || 'Подключите NFC-считыватель.'}</span>
      {:else if $nfcReaderStore.status === 'recovering'}
        <span class="status-text warn-text">Восстановление</span>
        <span class="detail">{$nfcReaderStore.message || 'Пытаемся восстановить подключение к NFC.'}</span>
      {:else if $nfcReaderStore.status === 'ok'}
        <span class="status-text">Подключено</span>
        <span class="detail">Считыватель: {$nfcReaderStore.readerName || 'ACR122U'}</span>
      {:else}
        <span class="status-text error-text">Ошибка</span>
        <span class="detail error-detail">{$nfcReaderStore.error || $nfcReaderStore.message}</span>
      {/if}
    </div>
  </div>
</div>

<style>
  .status-widget {
    border: 1px solid #eee;
    border-radius: 8px;
    background-color: #fff;
  }
  .header {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #eee;
  }
  .header h4 {
    margin: 0;
    font-size: 1.1rem;
  }
  .body {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
  }
  .status-indicator {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background-color: #cfd4db;
  }
  .status-indicator.ok {
    background-color: #28a745;
    box-shadow: 0 0 10px rgba(40, 167, 69, 0.5);
  }
  .status-indicator.warn {
    background-color: #f0ad4e;
    box-shadow: 0 0 10px rgba(240, 173, 78, 0.4);
  }
  .status-indicator.error {
    background-color: #dc3545;
    box-shadow: 0 0 10px rgba(220, 53, 69, 0.5);
  }
  .info {
    display: flex;
    flex-direction: column;
  }
  .status-text {
    font-weight: 600;
    font-size: 1rem;
  }
  .warn-text {
    color: #8d5b00;
  }
  .error-text {
    color: #dc3545;
  }
  .detail {
    font-size: 0.85rem;
    color: #666;
  }
  .error-detail {
    font-weight: 500;
  }
</style>
