<!-- src/routes/Dashboard.svelte -->
<script>
  // Импортируем все необходимые сторы и компоненты
  import { tapStore } from '../stores/tapStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { sessionStore } from '../stores/sessionStore.js';

  import NfcReaderStatus from '../components/system/NfcReaderStatus.svelte';

  import TapGrid from '../components/taps/TapGrid.svelte';
  import PourFeed from '../components/pours/PourFeed.svelte';

  let initialLoadAttempted = false;

  // Лучшая практика: Дашборд, как и другие страницы, сам отвечает
  // за инициирование загрузки данных, которые ему нужны.
  // pourStore начнет опрос автоматически благодаря своей внутренней логике,
  // а вот taps нужно "пнуть" один раз.
  $: {
    if ($sessionStore.token && !initialLoadAttempted) {
      console.log("Dashboard: токен доступен, инициируем загрузку данных для кранов.");
      tapStore.fetchTaps();
      // pourStore.fetchPours() вызывать не нужно, он сам начнет работать,
      // как только увидит токен в sessionStore.
      initialLoadAttempted = true;
    }
  }
</script>

<div class="page-header">
  <h1>Dashboard</h1>
  <!-- Здесь можно будет добавить виджеты с ключевыми показателями -->
</div>

<div class="dashboard-layout">
  <!-- Основная секция со статусом оборудования -->
  <section class="main-section">
    <h2>Equipment Status</h2>
    <!-- Добавляем виджет статуса NFC +++ -->
    <div class="status-widgets-grid">
      <NfcReaderStatus />
      <!-- Здесь можно будет добавить другие виджеты, например, статус контроллеров -->
    </div>

    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Loading tap statuses...</p>
    {:else if $tapStore.error}
      <p class="error">Error loading taps: {$tapStore.error}</p>
    {:else}
      <TapGrid taps={$tapStore.taps} />
    {/if}
  </section>

  <!-- Боковая секция с живой лентой событий -->
  <aside class="sidebar-section">
    {#if $pourStore.loading && $pourStore.pours.length === 0}
      <p>Loading live feed...</p>
    {:else if $pourStore.error}
       <p class="error">Error loading feed: {$pourStore.error}</p>
    {:else}
      <PourFeed pours={$pourStore.pours} />
    {/if}
  </aside>
</div>

<style>
  .page-header {
    margin-bottom: 1.5rem;
  }
  .page-header h1 {
    margin: 0;
  }
  .dashboard-layout {
    display: grid;
    grid-template-columns: 2fr 1fr; /* Основная секция занимает 2/3, сайдбар 1/3 */
    gap: 1.5rem;
    /* Устанавливаем высоту, чтобы внутренние блоки могли скроллиться */
    height: calc(100vh - 8rem); 
  }
  .status-widgets-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem; /* Отступ до сетки кранов */
  }
  .main-section h2, .sidebar-section h2 {
    margin-top: 0;
    margin-bottom: 1rem;
  }
  .sidebar-section {
    /* Это нужно, чтобы PourFeed мог растянуться на всю высоту */
    display: flex;
    flex-direction: column;
  }
  .error {
    color: red;
  }
</style>