<!-- src/components/beverages/BeverageManager.svelte -->
<script>
  import { beverageStore } from '../../stores/beverageStore.js';
  
  // --- ИЗМЕНЕНИЕ: formData приведена в полное соответствие с Pydantic схемой BeverageCreate ---
  let formData = {
    name: '',
    style: 'IPA',
    brewery: '',
    abv: '5.0',
    sell_price_per_liter: '7.50'
    // Поле description удалено, так как его нет в схеме создания
  };

  let formError = '';

  async function handleSubmit() {
    formError = '';
    try {
      // payload теперь полностью соответствует `BeveragePayload` в Rust
      const payload = { 
        ...formData, 
        abv: formData.abv ? String(formData.abv) : null // Убедимся, что abv - строка или null
      };
      await beverageStore.createBeverage(payload);
      
      // Сброс формы
      formData.name = '';
      formData.brewery = '';
      formData.abv = '5.0';
      formData.sell_price_per_liter = '7.50';

    } catch (error) {
      formError = typeof error === 'string' ? error : (error instanceof Error ? error.message : 'Unknown error');
    }
  }
</script>

<div class="beverage-manager">
  <div class="beverage-list">
    {#if $beverageStore.loading && $beverageStore.beverages.length === 0}
      <p class="placeholder-text">Loading beverages...</p>
    {:else if $beverageStore.beverages.length === 0}
      <p class="placeholder-text">No beverages found. Add one below.</p>
    {:else}
      <ul>
        {#each $beverageStore.beverages as beverage (beverage.beverage_id)}
          <li>
            <span class="name">{beverage.name}</span>
            <!-- --- ИЗМЕНЕНИЕ: beverage.beverage_type -> beverage.style --- -->
            <span class="type">{beverage.style}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  <!-- --- ИЗМЕНЕНИЕ: Поля формы и плейсхолдеры обновлены --- -->
  <form class="beverage-form" on:submit|preventDefault={handleSubmit}>
    <h4>Add New Beverage</h4>
    <input type="text" placeholder="Beverage Name" bind:value={formData.name} required disabled={$beverageStore.loading} />
    <input type="text" placeholder="Brewery" bind:value={formData.brewery} required disabled={$beverageStore.loading} />
    <select bind:value={formData.style} disabled={$beverageStore.loading}>
      <option value="IPA">IPA</option>
      <option value="Stout">Stout</option>
      <option value="Lager">Lager</option>
      <option value="Cider">Cider</option>
      <option value="Other">Other</option>
    </select>
    <input 
      type="text" 
      placeholder="ABV (e.g., 5.0)" 
      bind:value={formData.abv}
      pattern="^\d*\.?\d*$"
      title="ABV should be a number, e.g., 5.0 or 4.5"
      disabled={$beverageStore.loading}
    />
    <input 
      type="text" 
      placeholder="Sell Price per Liter (e.g., 7.50)" 
      bind:value={formData.sell_price_per_liter} 
      required 
      pattern="^\d*\.?\d*$"
      title="Price should be a number, e.g., 7.50 or 8"
      disabled={$beverageStore.loading}
    />
    <button type="submit" disabled={$beverageStore.loading}>
      {$beverageStore.loading ? 'Adding...' : '+ Add Beverage'}
    </button>
    {#if formError}<p class="error">{formError}</p>{/if}
  </form>
</div>

<style>
    .beverage-manager { 
        border: 1px solid #eee; 
        border-radius: 8px; 
        overflow: hidden; 
        display: flex;
        flex-direction: column;
        height: 100%; /* Занимает всю высоту родительского грид-элемента */
    }
    .beverage-list { 
        flex-grow: 1; /* Список занимает всё доступное пространство */
        overflow-y: auto; 
        padding: 0.5rem; 
    }
    .beverage-list ul { 
        list-style-type: none; 
        padding: 0; 
        margin: 0; 
    }
    .beverage-list li { 
        display: flex; 
        justify-content: space-between; 
        padding: 0.5rem; 
        border-bottom: 1px solid #f0f0f0; 
    }
    .beverage-list li:last-child { 
        border-bottom: none; 
    }
    .name { 
        font-weight: 500; 
    }
    .type { 
        font-size: 0.85rem; 
        color: #666; 
    }
    .placeholder-text {
        padding: 1rem;
        text-align: center;
        color: #888;
    }
    .beverage-form { 
        padding: 1rem; 
        background-color: #f9f9f9; 
        border-top: 1px solid #eee; 
    }
    .beverage-form h4 { 
        margin: 0 0 1rem 0; 
    }
    .beverage-form input, .beverage-form select { 
        width: 100%; 
        margin-bottom: 0.5rem; 
        padding: 0.5rem; 
        box-sizing: border-box;
    }
    .beverage-form button { 
        width: 100%; 
        padding: 0.5rem; 
        margin-top: 0.5rem;
    }
    .error { 
        color: red; 
        font-size: 0.8rem; 
        margin-top: 0.5rem; 
        text-align: center;
    }
</style>