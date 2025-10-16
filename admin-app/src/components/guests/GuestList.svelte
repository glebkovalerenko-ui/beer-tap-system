<script>
  import GuestListItem from './GuestListItem.svelte';

  // Этот компонент получает гостей как свойство (prop)
  export let guests = [];
</script>

{#if guests.length === 0}
  <p>No guests match your search.</p>
{:else}
  <ul class="guest-list">
    {#each guests as guest (guest.guest_id)}
      <!-- Передаем управление событием 'select' наверх -->
      <GuestListItem {guest} on:select />
    {/each}
  </ul>
{/if}

<style>
  .guest-list { list-style-type: none; padding: 0; }
</style>