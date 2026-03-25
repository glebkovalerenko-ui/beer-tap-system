<script>
  import { onMount, onDestroy } from 'svelte';
  import Router from 'svelte-spa-router';

  import { sessionStore } from './stores/sessionStore.js';
  import { systemStore } from './stores/systemStore.js';
  import { roleStore } from './stores/roleStore.js';
  import { demoModeStore } from './stores/demoModeStore.js';
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
      href: '#/today',
      label: 'Сегодня',
      description: 'Открыть текущие задачи, очередь внимания и быстрые действия смены.',
      visible: (permissions) => permissions.taps_view || permissions.sessions_view,
    },
    {
      href: '#/taps',
      label: 'Краны',
      description: 'Следить за линиями, статусами и рабочими действиями у стойки.',
      visible: (permissions) => permissions.taps_view,
    },
    {
      href: '#/sessions',
      label: 'Сессии',
      description: 'Сопровождать активные визиты и разбирать историю обслуживания.',
      visible: (permissions) => permissions.sessions_view,
    },
    {
      href: '#/cards-guests',
      label: 'Карты и гости',
      description: 'Найти гостя, проверить карту и безопасно продолжить обслуживание.',
      visible: (permissions) => permissions.cards_lookup,
    },
    {
      href: '#/kegs-beverages',
      label: 'Кеги и напитки',
      description: 'Рабочая подготовка ассортимента и линии налива.',
      visible: (permissions) => (
        permissions.inventory_view
        || permissions.kegs_manage
        || permissions.beverages_catalog_manage
        || permissions.settings_manage
      ),
    },
    {
      href: '#/incidents',
      label: 'Инциденты',
      description: 'Фиксировать проблемы смены и отслеживать эскалации.',
      visible: (permissions) => permissions.incidents_view,
    },
    {
      href: '#/tap-screens',
      label: 'Экраны кранов',
      description: 'Сервисное управление display-сценариями.',
      visible: (permissions) => permissions.display_override,
    },
    {
      href: '#/system',
      label: 'Система',
      description: 'Проверить health, устройства и синхронизацию, когда сервис проседает.',
      visible: (permissions) => permissions.system_health_view,
    },
  ];

  const supportNav = [
    {
      href: '#/settings',
      label: 'Настройки',
      description: 'Редкие административные действия и управление параметрами продукта.',
      visible: (permissions) => permissions.settings_manage,
    },
    {
      href: '#/help',
      label: 'Справка / регламенты',
      description: 'Регламенты смены, SOP и сервисные entry-point\'ы для старшего/инженера.',
      visible: (permissions) => permissions.system_health_view,
    },
  ];

  let shellDataLoadAttempted = false;

  onMount(() => {
    let disposed = false;

    (async () => {
      await initializeBackendBaseUrl();
      if (disposed) {
        return;
      }

      systemStore.startPolling();
    })();

    return () => {
      disposed = true;
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
          <div class="nav-title">Рабочая навигация</div>
          <p>Откройте раздел, где оператору нужно работать прямо сейчас. Сервисные и редкие инструменты убраны из постоянной зоны.</p>
        </div>

        <div class="nav-group">
          <div class="nav-title">Основные разделы</div>
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
            <div class="nav-title">Настройки и справка</div>
            <p>Внизу собраны редкие административные действия и отдельный вход в справку / регламенты, чтобы не смешивать их с operator shell.</p>
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
