<script>
  import { onMount, onDestroy } from 'svelte';
  import Router from 'svelte-spa-router';

  import { sessionStore } from './stores/sessionStore.js';
  import { guestStore } from './stores/guestStore.js';
  import { systemStore } from './stores/systemStore.js';
  import { roleStore } from './stores/roleStore.js';
  import { demoGuideStore } from './stores/demoGuideStore.js';
  import { demoModeStore } from './stores/demoModeStore.js';
  import { nfcReaderStore } from './stores/nfcReaderStore.js';
  import { shiftStore } from './stores/shiftStore.js';
  import { initializeBackendBaseUrl } from './lib/config.js';

  import Today from './routes/Today.svelte';
  import Taps from './routes/Taps.svelte';
  import Sessions from './routes/Sessions.svelte';
  import CardsGuests from './routes/CardsGuests.svelte';
  import KegsBeverages from './routes/KegsBeverages.svelte';
  import Incidents from './routes/Incidents.svelte';
  import TapScreens from './routes/TapScreens.svelte';
  import System from './routes/System.svelte';
  import Settings from './routes/Settings.svelte';
  import Help from './routes/Help.svelte';
  import Login from './routes/Login.svelte';

  import ToastContainer from './components/feedback/ToastContainer.svelte';
  import ConfirmDialog from './components/feedback/ConfirmDialog.svelte';
  import DemoGuide from './components/demo/DemoGuide.svelte';
  import ActivityTrail from './components/system/ActivityTrail.svelte';
  import ShellTopBar from './components/shell/ShellTopBar.svelte';
  import SystemFallbackBanner from './components/system/SystemFallbackBanner.svelte';
  import DebugManagementEntry from './components/system/DebugManagementEntry.svelte';

  const routes = {
    '/': Today,
    '/today': Today,
    '/taps': Taps,
    '/sessions': Sessions,
    '/sessions/history': Sessions,
    '/cards-guests': CardsGuests,
    '/kegs-beverages': KegsBeverages,
    '/incidents': Incidents,
    '/tap-screens': TapScreens,
    '/system': System,
    '/settings': Settings,
    '/help': Help,
    '*': Today,
  };

  const primaryNav = [
    { href: '#/today', label: 'Сегодня', visible: (permissions) => permissions.taps_view || permissions.sessions_view },
    { href: '#/taps', label: 'Краны', visible: (permissions) => permissions.taps_view },
    { href: '#/sessions', label: 'Сессии', visible: (permissions) => permissions.sessions_view },
    { href: '#/cards-guests', label: 'Карты и гости', visible: (permissions) => permissions.cards_lookup },
    { href: '#/kegs-beverages', label: 'Кеги и напитки', visible: (permissions) => permissions.settings_manage },
    { href: '#/incidents', label: 'Инциденты', visible: (permissions) => permissions.incidents_manage },
    { href: '#/tap-screens', label: 'Экраны кранов', visible: (permissions) => permissions.display_override },
    { href: '#/system', label: 'Система', visible: (permissions) => permissions.system_health_view },
  ];

  const supportNav = [
    { href: '#/help', label: 'Справка / регламенты', visible: (permissions) => permissions.system_health_view, tone: 'support' },
    { href: '#/settings', label: 'Настройки', visible: (permissions) => permissions.settings_manage, tone: 'muted' },
  ];

  let online = typeof navigator !== 'undefined' ? navigator.onLine : true;
  let shiftLoadAttempted = false;

  $: if ($sessionStore.token && !shiftLoadAttempted) {
    shiftLoadAttempted = true;
    shiftStore.fetchCurrent().catch((error) => {
      const message = error?.message || error?.toString?.() || '';
      if (message.includes('Требуется повторный вход') || message.includes('Could not validate credentials')) {
        sessionStore.logout();
        return;
      }

      console.error('[App] Не удалось загрузить текущую смену', error);
    });
  }

  $: if (!$sessionStore.token && shiftLoadAttempted) {
    shiftStore.reset();
    shiftLoadAttempted = false;
  }

  const updateOnline = () => {
    online = navigator.onLine;
  };

  onMount(() => {
    let disposed = false;

    (async () => {
      await initializeBackendBaseUrl();
      if (disposed) {
        return;
      }

      systemStore.startPolling();
      if ($guestStore.guests.length === 0 && !$guestStore.loading) {
        guestStore.fetchGuests();
      }
    })();

    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);

    return () => {
      disposed = true;
    };
  });


  $: visiblePrimaryNav = primaryNav.filter((item) => item.visible($roleStore.permissions));
  $: visibleSupportNav = supportNav.filter((item) => item.visible($roleStore.permissions));

  onDestroy(() => {
    systemStore.stopPolling();
    window.removeEventListener('online', updateOnline);
    window.removeEventListener('offline', updateOnline);
  });
</script>

{#if $sessionStore.token}
  <div class="app-shell" class:emergency-active={$systemStore.emergencyStop}>
    {#if $systemStore.emergencyStop}
      <div class="emergency-banner">
        ВНИМАНИЕ: АКТИВНА ЭКСТРЕННАЯ ОСТАНОВКА. НОВЫЕ НАЛИВЫ ЗАБЛОКИРОВАНЫ.
      </div>
    {/if}

    <ShellTopBar />
    <SystemFallbackBanner demoMode={$demoModeStore} {online} nfcStatus={$nfcReaderStore.status} />

    <div class="workspace-grid">
      <aside class="left-rail ui-card">
        <div class="nav-group">
          <div class="nav-title">Основные разделы</div>
          <nav aria-label="Главная навигация">
            {#each visiblePrimaryNav as item}
              <a href={item.href}>{item.label}</a>
            {/each}
          </nav>
        </div>

        {#if visibleSupportNav.length > 0}
          <div class="nav-group secondary">
            <div class="nav-title">Поддержка</div>
            <nav aria-label="Дополнительные разделы">
              {#each visibleSupportNav as item}
                <a href={item.href} class:muted-link={item.tone === 'muted'}>{item.label}</a>
              {/each}
            </nav>
          </div>
        {/if}

        <button class="demo-button" on:click={() => demoGuideStore.open()}>▶ Показать сценарий обучения</button>
        <DebugManagementEntry />
        <ActivityTrail />
      </aside>

      <main class="main-content ui-card">
        <div class="page-scroll">
          <Router {routes} />
        </div>
      </main>
    </div>
  </div>
{:else}
  <Login />
{/if}

<ToastContainer />
<ConfirmDialog />
<DemoGuide />

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
    height: 100vh;
    overflow: hidden;
    font-size: 16px;
    background: var(--bg-app);
    color: var(--text-primary);
  }

  .app-shell {
    display: flex;
    flex-direction: column;
    height: 100vh;
    gap: 10px;
  }

  .workspace-grid {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 12px;
    height: calc(100vh - 88px);
    padding: 0 12px 12px;
    box-sizing: border-box;
  }

  .left-rail {
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    overflow: hidden;
  }

  .nav-group {
    display: grid;
    gap: 10px;
  }

  .secondary {
    margin-top: auto;
  }

  .nav-title {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-secondary);
  }

  nav {
    display: grid;
    gap: 8px;
  }

  nav a {
    text-decoration: none;
    color: var(--text-primary);
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    padding: 10px;
    font-weight: 600;
    transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease, opacity 0.16s ease;
  }

  nav a:hover,
  nav a:focus-visible { background: #eaf1ff; }

  .secondary nav a {
    color: var(--text-secondary);
    background: color-mix(in srgb, var(--bg-surface-muted) 82%, transparent);
    border-color: color-mix(in srgb, var(--border-soft) 88%, transparent);
  }

  .secondary nav a.muted-link {
    background: color-mix(in srgb, var(--bg-surface-muted) 58%, transparent);
    border-style: dashed;
    opacity: 0.9;
  }

  .secondary nav a:hover,
  .secondary nav a:focus-visible {
    color: var(--text-primary);
    opacity: 1;
  }

  .main-content { overflow: hidden; }

  .page-scroll {
    overflow-y: auto;
    padding: var(--space-4);
    height: 100%;
    box-sizing: border-box;
  }

  .demo-button { width: 100%; background: #eef3ff; color: #1849a9; }

  .emergency-banner {
    background-color: var(--danger);
    color: white;
    text-align: center;
    padding: 0.5rem;
    font-weight: bold;
    width: 100%;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1000;
  }

  .app-shell.emergency-active { padding-top: 2.5rem; }

  :global(button) {
    font-size: 0.95rem;
    padding: 0.6rem 1rem;
    border-radius: var(--radius-sm);
    border: 1px solid rgba(0,0,0,0.08);
    background: var(--brand);
    color: white;
    cursor: pointer;
    transition: transform 0.06s ease, filter 0.06s ease, box-shadow 0.06s ease;
    box-shadow: 0 1px 0 rgba(0,0,0,0.02);
  }

  :global(button:hover:not(:disabled)) { filter: brightness(0.95); }
  :global(button:active:not(:disabled)) { transform: scale(0.98); }
  :global(button:disabled) { opacity: 0.6; cursor: not-allowed; filter: none; }

  :global(input, textarea, select) {
    font-size: 0.95rem;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-soft);
    box-sizing: border-box;
    background: #fff;
  }
</style>
