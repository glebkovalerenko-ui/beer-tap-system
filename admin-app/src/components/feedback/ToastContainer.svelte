<script>
  import { uiStore } from '../../stores/uiStore.js';

  function closeToast(id) {
    uiStore.dismissToast(id);
  }
</script>

<div class="toast-container" aria-live="polite" aria-atomic="true">
  {#each $uiStore.toasts as toast (toast.id)}
    <div class="toast {toast.type}">
      <span>{toast.message}</span>
      <button class="close" on:click={() => closeToast(toast.id)} aria-label="Закрыть уведомление">×</button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    right: 1rem;
    top: 1rem;
    z-index: 2000;
    display: grid;
    gap: 0.5rem;
    max-width: 420px;
  }
  .toast {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    border: 1px solid transparent;
    background: white;
    box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    font-size: 0.92rem;
  }
  .toast.success { border-color: #b7ebc6; background: #f3fff7; color: #1f6b33; }
  .toast.error { border-color: #ffc4c4; background: #fff5f5; color: #8c1d1d; }
  .toast.warning { border-color: #ffe5a8; background: #fffaf0; color: #8a5b00; }
  .toast.info { border-color: #c8defd; background: #f5f9ff; color: #124b92; }
  .close {
    background: transparent;
    border: none;
    color: inherit;
    font-size: 1.1rem;
    cursor: pointer;
    line-height: 1;
    padding: 0;
    width: 22px;
    height: 22px;
  }
</style>
