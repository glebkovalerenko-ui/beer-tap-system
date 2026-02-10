<!-- src/components/system/NfcReaderStatus.svelte -->
<script>
  import { nfcReaderStore } from '../../stores/nfcReaderStore.js';
</script>

<div class="status-widget">
  <div class="header">
    <h4>NFC считыватель</h4>
  </div>
  <div class="body">
    {#if $nfcReaderStore.status === 'initializing'}
      <p>Инициализация...</p>
    {:else if $nfcReaderStore.status === 'ok'}
      <div class="status-indicator ok"></div>
      <div class="info">
        <span class="status-text">Подключено</span>
        <span class="detail">Считыватель: {$nfcReaderStore.readerName || 'ACR122U'}</span>
      </div>
    {:else if $nfcReaderStore.status === 'error'}
      <div class="status-indicator error"></div>
       <div class="info">
        <span class="status-text error-text">Ошибка</span>
        <span class="detail error-detail">{$nfcReaderStore.error}</span>
      </div>
    {/if}
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
  }
  .status-indicator.ok {
    background-color: #28a745;
    box-shadow: 0 0 10px rgba(40, 167, 69, 0.5);
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