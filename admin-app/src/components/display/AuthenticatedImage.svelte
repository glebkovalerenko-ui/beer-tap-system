<script>
  import { onDestroy } from 'svelte';

  import { displayAdminFetchBlob } from '../../lib/displayAdminApi.js';

  export let src = '';
  export let alt = '';
  export let emptyLabel = 'Превью недоступно';

  let currentSrc = null;
  let requestId = 0;
  let objectUrl = '';
  let loading = false;
  let failed = false;

  function revokeObjectUrl() {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = '';
    }
  }

  async function loadImage(source) {
    const nextRequestId = ++requestId;
    revokeObjectUrl();
    failed = false;

    if (!source) {
      loading = false;
      return;
    }

    loading = true;

    try {
      const blob = await displayAdminFetchBlob(source);
      if (nextRequestId !== requestId) {
        return;
      }
      objectUrl = URL.createObjectURL(blob);
    } catch {
      if (nextRequestId !== requestId) {
        return;
      }
      failed = true;
    } finally {
      if (nextRequestId === requestId) {
        loading = false;
      }
    }
  }

  $: if (src !== currentSrc) {
    currentSrc = src;
    loadImage(src);
  }

  onDestroy(() => {
    revokeObjectUrl();
  });
</script>

<div class="image-frame">
  {#if objectUrl}
    <img src={objectUrl} {alt} loading="lazy" />
  {:else if loading}
    <span class="placeholder">Загрузка...</span>
  {:else if failed}
    <span class="placeholder">{emptyLabel}</span>
  {:else}
    <span class="placeholder">{emptyLabel}</span>
  {/if}
</div>

<style>
  .image-frame {
    width: 100%;
    height: 100%;
    background: linear-gradient(180deg, #f5f7fb 0%, #eef2f8 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .placeholder {
    padding: 0.75rem;
    color: #64748b;
    font-size: 0.85rem;
    text-align: center;
  }
</style>
