<!-- src/components/taps/TapGrid.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import TapCard from './TapCard.svelte';
  
  /** @type {import('../../../../src-tauri/src/api_client').Tap[]} */
  export let taps = [];

  // +++ НОВЫЙ КОД: Создаем диспетчер событий +++
  const dispatch = createEventDispatcher();
</script>

{#if taps.length > 0}
  <div class="tap-grid">
    {#each taps as tap (tap.tap_id)}
      <!-- --- ИЗМЕНЕНИЕ: Добавляем on:assign --- -->
      <!-- Эта конструкция слушает событие 'assign' от TapCard 
           и автоматически "пробрасывает" его дальше наверх 
           со всеми деталями. -->
      <TapCard {tap} on:assign />
    {/each}
  </div>
{:else}
  <p>No taps found in the system.</p>
{/if}

<style>
  .tap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }
</style>