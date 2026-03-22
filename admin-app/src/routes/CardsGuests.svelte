<script>
  import Guests from './Guests.svelte';
  import LostCards from './LostCards.svelte';
  import { roleStore } from '../stores/roleStore.js';

  let activeTab = 'guests';

  const tabs = [
    { key: 'guests', label: 'Гости и карты' },
    { key: 'lost-cards', label: 'LostCards' },
  ];
</script>

{#if !$roleStore.permissions.cards_manage}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает операции с картами и гостями.</p>
  </section>
{:else}
  <section class="cards-guests-page">
    <header class="page-header">
      <div>
        <h1>CardsGuests</h1>
        <p>Рабочий сценарий по гостям, картам, пополнениям и обработке LostCards внутри одного раздела.</p>
      </div>
      <div class="tabs" role="tablist" aria-label="Карты и гости">
        {#each tabs as tab}
          <button
            class:active={activeTab === tab.key}
            class="tab-button"
            on:click={() => (activeTab = tab.key)}
            role="tab"
            aria-selected={activeTab === tab.key}
          >
            {tab.label}
          </button>
        {/each}
      </div>
    </header>

    {#if activeTab === 'guests'}
      <Guests embedded={true} />
    {:else}
      <LostCards embedded={true} />
    {/if}
  </section>
{/if}

<style>
  .cards-guests-page {
    display: grid;
    gap: 1rem;
  }
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 1rem;
  }
  .page-header h1 {
    margin: 0 0 0.25rem;
  }
  .page-header p {
    margin: 0;
    color: var(--text-secondary);
  }
  .tabs {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .tab-button {
    background: #eef3ff;
    color: #23416b;
  }
  .tab-button.active {
    background: var(--brand);
    color: white;
  }
  .access-denied { padding: 1rem; }
</style>
