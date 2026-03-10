<script>
  import { createEventDispatcher } from 'svelte';
  import { kegStore } from '../../stores/kegStore';
  import { formatVolumeRu } from '../../lib/formatters.js';

  /** @type {import('../../../../src-tauri/src/api_client').Tap} */
  export let tap;
  export let isSaving = false;

  const dispatch = createEventDispatcher();

  let selectedKegId = null;
  let suggestion = null;
  let suggestionLoading = false;
  let suggestionError = '';
  let lastRequestedBeerTypeId = null;

  $: availableKegs = $kegStore.kegs.filter((keg) => keg.status === 'full');
  $: selectedKeg = availableKegs.find((keg) => keg.keg_id === selectedKegId) ?? null;
  $: selectedBeerTypeId = selectedKeg?.beverage_id ?? null;

  $: {
    if (availableKegs.length > 0) {
      const selectedKegStillAvailable = availableKegs.some((keg) => keg.keg_id === selectedKegId);
      if (!selectedKegId || !selectedKegStillAvailable) {
        selectedKegId = availableKegs[0].keg_id;
      }
    } else {
      selectedKegId = null;
    }
  }

  $: if (!selectedBeerTypeId) {
    suggestion = null;
    suggestionError = '';
    lastRequestedBeerTypeId = null;
  }

  $: if (selectedBeerTypeId && selectedBeerTypeId !== lastRequestedBeerTypeId) {
    loadSuggestion(selectedBeerTypeId);
  }

  function kegLabel(keg) {
    return `${keg.beverage.name} (${formatVolumeRu(keg.initial_volume_ml)}) · ID ...${keg.keg_id.slice(-6)}`;
  }

  async function loadSuggestion(beerTypeId) {
    lastRequestedBeerTypeId = beerTypeId;
    suggestionLoading = true;
    suggestionError = '';
    const requestBeerTypeId = beerTypeId;

    try {
      const response = await kegStore.getSuggestion(beerTypeId);
      if (lastRequestedBeerTypeId !== requestBeerTypeId) {
        return;
      }
      suggestion = response;
    } catch (error) {
      if (lastRequestedBeerTypeId !== requestBeerTypeId) {
        return;
      }
      suggestion = null;
      suggestionError = error instanceof Error ? error.message : String(error);
    } finally {
      if (lastRequestedBeerTypeId === requestBeerTypeId) {
        suggestionLoading = false;
      }
    }
  }

  function applySuggestedKeg() {
    if (suggestion?.recommended_keg?.keg_id) {
      selectedKegId = suggestion.recommended_keg.keg_id;
    }
  }
</script>

<div class="assign-keg-modal">
  <h3>Назначить кегу на <span class="tap-name">{tap.display_name}</span></h3>

  {#if availableKegs.length === 0}
    <div class="no-kegs-placeholder">
      <p>В инвентаре нет доступных полных кег.</p>
      <p>Сначала добавьте новую кегу.</p>
    </div>
  {:else}
    <div class="form-group">
      <label for="keg-select">Выберите доступную кегу:</label>
      <select id="keg-select" bind:value={selectedKegId} disabled={isSaving}>
        {#each availableKegs as keg (keg.keg_id)}
          <option value={keg.keg_id}>{kegLabel(keg)}</option>
        {/each}
      </select>
    </div>

    <section class="suggestion-panel">
      <div class="suggestion-header">
        <h4>Рекомендованный кег (FIFO)</h4>
        {#if suggestion?.ordering_keys_used?.length}
          <span class="ordering-keys">{suggestion.ordering_keys_used.join(' → ')}</span>
        {/if}
      </div>

      {#if suggestionLoading}
        <p class="hint">Ищем старейший доступный кег этого типа...</p>
      {:else if suggestionError}
        <p class="error">{suggestionError}</p>
      {:else if suggestion?.recommended_keg}
        <div class="suggestion-card">
          <div class="suggestion-main">{kegLabel(suggestion.recommended_keg)}</div>
          <div class="suggestion-meta">
            <span>Кандидатов: {suggestion.candidates_count}</span>
            <span>Причина: {suggestion.reason}</span>
          </div>
          <button
            class="btn-secondary"
            type="button"
            on:click={applySuggestedKeg}
            disabled={isSaving || suggestion.recommended_keg.keg_id === selectedKegId}
          >
            Выбрать этот кег
          </button>
        </div>
      {:else}
        <p class="hint">Нет доступных кегов этого типа.</p>
      {/if}
    </section>
  {/if}

  <div class="form-actions">
    <button class="btn-secondary" on:click={() => dispatch('cancel')} disabled={isSaving}>
      Отмена
    </button>
    <button
      class="btn-primary"
      on:click={() => dispatch('save', { kegId: selectedKegId })}
      disabled={isSaving || availableKegs.length === 0}
    >
      {#if isSaving}
        Назначение...
      {:else}
        Назначить кегу
      {/if}
    </button>
  </div>
</div>

<style>
  .assign-keg-modal {
    min-width: 440px;
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

  .suggestion-panel {
    margin-top: 1rem;
    padding: 1rem;
    border: 1px solid #d9e2ec;
    border-radius: 6px;
    background: #f8fbff;
  }

  .suggestion-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.75rem;
  }

  .suggestion-header h4 {
    margin: 0;
  }

  .ordering-keys {
    font-size: 0.85rem;
    color: #52606d;
  }

  .suggestion-card {
    display: grid;
    gap: 0.5rem;
  }

  .suggestion-main {
    font-weight: 600;
  }

  .suggestion-meta {
    display: flex;
    gap: 1rem;
    font-size: 0.9rem;
    color: #52606d;
  }

  .hint {
    margin: 0;
    color: #52606d;
  }

  .error {
    margin: 0;
    color: #c53030;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 2rem;
  }

  .btn-primary,
  .btn-secondary {
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
