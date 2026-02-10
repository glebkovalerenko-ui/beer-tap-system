<!-- src/components/taps/TapCard.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { tapStore } from '../../stores/tapStore.js';
  import { kegStore } from '../../stores/kegStore.js';

  /** @type {import('../../../../src-tauri/src/api_client').Tap} */
  export let tap;

  const dispatch = createEventDispatcher();

  // --- ИЗМЕНЕНИЕ: tap.current_keg -> tap.keg ---
  $: keg = tap.keg;
  $: kegPercentage = keg ? (keg.current_volume_ml / keg.initial_volume_ml) * 100 : 0;
  // --- ИЗМЕНЕНИЕ: Логика теперь полагается на keg_id ---
  $: isAssignable = !tap.keg_id && (tap.status === 'locked' || tap.status === 'empty');
  
  let isLoading = false;

  async function handleUnassign() {
    if (!keg) return;
    if (confirm(`Вы уверены, что хотите отключить кегу "${keg.beverage.name}" с ${tap.display_name}?`)) {
      isLoading = true;
      try {
        await tapStore.unassignKegFromTap(tap.tap_id);
        kegStore.markKegAsAvailable(keg.keg_id);
      } catch (error) {
        alert(`Ошибка: ${error}`);
      } finally {
        isLoading = false;
      }
    }
  }

  async function handleStatusChange(newStatus) {
    if (confirm(`Изменить статус ${tap.display_name} на "${newStatus}"?`)) {
      isLoading = true;
      try {
        await tapStore.updateTapStatus(tap.tap_id, newStatus);
      } catch (error) {
        alert(`Ошибка: ${error}`);
      } finally {
        isLoading = false;
      }
    }
  }
</script>

<div class="tap-card" class:locked={tap.status !== 'active'} class:loading={isLoading}>
  {#if isLoading}<div class="overlay"><div class="spinner"></div></div>{/if}
  <div class="header">
    <span class="tap-name">{tap.display_name}</span>
    <span class="status {tap.status}">{tap.status}</span>
  </div>
  <div class="body">
    <!-- --- ИЗМЕНЕНИЕ: Проверяем `keg` и `keg.beverage` для безопасности --- -->
    {#if keg && keg.beverage}
      <div class="keg-info">
        <p class="beverage-name">{keg.beverage.name}</p>
        <p class="beverage-type">{keg.beverage.style}</p>
      </div>
      <div class="volume-bar-container">
        <div class="volume-bar" style="width: {kegPercentage}%"></div>
      </div>
      <p class="volume-text">
        {keg.current_volume_ml} / {keg.initial_volume_ml} мл осталось
      </p>
    {:else}
      <div class="empty-keg">
        <p>Кега не назначена</p>
      </div>
    {/if}
  </div>

  <!-- --- ИЗМЕНЕНИЕ: Логика `{#if}` теперь будет работать правильно --- -->
  <div class="footer">
    {#if tap.keg_id}
      <!-- Кнопки, если кега назначена -->
      <button class="btn-secondary" on:click={() => handleStatusChange(tap.status === 'active' ? 'locked' : 'active')}>
        {tap.status === 'active' ? 'Заблокировать кран' : 'Активировать кран'}
      </button>
      <button class="btn-danger" on:click={handleUnassign}>Отключить кегу</button>
    {:else}
      <!-- Кнопки, если кега НЕ назначена -->
      {#if tap.status === 'cleaning'}
        <button class="btn-primary" on:click={() => handleStatusChange('locked')}>Отметить чистой</button>
      {:else}
        <button class="btn-secondary" on:click={() => handleStatusChange('cleaning')}>Перевести на чистку</button>
        <button class="btn-primary" on:click={() => dispatch('assign', { tap })} disabled={!isAssignable}>
          Назначить кегу
        </button>
      {/if}
    {/if}
  </div>
</div>

<style>
  /* ... (основные стили без изменений) ... */
  .tap-card {
    border: 1px solid #ccc;
    border-radius: 8px;
    background-color: #fff;
    display: flex;
    flex-direction: column;
    transition: box-shadow 0.2s;
  }
  .tap-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .tap-card.locked { background-color: #f8f8f8; opacity: 0.7; }
  .header { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; border-bottom: 1px solid #eee; }
  .tap-name { font-weight: bold; font-size: 1.2rem; }
  .status { font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 12px; font-weight: 500; text-transform: capitalize; }
  .status.active { background-color: #d4edda; color: #155724; }
  .status.locked { background-color: #f8d7da; color: #721c24; }
  .status.cleaning { background-color: #cce5ff; color: #004085; }
  .status.empty { background-color: #e2e3e5; color: #383d41; }

  .body { padding: 1rem; flex-grow: 1; }
  .keg-info { margin-bottom: 1rem; }
  .beverage-name { font-size: 1.1rem; font-weight: 600; margin: 0; }
  .beverage-type { font-size: 0.9rem; color: #666; margin: 0; }
  .volume-bar-container { height: 10px; background-color: #e9ecef; border-radius: 5px; overflow: hidden; margin-bottom: 0.5rem; }
  .volume-bar { height: 100%; background-color: #28a745; transition: width 0.3s ease-in-out; }
  .volume-text { font-size: 0.8rem; text-align: center; color: #666; margin: 0; }
  .empty-keg { display: flex; align-items: center; justify-content: center; min-height: 100px; color: #888; }
  
  .footer { padding: 0.75rem; border-top: 1px solid #eee; text-align: right; }
  .footer button:disabled { background-color: #e9ecef; cursor: not-allowed; color: #6c757d; }
  .footer { display: flex; gap: 0.5rem; justify-content: flex-end; }
  .footer button { flex-grow: 1; }
  .btn-primary { background-color: #28a745; color: white; border: none; }
  .btn-secondary { background-color: #f0f0f0; color: #333; border: 1px solid #ccc; }
  .btn-danger { background-color: #dc3545; color: white; border: none; }
  .loading { position: relative; }
  .overlay { position: absolute; inset: 0; background: rgba(255,255,255,0.7); display: grid; place-items: center; border-radius: 8px; }
  .spinner { width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite; }
  @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>