<script>
  import TapCard from './TapCard.svelte';

  export let taps = [];
  export let canControl = false;
  export let canMaintain = false;
  export let canDisplayOverride = false;
</script>

{#if taps.length > 0}
  <div class="tap-grid">
    {#each taps as tap (tap.tap_id)}
      <div class="grid-item">
        <TapCard
          {tap}
          {canControl}
          {canMaintain}
          {canDisplayOverride}
          on:open-detail
          on:assign
          on:display-settings
          on:stop-pour
          on:toggle-lock
          on:cleaning
          on:mark-ready
          on:unassign
        />
      </div>
    {/each}
  </div>
{:else}
  <div class="no-taps">
    <p>Краны не найдены в системе.</p>
  </div>
{/if}

<style>
  .tap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 1rem;
    padding: 0.25rem 0;
  }

  .grid-item {
    display: flex;
    flex-direction: column;
  }

  .no-taps {
    text-align: center;
    color: #666;
    padding: 2rem;
    background: #f9f9f9;
    border-radius: 8px;
  }
</style>
