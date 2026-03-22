<script>
  import { roleStore } from '../stores/roleStore.js';
  import { incidentStore } from '../stores/incidentStore.js';
  import IncidentList from '../components/incidents/IncidentList.svelte';
</script>

{#if !$roleStore.permissions.incidents_manage}
  <section class="ui-card restricted"><h1>Инциденты</h1><p>Раздел инцидентов скрыт для текущей роли.</p></section>
{:else}
  <section class="page">
    <div class="page-header">
      <h1>Инциденты</h1>
      <p>Здесь собраны отклонения, служебные события и действия, которые нужно отработать оператору.</p>
    </div>
    <div class="ui-card panel">
      {#if $incidentStore.loading && $incidentStore.items.length === 0}<p>Загрузка инцидентов...</p>
      {:else if $incidentStore.error}<p>{$incidentStore.error}</p>
      {:else}<IncidentList items={$incidentStore.items} />{/if}
    </div>
  </section>
{/if}

<style>.panel,.restricted{padding:1rem}.page{display:grid;gap:1rem}.page-header h1,.page-header p{margin:0}</style>
