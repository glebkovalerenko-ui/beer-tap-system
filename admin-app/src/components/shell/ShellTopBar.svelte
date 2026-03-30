<script>
  import { onDestroy, onMount } from 'svelte';

  import { canonicalVisitStatusLabel } from '../../lib/operator/visitStatus.js';
  import { formatDateTimeRu, formatTimeRu } from '../../lib/formatters.js';
  import { navigateWithFocus } from '../../lib/actionRouting.js';
  import { confirmShiftAction } from '../../lib/shiftActionConfirm.js';
  import { healthStateLabel } from '../../lib/healthStatus.js';
  import { ensureOperatorShellData } from '../../stores/operatorShellOrchestrator.js';
  import { operatorSearchStore } from '../../stores/operatorSearchStore.js';
  import { roleStore } from '../../stores/roleStore.js';
  import { sessionStore } from '../../stores/sessionStore.js';
  import { shiftStore } from '../../stores/shiftStore.js';
  import { systemStore } from '../../stores/systemStore.js';
  import { tapStore } from '../../stores/tapStore.js';
  import { uiStore } from '../../stores/uiStore.js';
  import { visitStore } from '../../stores/visitStore.js';

  import ShellStatusPills from './ShellStatusPills.svelte';

  let now = new Date();
  let searchQuery = '';
  let searchOpen = false;
  let debounceTimer = null;

  const GROUP_LABELS = {
    guests: 'Гости',
    visits: 'Визиты',
    taps: 'Краны',
    cards: 'Карты',
    pours: 'Наливы',
    kegs: 'Кеги',
  };

  function shiftStatusText() {
    if ($shiftStore.isOpen) {
      return $shiftStore.shift?.opened_at ? `Открыта с ${formatDateTimeRu($shiftStore.shift.opened_at)}` : 'Смена открыта';
    }
    if ($shiftStore.shift?.closed_at) {
      return `Закрыта ${formatDateTimeRu($shiftStore.shift.closed_at)}`;
    }
    return 'Смена закрыта';
  }

  async function handleOpenShift() {
    const confirmed = await confirmShiftAction({ uiStore, shiftState: $shiftStore, action: 'open' });
    if (!confirmed) return;
    try {
      await shiftStore.openShift();
      await ensureOperatorShellData({ reason: 'shift-open-close', force: true });
      uiStore.notifySuccess('Смена открыта');
    } catch (error) {
      uiStore.notifyError(error?.message || error?.toString?.() || 'Не удалось открыть смену');
    }
  }

  async function handleCloseShift() {
    const confirmed = await confirmShiftAction({ uiStore, shiftState: $shiftStore, action: 'close' });
    if (!confirmed) return;
    try {
      await shiftStore.closeShift();
      await ensureOperatorShellData({ reason: 'shift-open-close', force: true });
      uiStore.notifySuccess('Смена закрыта');
    } catch (error) {
      uiStore.notifyError(error?.message || error?.toString?.() || 'Не удалось закрыть смену');
    }
  }

  function handleSearchInput(value) {
    searchQuery = value;
    searchOpen = Boolean(value.trim());
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      operatorSearchStore.search(value, { limit: 5 }).catch(() => {});
    }, 180);
  }

  function clearSearch() {
    searchQuery = '';
    searchOpen = false;
    operatorSearchStore.clear();
  }

  function openSearchResult(item) {
    navigateWithFocus({
      target: item.kind === 'visit' ? 'visit' : item.kind,
      route: `/${item.route}`,
      guestId: item.guest_id,
      visitId: item.visit_id,
      tapId: item.tap_id,
      cardUid: item.card_uid,
      pourRef: item.pour_ref,
      kegId: item.keg_id,
    });
    clearSearch();
  }

  function openQuickVisit() {
    const activeVisit = ($visitStore.activeVisits || [])[0];
    if (activeVisit?.visit_id) {
      navigateWithFocus({ target: 'visit', visitId: activeVisit.visit_id, tapId: activeVisit.active_tap_id });
      return;
    }
    window.location.hash = '/visits';
  }

  onMount(() => {
    const clockTimer = setInterval(() => {
      now = new Date();
    }, 1000);

    const clickHandler = (event) => {
      if (!event.target.closest('.quick-search')) {
        searchOpen = false;
      }
    };
    window.addEventListener('click', clickHandler);

    return () => {
      clearInterval(clockTimer);
      window.removeEventListener('click', clickHandler);
    };
  });

  onDestroy(() => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
  });

  $: overallState = $systemStore.health.overall || 'unknown';
  $: overallStateLabel = healthStateLabel(overallState, 'overall');
  $: operatorName = $sessionStore.user?.name || $sessionStore.user?.email || 'Текущий оператор';
  $: searchGroups = $operatorSearchStore.groups || [];
  $: activeVisitCount = ($visitStore.activeVisits || []).length;
  $: pouringCount = Number($tapStore.summary?.pouringCount || 0);
</script>

<header class="topbar ui-card">
  <section class="left-column">
    <button class="shift-brand" type="button" on:click={() => (window.location.hash = '/shift')}>
      <div class="eyebrow">Рабочая смена</div>
      <div class="brand-row">
        <strong>{$shiftStore.isOpen ? 'Смена открыта' : 'Смена закрыта'}</strong>
        <span class="overall-health" data-tone={overallState}>{overallStateLabel}</span>
      </div>
      <p>{shiftStatusText()} · {activeVisitCount} активных · {pouringCount} льют</p>
    </button>

    <div class="status-strip">
      <ShellStatusPills />
    </div>

    <div class="quick-search">
      <label class="sr-only" for="operator-quick-search">Быстрый поиск</label>
      <input
        id="operator-quick-search"
        type="text"
        bind:value={searchQuery}
        placeholder="Гость, карта, визит, кран"
        on:input={(event) => handleSearchInput(event.currentTarget.value)}
        on:focus={() => {
          if (searchQuery.trim()) searchOpen = true;
        }}
      />

      {#if searchOpen}
        <div class="search-popover ui-card">
          {#if $operatorSearchStore.loading}
            <p class="muted">Ищем по операторским разделам...</p>
          {:else if $operatorSearchStore.error}
            <p class="error">{$operatorSearchStore.error}</p>
          {:else if searchGroups.length === 0}
            <p class="muted">Начните с 2+ символов, чтобы искать по гостям, визитам, кранам, картам, наливам и кегам.</p>
          {:else}
            {#each searchGroups as group}
              <section class="search-group">
                <div class="search-group-head">
                  <strong>{GROUP_LABELS[group.key] || group.label}</strong>
                  <span>{group.items.length}</span>
                </div>
                <div class="search-result-list">
                  {#each group.items as item}
                    <button class="search-result" on:click={() => openSearchResult(item)}>
                      <div>
                        <strong>{item.title}</strong>
                        {#if item.subtitle}<small>{item.subtitle}</small>{/if}
                      </div>
                      <div class="search-meta">
                        {#if item.canonical_visit_status}
                          <span class="status-pill">{canonicalVisitStatusLabel(item.canonical_visit_status)}</span>
                        {/if}
                        {#if item.meta}<small>{item.meta}</small>{/if}
                      </div>
                    </button>
                  {/each}
                </div>
              </section>
            {/each}
          {/if}
        </div>
      {/if}
    </div>
  </section>

  <section class="right-column">
    <div class="clock-card">
      <span class="time-value">{formatTimeRu(now.toISOString())}</span>
      <span class="time-date">{formatDateTimeRu(now.toISOString())}</span>
    </div>

    <div class="action-cluster">
      {#if $shiftStore.isOpen}
        <button on:click={handleCloseShift} disabled={$shiftStore.loading}>Закрыть смену</button>
      {:else}
        <button on:click={handleOpenShift} disabled={$shiftStore.loading}>Открыть смену</button>
      {/if}
      {#if $roleStore.permissions.incidents_view}
        <button class="ghost critical" on:click={() => (window.location.hash = '/incidents')}>Инциденты</button>
      {/if}
      <button class="ghost" on:click={() => (window.location.hash = '/taps')}>Краны</button>
      <button class="ghost" on:click={openQuickVisit}>Визиты</button>
    </div>

    <div class="operator-card">
      <div>
        <span class="eyebrow">Оператор</span>
        <strong>{operatorName}</strong>
        <small>Роль: {$roleStore.label}</small>
      </div>
      <button class="ghost" on:click={() => sessionStore.logout()}>Выйти</button>
    </div>
  </section>
</header>

<style>
  .topbar {
    margin: 0 12px;
    padding: 10px 12px;
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.95fr);
    gap: 10px;
    border-radius: 14px;
    align-items: start;
  }
  .left-column, .right-column, .quick-search, .operator-card { display: grid; gap: 8px; }
  .shift-brand {
    display: grid;
    gap: 4px;
    text-align: left;
    padding: 0;
    background: transparent;
    color: inherit;
    border: 0;
  }
  .shift-brand p, .time-date, .operator-card small, .muted { margin: 0; color: var(--text-secondary); }
  .brand-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }
  .eyebrow {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
  }
  .overall-health {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 3px 9px;
    font-size: 0.74rem;
    font-weight: 700;
    background: #eef2f8;
    border: 1px solid #d7e2f1;
    color: #29405f;
  }
  .overall-health[data-tone='ok'] { background: #e9f8ef; border-color: #bde8cc; color: #116d3a; }
  .overall-health[data-tone='warning'],
  .overall-health[data-tone='degraded'],
  .overall-health[data-tone='unknown'] { background: #fff8e9; border-color: #ffe1a3; color: #8d5b00; }
  .overall-health[data-tone='critical'],
  .overall-health[data-tone='error'],
  .overall-health[data-tone='offline'] { background: #ffeef0; border-color: #ffc6cc; color: #9e1f2c; }
  .status-strip { display: grid; }
  .quick-search { position: relative; }
  .quick-search input { width: 100%; }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  .search-popover {
    position: absolute;
    top: calc(100% + 8px);
    left: 0;
    right: 0;
    z-index: 20;
    padding: 10px;
    display: grid;
    gap: 10px;
    max-height: 420px;
    overflow: auto;
  }
  .search-group, .search-result-list { display: grid; gap: 8px; }
  .search-group-head {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    align-items: center;
  }
  .search-result {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    text-align: left;
    border: 1px solid var(--border-soft);
    border-radius: 12px;
    padding: 10px 12px;
    background: #fff;
    color: inherit;
  }
  .search-result small, .search-meta small { color: var(--text-secondary); }
  .search-meta {
    display: grid;
    gap: 4px;
    justify-items: end;
  }
  .status-pill {
    border-radius: 999px;
    padding: 4px 10px;
    background: #eef2ff;
    color: #3447a3;
    font-size: 0.78rem;
    font-weight: 700;
  }
  .clock-card {
    display: flex;
    justify-content: flex-end;
    align-items: baseline;
    gap: 8px;
    text-align: right;
  }
  .time-value {
    font-size: 1.15rem;
    font-weight: 800;
  }
  .time-date { font-size: 0.8rem; }
  .action-cluster {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .action-cluster button,
  .operator-card button {
    padding: 0.55rem 0.75rem;
  }
  .ghost { background: #edf2fb; color: #23416b; }
  .ghost.critical {
    background: #fff1f2;
    color: #9e1f2c;
    border: 1px solid #ffc6cc;
  }
  .operator-card {
    padding: 8px 10px;
    border-radius: 12px;
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
  }
  .error { color: var(--state-critical-text, #9e1f2c); }
  @media (max-width: 1100px) {
    .topbar { grid-template-columns: 1fr; }
    .clock-card { justify-content: flex-start; text-align: left; }
    .action-cluster { justify-content: flex-start; }
  }
  @media (max-width: 720px) {
    .operator-card, .search-result { grid-template-columns: 1fr; }
    .search-meta { justify-items: start; }
  }
</style>
