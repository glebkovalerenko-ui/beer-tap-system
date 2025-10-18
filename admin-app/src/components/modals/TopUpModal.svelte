<!-- src/components/modals/TopUpModal.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import Modal from '../common/Modal.svelte';

  const dispatch = createEventDispatcher();
  
  // --- Props ---
  /**
   * Имя гостя для отображения в заголовке
   * @type {string}
   */
  export let guestName = 'Guest';
  /**
   * Флаг, указывающий на процесс сохранения (для блокировки кнопки)
   * @type {boolean}
   */
  export let isSaving = false;

  // --- Внутреннее состояние ---
  let amount = '';
  let error = '';

  function handleSave() {
    error = '';
    const numericAmount = parseFloat(amount);

    if (isNaN(numericAmount) || numericAmount <= 0) {
      error = 'Please enter a valid positive amount.';
      return;
    }

    // Отправляем данные наверх. Сумму передаем как строку,
    // так как бэкенд ожидает Decimal.
    dispatch('save', {
      amount: numericAmount.toFixed(2),
      payment_method: 'cash' // Пока хардкодим 'cash' для MVP
    });
  }
</script>

<Modal on:close={() => dispatch('close')}>
  <div class="top-up-modal">
    <h2>Top Up Balance for {guestName}</h2>
    <p>Enter the amount to add to the guest's balance.</p>

    <form on:submit|preventDefault={handleSave}>
      <div class="form-field">
        <label for="amount">Amount</label>
        <input
          type="number"
          id="amount"
          bind:value={amount}
          step="0.01"
          min="0.01"
          placeholder="e.g., 500.00"
          required
          disabled={isSaving}
        />
      </div>

      {#if error}
        <p class="error-message">{error}</p>
      {/if}

      <div class="form-actions">
        <button type="button" class="btn-cancel" on:click={() => dispatch('close')} disabled={isSaving}>
          Cancel
        </button>
        <button type="submit" class="btn-save" disabled={isSaving}>
          {#if isSaving}
            Saving...
          {:else}
            Save
          {/if}
        </button>
      </div>
    </form>
  </div>
</Modal>

<style>
  .top-up-modal {
    padding: 1rem;
  }
  h2 {
    margin-top: 0;
    font-size: 1.5rem;
  }
  p {
    color: #555;
    margin-bottom: 2rem;
  }
  .form-field {
    display: flex;
    flex-direction: column;
  }
  .form-field label {
    font-weight: bold;
    margin-bottom: 0.5rem;
  }
  .form-field input {
    font-size: 1.2rem;
    padding: 0.75rem;
    border: 1px solid #ccc;
    border-radius: 4px;
  }
  .error-message {
    color: #d32f2f;
    margin-top: 0.5rem;
    font-size: 0.9rem;
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 2rem;
  }
  button {
    padding: 0.75rem 1.5rem;
    border-radius: 5px;
    border: none;
    cursor: pointer;
    font-weight: bold;
  }
  .btn-cancel {
    background-color: #eee;
  }
  .btn-save {
    background-color: #2a9d8f;
    color: white;
  }
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>