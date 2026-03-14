<!-- src/components/taps/TapGrid.svelte -->
<script>
  import TapCard from './TapCard.svelte';

  export let taps = [];
</script>

{#if taps.length > 0}
  <div class="tap-grid">
    {#each taps as tap (tap.tap_id)}
      <div class="grid-item">
        <TapCard {tap} on:assign on:display-settings />
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
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
    padding: 0.5rem;
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
