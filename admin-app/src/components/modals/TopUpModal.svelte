<script>
  import { createEventDispatcher } from 'svelte';
  import Modal from '../common/Modal.svelte';

  const dispatch = createEventDispatcher();
  export let guestName = 'Гость';
  export let isSaving = false;

  const presets = [200, 500, 1000, 1500, 2000];
  let amount = '';
  let error = '';

  function applyPreset(value) {
    amount = value.toFixed(2);
    error = '';
  }

  function appendDigit(value) {
    const current = amount.replace(/[^\d.]/g, '');
    if (value === 'backspace') {
      amount = current.slice(0, -1);
      return;
    }

    if (value === '.' && current.includes('.')) return;
    const next = `${current}${value}`;
    amount = next;
  }

  function formatPreview(raw) {
    const n = Number(raw);
    if (!Number.isFinite(n) || n <= 0) return '0.00';
    return n.toFixed(2);
  }

  function handleSave() {
    error = '';
    const numericAmount = parseFloat(amount);

    if (isNaN(numericAmount) || numericAmount <= 0) {
      error = 'Введите положительную сумму.';
      return;
    }

    if (numericAmount > 50000) {
      error = 'Сумма выше лимита для демо (50 000).';
      return;
    }

    dispatch('save', {
      amount: numericAmount.toFixed(2),
      payment_method: 'cash'
    });
  }
</script>

<Modal on:close={() => dispatch('close')}>
  <div class="top-up-modal">
    <h2>Пополнение баланса</h2>
    <p class="subtitle">Гость: <strong>{guestName}</strong></p>

    <div class="preview">{formatPreview(amount)}</div>

    <div class="presets">
      {#each presets as preset}
        <button type="button" class="preset" on:click={() => applyPreset(preset)} disabled={isSaving}>+{preset}</button>
      {/each}
    </div>

    <div class="keypad">
      {#each ['1','2','3','4','5','6','7','8','9','00','0','.'] as key}
        <button type="button" on:click={() => appendDigit(key)} disabled={isSaving}>{key}</button>
      {/each}
      <button type="button" class="backspace" on:click={() => appendDigit('backspace')} disabled={isSaving}>⌫</button>
    </div>

    {#if error}
      <p class="error-message">{error}</p>
    {/if}

    <div class="form-actions">
      <button type="button" class="btn-cancel" on:click={() => dispatch('close')} disabled={isSaving}>Отмена</button>
      <button type="button" class="btn-save" on:click={handleSave} disabled={isSaving || !amount}>
        {#if isSaving}Сохранение...{:else}Подтвердить пополнение{/if}
      </button>
    </div>
  </div>
</Modal>

<style>
  .top-up-modal { padding: 1rem; width: min(560px, 92vw); }
  h2 { margin-top: 0; margin-bottom: 0.4rem; }
  .subtitle { margin-top: 0; color: #4e627f; }

  .preview {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: 0.02em;
    padding: 0.8rem 1rem;
    border: 1px solid #dbe4f1;
    border-radius: 10px;
    background: #f8fbff;
    margin-bottom: 0.8rem;
  }

  .presets {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.45rem;
    margin-bottom: 0.8rem;
  }
  .preset { background: #eaf1ff; color: #1d4f98; }

  .keypad {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .keypad button { min-height: 48px; font-weight: 700; }
  .backspace { background: #f0f3f8; color: #243b5c; }

  .error-message { color: #d32f2f; margin-top: 0.6rem; margin-bottom: 0; }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.8rem;
    margin-top: 1.25rem;
  }
  .btn-cancel { background: #eee; color: #243b5c; }
  .btn-save { background: var(--brand); color: white; }
</style>
