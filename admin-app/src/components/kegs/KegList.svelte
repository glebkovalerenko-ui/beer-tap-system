<!-- src/components/kegs/KegList.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';

  /** @type {import('../../../../src-tauri/src/api_client').Keg[]} */
  export let kegs = [];

  const dispatch = createEventDispatcher();
</script>

{#if kegs.length > 0}
  <div class="keg-list-container">
    <table>
      <thead>
        <tr>
          <th>Beverage</th>
          <th>Status</th>
          <th>Volume</th>
          <th>Purchase Price</th>
          <th>Created At</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each kegs as keg (keg.keg_id)}
          <tr>
            <td>
              <div class="beverage-cell">
                <span class="beverage-name">{keg.beverage.name}</span>
                <span class="beverage-type">{keg.beverage.beverage_type}</span>
              </div>
            </td>
            <td><span class="status {keg.status}">{keg.status}</span></td>
            <td>{keg.current_volume_ml} / {keg.initial_volume_ml} ml</td>
            <td>${keg.purchase_price}</td>
            <td>{new Date(keg.created_at).toLocaleDateString()}</td>
            <td>
              <div class="action-buttons">
                <!-- --- ИЗМЕНЕНИЕ: "Оживляем" кнопки --- -->
                <button class="btn-sm btn-edit" on:click={() => dispatch('edit', { keg })}>Edit</button>
                <button class="btn-sm btn-delete" on:click={() => dispatch('delete', { keg })}>Delete</button>
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else}
  <p>No kegs found in inventory. Try adding one!</p>
{/if}

<style>
  .keg-list-container {
    overflow-x: auto;
    border: 1px solid #eee;
    border-radius: 8px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th, td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid #eee;
  }
  thead {
    background-color: #f9f9f9;
  }
  th {
    font-size: 0.9rem;
    font-weight: 600;
    color: #555;
  }
  .beverage-cell {
    display: flex;
    flex-direction: column;
  }
  .beverage-name {
    font-weight: 500;
  }
  .beverage-type {
    font-size: 0.85rem;
    color: #666;
  }
  .status {
    display: inline-block;
    font-size: 0.8rem;
    padding: 0.2rem 0.5rem;
    border-radius: 12px;
    font-weight: 500;
  }
  .status.new { background-color: #cce5ff; color: #004085; }
  .status.in_use { background-color: #d4edda; color: #155724; }
  .status.empty { background-color: #e2e3e5; color: #383d41; }
  .action-buttons {
    display: flex;
    gap: 0.5rem;
  }
  .btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
    border-radius: 4px;
    border: 1px solid transparent;
    cursor: pointer;
  }
  .btn-edit {
    border-color: #007bff;
    color: #007bff;
    background-color: white;
  }
  .btn-delete {
    border-color: #dc3545;
    color: #dc3545;
    background-color: white;
  }
</style>