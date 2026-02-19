<script>
  export let demoMode = false;
  export let online = true;
  export let nfcStatus = 'ok';

  $: hasWarning = demoMode || !online || nfcStatus === 'error';
</script>

{#if hasWarning}
  <section class="banner" class:error={!online || nfcStatus === 'error'}>
    {#if demoMode}
      <strong>Demo mode:</strong> часть данных может быть моковой для стабильного показа.
    {/if}

    {#if !online}
      <span>Сеть недоступна. Используйте действия, не требующие онлайн-подтверждения.</span>
    {/if}

    {#if nfcStatus === 'error'}
      <span>NFC недоступен. Для демонстрации продолжайте сценарий с уже привязанной картой.</span>
    {/if}
  </section>
{/if}

<style>
  .banner {
    margin: 0 12px;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid #c8ddff;
    background: #f1f7ff;
    color: #1f4f8f;
    display: flex;
    flex-wrap: wrap;
    gap: 8px 12px;
    font-size: 0.88rem;
  }
  .banner.error {
    border-color: #ffc9cf;
    background: #fff2f4;
    color: #8c1c2a;
  }
</style>
