<script>
  import { createEventDispatcher } from 'svelte';

  import { normalizeError } from '../../lib/errorUtils.js';
  import { listDisplayMediaAssets, uploadDisplayMediaAsset } from '../../lib/displayAdminApi.js';
  import AuthenticatedImage from './AuthenticatedImage.svelte';

  export let kind = 'background';
  export let title = 'Медиафайл';
  export let description = '';
  export let selectedAssetId = null;
  export let disabled = false;
  export let emptyLabel = 'Файл не выбран';

  const dispatch = createEventDispatcher();

  let assets = [];
  let loading = false;
  let loadError = '';
  let uploadError = '';
  let isLibraryOpen = false;
  let fileInput;
  let loadedKind = null;

  $: selectedAsset = assets.find((asset) => asset.asset_id === selectedAssetId) || null;
  $: if (kind && kind !== loadedKind) {
    loadedKind = kind;
    loadAssets();
  }

  function formatSize(bytes) {
    const value = Number(bytes || 0);
    if (!value) {
      return '0 КБ';
    }

    return `${Math.max(1, Math.round(value / 1024))} КБ`;
  }

  function formatDimensions(asset) {
    if (!asset?.width || !asset?.height) {
      return 'Размер не определен';
    }

    return `${asset.width} × ${asset.height}`;
  }

  async function loadAssets() {
    loading = true;
    loadError = '';

    try {
      assets = await listDisplayMediaAssets(kind);
    } catch (error) {
      loadError = normalizeError(error);
    } finally {
      loading = false;
    }
  }

  async function handleFileChange(event) {
    const file = event.currentTarget.files?.[0];
    if (!file) {
      return;
    }

    uploadError = '';

    try {
      const uploaded = await uploadDisplayMediaAsset(kind, file);
      assets = [uploaded, ...assets.filter((asset) => asset.asset_id !== uploaded.asset_id)];
      isLibraryOpen = true;
      dispatch('change', { assetId: uploaded.asset_id, asset: uploaded });
    } catch (error) {
      uploadError = normalizeError(error);
    } finally {
      event.currentTarget.value = '';
    }
  }

  function handleSelectAsset(asset) {
    dispatch('change', { assetId: asset.asset_id, asset });
  }

  function clearSelection() {
    dispatch('change', { assetId: null, asset: null });
  }
</script>

<div class="media-picker">
  <div class="picker-header">
    <div>
      <h5>{title}</h5>
      {#if description}
        <p>{description}</p>
      {/if}
    </div>
    <div class="picker-actions">
      <button type="button" class="secondary-action" on:click={() => fileInput?.click()} disabled={disabled}>
        Загрузить
      </button>
      <button
        type="button"
        class="secondary-action"
        on:click={() => (isLibraryOpen = !isLibraryOpen)}
        disabled={disabled}
      >
        {isLibraryOpen ? 'Скрыть варианты' : 'Выбрать из загруженных'}
      </button>
      <button type="button" class="secondary-action clear-action" on:click={clearSelection} disabled={disabled || !selectedAssetId}>
        Очистить
      </button>
    </div>
  </div>

  <input
    bind:this={fileInput}
    type="file"
    accept=".png,.jpg,.jpeg,image/png,image/jpeg"
    hidden
    on:change={handleFileChange}
    disabled={disabled}
  />

  <div class:selected={Boolean(selectedAsset)} class="selected-asset">
    <div class="preview-box">
      <AuthenticatedImage src={selectedAsset?.content_url} alt={selectedAsset?.original_filename || title} emptyLabel={emptyLabel} />
    </div>
    <div class="selected-meta">
      {#if selectedAsset}
        <strong>{selectedAsset.original_filename}</strong>
        <span>{formatDimensions(selectedAsset)} · {formatSize(selectedAsset.byte_size)}</span>
      {:else}
        <strong>{emptyLabel}</strong>
        <span>Можно загрузить новый файл или выбрать уже существующий.</span>
      {/if}
    </div>
  </div>

  {#if uploadError}
    <p class="error-text">{uploadError}</p>
  {/if}

  {#if isLibraryOpen}
    <div class="library-panel">
      {#if loading}
        <p class="state-text">Загрузка файлов...</p>
      {:else if loadError}
        <div class="library-state">
          <p class="error-text">{loadError}</p>
          <button type="button" class="secondary-action" on:click={loadAssets}>Повторить</button>
        </div>
      {:else if assets.length === 0}
        <p class="state-text">Пока нет загруженных файлов этого типа.</p>
      {:else}
        <div class="asset-grid">
          {#each assets as asset (asset.asset_id)}
            <button
              type="button"
              class:selected={asset.asset_id === selectedAssetId}
              class="asset-card"
              on:click={() => handleSelectAsset(asset)}
              disabled={disabled}
            >
              <div class="asset-preview">
                <AuthenticatedImage src={asset.content_url} alt={asset.original_filename} />
              </div>
              <div class="asset-copy">
                <strong>{asset.original_filename}</strong>
                <span>{formatDimensions(asset)}</span>
                <span>{formatSize(asset.byte_size)}</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .media-picker {
    display: grid;
    gap: 0.75rem;
  }

  .picker-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }

  .picker-header h5 {
    margin: 0;
    font-size: 0.95rem;
  }

  .picker-header p,
  .selected-meta span,
  .asset-copy span,
  .state-text {
    margin: 0.25rem 0 0;
    color: var(--text-secondary);
    line-height: 1.35;
  }

  .picker-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .secondary-action {
    width: auto;
    margin: 0;
    background: #edf2fb;
    color: #23416b;
  }

  .clear-action {
    background: #f3f4f6;
    color: #49566d;
  }

  .selected-asset {
    display: grid;
    grid-template-columns: 112px 1fr;
    gap: 0.85rem;
    padding: 0.8rem;
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-sm);
    background: #fbfcfe;
  }

  .selected-asset.selected {
    border-color: #8bb0f1;
    background: #f7fbff;
  }

  .preview-box,
  .asset-preview {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(0, 0, 0, 0.06);
    background: #eef2f7;
  }

  .preview-box {
    min-height: 96px;
  }

  .selected-meta,
  .asset-copy {
    display: grid;
    align-content: center;
    gap: 0.25rem;
  }

  .selected-meta strong,
  .asset-copy strong {
    color: var(--text-primary);
  }

  .library-panel {
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-sm);
    padding: 0.8rem;
    background: #fbfcfe;
  }

  .library-state {
    display: grid;
    gap: 0.75rem;
    justify-items: start;
  }

  .asset-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 0.75rem;
  }

  .asset-card {
    width: 100%;
    margin: 0;
    padding: 0.6rem;
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-sm);
    background: #fff;
    color: inherit;
    box-shadow: none;
    display: grid;
    gap: 0.6rem;
    text-align: left;
  }

  .asset-card.selected {
    border-color: #8bb0f1;
    background: #eef5ff;
  }

  .asset-preview {
    min-height: 118px;
  }

  .error-text {
    margin: 0;
    color: #c61f35;
  }

  @media (max-width: 860px) {
    .picker-header,
    .selected-asset {
      grid-template-columns: 1fr;
      display: grid;
    }

    .picker-actions {
      justify-content: flex-start;
    }
  }
</style>
