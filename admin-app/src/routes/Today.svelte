<script>
  import { incidentStore } from '../stores/incidentStore.js';
  import { systemStore } from '../stores/systemStore.js';
  import IncidentList from '../components/incidents/IncidentList.svelte';

  $: actionableIncidents = ($incidentStore.items || []).filter((item) => item.status !== 'closed').slice(0, 5);
  $: actionableSystems = ($systemStore.subsystems || []).filter((item) => item.state !== 'ok').slice(0, 4);
</script>

<section class="today-page">
  <div class="hero ui-card">
    <div><span class="eyebrow">Today</span><h1>Top actionable subset</h1></div>
    <div class="stats">
      <article><span>Open incidents</span><strong>{actionableIncidents.length}</strong></article>
      <article><span>System warnings</span><strong>{actionableSystems.length}</strong></article>
      <article><span>Emergency stop</span><strong>{$systemStore.emergencyStop ? 'ON' : 'OFF'}</strong></article>
    </div>
  </div>

  <div class="content-grid">
    <section class="ui-card panel">
      <div class="section-head"><h2>Incidents</h2><a href="#/incidents">Открыть полный разбор</a></div>
      <IncidentList items={actionableIncidents} />
    </section>
    <section class="ui-card panel">
      <div class="section-head"><h2>System</h2><a href="#/system">Открыть System screen</a></div>
      {#if actionableSystems.length === 0}
        <p>Все ключевые подсистемы в норме.</p>
      {:else}
        <ul class="system-list">{#each actionableSystems as item (item.name)}<li><strong>{item.name}</strong><span>{item.label}</span><small>{item.detail || item.state}</small></li>{/each}</ul>
      {/if}
    </section>
  </div>
</section>

<style>
.today-page{display:grid;gap:1rem}.hero,.panel{padding:1rem}.hero h1{margin:.25rem 0 0}.eyebrow{font-size:.8rem;color:var(--text-secondary);text-transform:uppercase}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.stats article span{display:block;color:var(--text-secondary)}.content-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:1rem}.section-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:1rem}.section-head h2{margin:0}.system-list{margin:0;padding-left:1rem}.system-list li{margin-bottom:.75rem}.system-list small{display:block;color:var(--text-secondary)}
</style>
