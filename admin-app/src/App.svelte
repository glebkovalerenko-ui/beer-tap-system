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
  import Login from './routes/Login.svelte';

  import ToastContainer from './components/feedback/ToastContainer.svelte';
  import ConfirmDialog from './components/feedback/ConfirmDialog.svelte';
  import DemoGuide from './components/demo/DemoGuide.svelte';
  import ActivityTrail from './components/system/ActivityTrail.svelte';
  import ShellTopBar from './components/shell/ShellTopBar.svelte';
  import SystemFallbackBanner from './components/system/SystemFallbackBanner.svelte';

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
    '*': Today,
  };

  const primaryNav = [
    { href: '#/today', label: 'Today', visible: (permissions) => permissions.taps_view || permissions.sessions_view },
    { href: '#/taps', label: 'Taps', visible: (permissions) => permissions.taps_view },
    { href: '#/sessions', label: 'Sessions', visible: (permissions) => permissions.sessions_view },
    { href: '#/cards-guests', label: 'CardsGuests', visible: (permissions) => permissions.cards_manage },
    { href: '#/incidents', label: 'Incidents', visible: (permissions) => permissions.incidents_manage },
  ];

  const secondaryNav = [
    { href: '#/tap-screens', label: 'TapScreens', visible: (permissions) => permissions.display_override },
    { href: '#/kegs-beverages', label: 'KegsBeverages', visible: (permissions) => permissions.settings_manage },
    { href: '#/system', label: 'System', visible: (permissions) => permissions.system_view },
  ];

  let online = typeof navigator !== 'undefined' ? navigator.onLine : true;
  let shiftLoadAttempted = false;

  $: if ($sessionStore.token && !shiftLoadAttempted) {
    shiftStore.fetchCurrent();
    shiftLoadAttempted = true;
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

    <ShellTopBar title="Operator workspace" />
    <SystemFallbackBanner demoMode={$demoModeStore} {online} nfcStatus={$nfcReaderStore.status} />

    <div class="workspace-grid">
      <aside class="left-rail ui-card">
        <div class="nav-group">
          <div class="nav-title">Операторские сценарии</div>
          <nav aria-label="Главная навигация">
            {#each primaryNav as item}
              {#if item.visible($roleStore.permissions)}
                <a href={item.href}>{item.label}</a>
              {/if}
            {/each}
          </nav>
        </div>

        <div class="nav-group secondary">
          <div class="nav-title">Внизу shell</div>
          <nav aria-label="Вторичная навигация">
            {#each secondaryNav as item}
              {#if item.visible($roleStore.permissions)}
                <a href={item.href}>{item.label}</a>
              {/if}
            {/each}
          </nav>
        </div>

        <button class="demo-button" on:click={() => demoGuideStore.open()}>▶ Операторский walkthrough</button>
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
  }

  nav a:hover { background: #eaf1ff; }

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
