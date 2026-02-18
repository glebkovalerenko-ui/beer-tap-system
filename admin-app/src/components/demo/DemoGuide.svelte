<script>
  import { demoGuideStore } from '../../stores/demoGuideStore.js';

  const steps = [
    { title: '1. Ценность в цифрах', text: 'На дашборде смотрим KPI-блок для владельца: выручка, чек, риски.' , link: '#/'},
    { title: '2. Операционный контроль', text: 'Проверяем состояние кранов и кег, снимаем риски пустых линий.', link: '#/taps-kegs'},
    { title: '3. Управление гостями', text: 'Показываем цикл клиента: создание, карта, пополнение.', link: '#/guests'},
  ];
</script>

{#if $demoGuideStore.open}
  <div class="overlay" role="dialog" aria-modal="true" aria-label="Guided demo mode">
    <section class="panel ui-card">
      <header>
        <h2>Guided demo mode</h2>
        <button class="close" on:click={() => demoGuideStore.close()}>Закрыть</button>
      </header>
      <p class="ui-muted">Пошаговый сценарий презентации для инвестора или владельца бара.</p>
      <ol>
        {#each steps as step}
          <li>
            <h3>{step.title}</h3>
            <p>{step.text}</p>
            <a href={step.link}>Перейти к шагу</a>
          </li>
        {/each}
      </ol>
    </section>
  </div>
{/if}

<style>
  .overlay {
    position: fixed; inset: 0; z-index: 2100; background: rgba(16, 24, 40, 0.45);
    display: flex; justify-content: center; align-items: center; padding: 1rem;
  }
  .panel { width: min(760px, 96vw); padding: 1rem; }
  header { display: flex; justify-content: space-between; align-items: center; }
  h2 { margin: 0; }
  ol { padding-left: 1.2rem; display: grid; gap: 0.75rem; }
  li h3 { margin: 0 0 0.3rem; font-size: 1rem; }
  li p { margin: 0 0 0.35rem; color: var(--text-secondary); }
  a { color: var(--brand); text-decoration: none; font-weight: 600; }
  .close { background: #eef2ff; color: #1e40af; }
</style>
