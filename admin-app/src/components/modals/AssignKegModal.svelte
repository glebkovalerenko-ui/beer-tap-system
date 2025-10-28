<!-- src/components/modals/AssignKegModal.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { kegStore } from '../../stores/kegStore';

  /** @type {import('../../../../src-tauri/src/api_client').Tap} */
  export let tap;
  export let isSaving = false;

  const dispatch = createEventDispatcher();

  $: availableKegs = $kegStore.kegs.filter(keg => keg.status === 'full');

  // --- ИЗМЕНЕНИЕ: Безопасная инициализация selectedKegId ---
  let selectedKegId = null;

  // Этот реактивный блок будет выполнен, когда `availableKegs` изменится.
  // Он безопасно установит значение по умолчанию, только если оно еще не установлено
  // или если предыдущее выбранное значение исчезло из списка.
  $: {
    if (availableKegs.length > 0) {
      const selectedKegStillAvailable = availableKegs.some(k => k.keg_id === selectedKegId);
      if (!selectedKegId || !selectedKegStillAvailable) {
        selectedKegId = availableKegs[0].keg_id;
      }
    } else {
      selectedKegId = null;
    }
  }
</script>

<div class="assign-keg-modal">
  <h3>Assign Keg to <span class="tap-name">{tap.display_name}</span></h3>

  {#if availableKegs.length === 0}
    <div class="no-kegs-placeholder">
      <p>There are no 'full' kegs available in the inventory.</p>
      <p>Please add a new keg first.</p>
    </div>
  {:else}
    <div class="form-group">
      <label for="keg-select">Select an available keg:</label>
      <select id="keg-select" bind:value={selectedKegId} disabled={isSaving}>
        {#each availableKegs as keg (keg.keg_id)}
          <option value={keg.keg_id}>
            {keg.beverage.name} ({keg.initial_volume_ml / 1000}L) - ID: ...{keg.keg_id.slice(-6)}
          </option>
        {/each}
      </select>
    </div>
  {/if}

  <div class="form-actions">
    <button class="btn-secondary" on:click={() => dispatch('cancel')} disabled={isSaving}>
      Cancel
    </button>
    <button 
      class="btn-primary" 
      on:click={() => dispatch('save', { kegId: selectedKegId })} 
      disabled={isSaving || availableKegs.length === 0}
    >
      {#if isSaving}
        Assigning...
      {:else}
        Assign Keg
      {/if}
    </button>
  </div>
</div>

<style>
  .assign-keg-modal {
    min-width: 400px;
  }
  .tap-name {
    color: #007bff;
  }
  .no-kegs-placeholder {
    margin: 2rem 0;
    padding: 1rem;
    text-align: center;
    background-color: #f8f9fa;
    border-radius: 4px;
    color: #6c757d;
  }
  .form-group {
    margin: 1.5rem 0;
  }
  label {
    display: block;
    margin-bottom: 0.5rem;
  }
  select {
    width: 100%;
    padding: 0.5rem;
  }
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 2rem;
  }
  .btn-primary, .btn-secondary {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    border: 1px solid transparent;
  }
  .btn-primary {
    background-color: #28a745;
    color: white;
  }
  .btn-primary:disabled {
    background-color: #a0d8af;
  }
  .btn-secondary {
    background-color: #f0f0f0;
    color: #333;
    border-color: #ccc;
  }
</style>