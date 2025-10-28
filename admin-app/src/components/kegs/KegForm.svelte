<!-- src/components/kegs/KegForm.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  // +++ НОВЫЙ ИМПОРТ +++
  import { beverageStore } from '../../stores/beverageStore.js';

  /** @type {import('../../../../src-tauri/src/api_client').Keg | null} */
  export let keg = null;
  export let isSaving = false;
  
  const dispatch = createEventDispatcher();
  
  // --- ИЗМЕНЕНИЕ: Убираем хардкод. `availableBeverages` теперь реактивная переменная.
  $: availableBeverages = $beverageStore.beverages;

  let formData = {
    // Реактивно устанавливаем beverage_id, если список доступен
    beverage_id: keg?.beverage.beverage_id || ($beverageStore.beverages[0]?.beverage_id || ''),
    initial_volume_ml: keg?.initial_volume_ml || 50000, 
    purchase_price: keg?.purchase_price || '100.00',
  };
  
  // Если список напитков изменится (например, после загрузки), 
  // а у нас не выбран ID, выберем первый доступный.
  $: if (!$beverageStore.loading && availableBeverages.length > 0 && !formData.beverage_id) {
    formData.beverage_id = availableBeverages[0].beverage_id;
  }

  function handleSubmit() {
    if (!formData.beverage_id) {
      alert("Please select a beverage. If the list is empty, add one in the 'Beverage Directory' first.");
      return;
    }
    const payload = {
      ...formData,
      initial_volume_ml: parseInt(String(formData.initial_volume_ml), 10),
    };
    dispatch('save', payload);
  }
</script>

<form on:submit|preventDefault={handleSubmit}>
  <h3>{keg ? 'Edit Keg Information' : 'Add New Keg to Inventory'}</h3>
  
  <fieldset>
    <legend>Beverage & Volume</legend>
    <div class="form-group">
      <label for="beverage_id">Beverage</label>
      <!-- --- ИЗМЕНЕНИЕ: Select теперь полностью динамический --- -->
      <select 
        id="beverage_id" 
        bind:value={formData.beverage_id} 
        required 
        disabled={isSaving || availableBeverages.length === 0}
      >
        {#if $beverageStore.loading}
          <option value="" disabled>Loading beverages...</option>
        {:else if availableBeverages.length === 0}
          <option value="" disabled>Please add a beverage first</option>
        {:else}
          {#each availableBeverages as beverage (beverage.beverage_id)}
            <option value={beverage.beverage_id}>{beverage.name}</option>
          {/each}
        {/if}
      </select>
    </div>
    <div class="form-group">
      <label for="initial_volume_ml">Initial Volume (ml)</label>
      <input 
        id="initial_volume_ml" 
        type="number" 
        bind:value={formData.initial_volume_ml} 
        required 
        min="1000"
        step="1000"
        disabled={isSaving}
      />
    </div>
  </fieldset>

  <fieldset>
    <legend>Financial</legend>
    <div class="form-group">
      <label for="purchase_price">Purchase Price ($)</label>
      <input 
        id="purchase_price" 
        type="text" 
        bind:value={formData.purchase_price} 
        required
        pattern="^\d*\.?\d*$"
        title="Price should be a number, e.g., 99.50 or 100"
        disabled={isSaving}
      />
    </div>
  </fieldset>

  <div class="form-actions">
    <button type="button" class="btn-secondary" on:click={() => dispatch('cancel')} disabled={isSaving}>
      Cancel
    </button>
    <button type="submit" class="btn-primary" disabled={isSaving}>
      {#if isSaving}
        Saving...
      {:else}
        {keg ? 'Save Changes' : 'Add Keg'}
      {/if}
    </button>
  </div>
</form>

<style>
  /* Стили скопированы из GuestForm для консистентности */
  h3 { margin-top: 0; }
  fieldset { border: 1px solid #eee; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; }
  legend { font-weight: bold; padding: 0 0.5rem; }
  .form-group { margin-bottom: 1rem; }
  label { display: block; margin-bottom: 0.25rem; font-size: 0.9rem; color: #555; }
  input, select { width: 100%; padding: 0.5rem; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
  .form-actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 1.5rem; }
  .btn-primary { background-color: #28a745; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
  .btn-primary:disabled { background-color: #a0d8af; cursor: not-allowed; }
  .btn-secondary { background-color: #f0f0f0; color: #333; border: 1px solid #ccc; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
</style>