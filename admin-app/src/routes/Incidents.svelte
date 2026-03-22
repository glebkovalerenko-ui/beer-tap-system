<script>
  import LostCards from './LostCards.svelte';
  import ActivityTrail from '../components/system/ActivityTrail.svelte';
  import { roleStore } from '../stores/roleStore.js';
</script>

{#if !$roleStore.permissions.incidents}
  <section class="ui-card restricted">
    <h1>Incidents</h1>
    <p>Раздел инцидентов скрыт для текущей роли.</p>
  </section>
{:else}
  <section class="incident-layout">
    <div class="ui-card incident-panel">
      <div class="section-header">
        <h1>Incidents</h1>
        <p>Операционные отклонения, потерянные карты и журнал событий смены.</p>
      </div>
      <LostCards embedded={true} />
    </div>

    <div class="ui-card trail-panel">
      <h2>События и регламенты</h2>
      <p class="hint">Используйте журнал как быстрый чек-лист при разборе спорных операций и восстановлении хода смены.</p>
      <ActivityTrail />
    </div>
  </section>
{/if}

<style>
  .incident-layout {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
    gap: 1rem;
    align-items: start;
  }
  .incident-panel,
  .trail-panel {
    padding: 1rem;
  }
  .section-header h1,
  .trail-panel h2 {
    margin: 0 0 0.25rem;
  }
  .section-header p,
  .hint {
    margin: 0 0 1rem;
    color: var(--text-secondary);
  }
  .restricted { padding: 1rem; }
</style>
