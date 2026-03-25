<script>
  import { onMount, onDestroy } from 'svelte';
  import Router from 'svelte-spa-router';

  import { sessionStore } from './stores/sessionStore.js';
  import { systemStore } from './stores/systemStore.js';
  import { roleStore } from './stores/roleStore.js';
  import { demoModeStore } from './stores/demoModeStore.js';
  import { operatorConnectionStore } from './stores/operatorConnectionStore.js';
  import { ensureOperatorShellData, OPERATOR_SHELL_REFETCH_POLICY, OPERATOR_SHELL_SHARED_DATA } from './stores/operatorShellOrchestrator.js';
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
  import ShellTopBar from './components/shell/ShellTopBar.svelte';
  import SystemFallbackBanner from './components/system/SystemFallbackBanner.svelte';
  import { ROUTE_COPY, SHELL_NAV_COPY } from './lib/operator/routeCopy.js';

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

  // NOTE: порядок primaryNav отражает operator workflow, а не технические домены.
  const primaryNav = [
    {
      href: ROUTE_COPY.today.href,
      label: ROUTE_COPY.today.label,
      description: ROUTE_COPY.today.navDescription,
      visible: (permissions) => permissions.taps_view || permissions.sessions_view,
    },
    {
      href: ROUTE_COPY.taps.href,
      label: ROUTE_COPY.taps.label,
      description: ROUTE_COPY.taps.navDescription,
      visible: (permissions) => permissions.taps_view,
    },
    {
      href: ROUTE_COPY.sessions.href,
      label: ROUTE_COPY.sessions.label,
      description: ROUTE_COPY.sessions.navDescription,
      visible: (permissions) => permissions.sessions_view,
    },
    {
      href: ROUTE_COPY.cardsGuests.href,
      label: ROUTE_COPY.cardsGuests.label,
      description: ROUTE_COPY.cardsGuests.navDescription,
      visible: (permissions) => permissions.cards_lookup,
    },
    {
      href: ROUTE_COPY.kegsBeverages.href,
      label: ROUTE_COPY.kegsBeverages.label,
      description: ROUTE_COPY.kegsBeverages.navDescription,
      visible: (permissions) => (
        permissions.inventory_view
        || permissions.kegs_manage
        || permissions.beverages_catalog_manage
        || permissions.settings_manage
      ),
    },
    {
      href: ROUTE_COPY.incidents.href,
      label: ROUTE_COPY.incidents.label,
      description: ROUTE_COPY.incidents.navDescription,
      visible: (permissions) => permissions.incidents_view,
    },
    {
      href: ROUTE_COPY.tapScreens.href,
      label: ROUTE_COPY.tapScreens.label,
      description: ROUTE_COPY.tapScreens.navDescription,
      visible: (permissions) => permissions.display_override,
    },
    {
      href: ROUTE_COPY.system.href,
      label: ROUTE_COPY.system.label,
      description: ROUTE_COPY.system.navDescription,
      visible: (permissions) => permissions.system_health_view,
    },
  ];

  const supportNav = [
    {
      href: ROUTE_COPY.settings.href,
      label: ROUTE_COPY.settings.label,
      description: ROUTE_COPY.settings.navDescription,
      visible: (permissions) => permissions.settings_manage,
    },
    {
      href: ROUTE_COPY.help.href,
      label: ROUTE_COPY.help.label,
      description: ROUTE_COPY.help.navDescription,
      visible: (permissions) => permissions.system_health_view,
    },
  ];

  let shellDataLoadAttempted = false;

  function syncActiveRoute() {
    operatorConnectionStore.setActiveRoute(window.location.hash.replace(/^#/, '') || '/today');
  }

  onMount(() => {
    let disposed = false;
    syncActiveRoute();
    window.addEventListener('hashchange', syncActiveRoute);

    (async () => {
      await initializeBackendBaseUrl();
      if (disposed) {
        return;
      }

      systemStore.startPolling();
    })();

    return () => {
      disposed = true;
      window.removeEventListener('hashchange', syncActiveRoute);
    };
  });


  $: visiblePrimaryNav = primaryNav.filter((item) => item.visible($roleStore.permissions));
  $: visibleSupportNav = supportNav.filter((item) => item.visible($roleStore.permissions));

  onDestroy(() => {
    systemStore.stopPolling();
  });

  $: if ($sessionStore.token && !shellDataLoadAttempted) {
    shellDataLoadAttempted = true;
    ensureOperatorShellData({ reason: OPERATOR_SHELL_REFETCH_POLICY.defaultReason }).catch((error) => {
      const message = error?.message || error?.toString?.() || '';
      if (message.includes('Требуется повторный вход') || message.includes('Could not validate credentials')) {
        sessionStore.logout();
        return;
      }
      console.error('[App] Не удалось прогреть operator-shell shared data', OPERATOR_SHELL_SHARED_DATA, error);
    });
  }

  $: if (!$sessionStore.token && shellDataLoadAttempted) {
    shellDataLoadAttempted = false;
  }
</script>

{#if $sessionStore.token}
  <div class="app-shell" class:emergency-active={$systemStore.emergencyStop}>
    {#if $systemStore.emergencyStop}
      <div class="emergency-banner">
        ВНИМАНИЕ: АКТИВНА ЭКСТРЕННАЯ ОСТАНОВКА. НОВЫЕ НАЛИВЫ ЗАБЛОКИРОВАНЫ.
      </div>
    {/if}

    <ShellTopBar />
    <SystemFallbackBanner demoMode={$demoModeStore} />

    <div class="workspace-grid">
      <aside class="left-rail ui-card">
        <div class="nav-group rail-intro">
          <div class="nav-title">{SHELL_NAV_COPY.primaryIntroTitle}</div>
          <p>{SHELL_NAV_COPY.primaryIntro}</p>
        </div>

        <div class="nav-group">
          <div class="nav-title">{SHELL_NAV_COPY.primaryTitle}</div>
          <nav aria-label="Главная навигация">
            {#each visiblePrimaryNav as item}
              <a href={item.href}>
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </a>
            {/each}
          </nav>
        </div>

        {#if visibleSupportNav.length > 0}
          <div class="support-block">
            <div class="nav-title">{SHELL_NAV_COPY.supportTitle}</div>
            <p>{SHELL_NAV_COPY.supportIntro}</p>
            <nav aria-label="Настройки, поддержка и регламенты">
              {#each visibleSupportNav as item}
                <a href={item.href} class="support-link">
                  <strong>{item.label}</strong>
                  <span>{item.description}</span>
                </a>
              {/each}
            </nav>
          </div>
        {/if}
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

  .rail-intro {
    gap: 6px;
  }

  .rail-intro p {
    margin: 0;
    color: var(--text-secondary);
    line-height: 1.45;
    font-size: 0.92rem;
  }

  .support-block {
    margin-top: auto;
    display: grid;
    gap: 10px;
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
    padding: 12px;
    display: grid;
    gap: 4px;
    transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease, opacity 0.16s ease;
  }

  nav a strong {
    font-size: 0.96rem;
  }

  nav a span {
    color: var(--text-secondary);
    font-size: 0.84rem;
    line-height: 1.35;
  }

  nav a:hover,
  nav a:focus-visible { background: #eaf1ff; }

  .support-link {
    background: color-mix(in srgb, var(--bg-surface-muted) 72%, transparent);
    border-style: dashed;
  }
</style>
