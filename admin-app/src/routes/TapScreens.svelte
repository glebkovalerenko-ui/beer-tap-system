<script>
  // @ts-nocheck
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import Modal from '../components/common/Modal.svelte';
  import TapDisplaySettingsModal from '../components/taps/TapDisplaySettingsModal.svelte';
  import { buildTapGuestDisplaySnapshot } from '../lib/formatters.js';
  import { roleStore } from '../stores/roleStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';

  let initialLoadAttempted = false;
  let focusedTap = null;
  let isTapDisplayModalOpen = false;
  let displayConfigs = {};
  let displayConfigErrors = {};
  const requestedTapConfigIds = new Set();

  $: if ($sessionStore.token && !initialLoadAttempted) {
    tapStore.fetchTaps();
    initialLoadAttempted = true;
  }

  $: if (focusedTap) {
    focusedTap = $tapStore.taps.find((item) => item.tap_id === focusedTap.tap_id) || focusedTap;
  }

  $: if ($roleStore.permissions.display_override && $tapStore.taps.length) {
    hydrateDisplayConfigs($tapStore.taps);
  }

  onMount(() => {
    const token = get(sessionStore).token;
    if (token && !initialLoadAttempted) {
      tapStore.fetchTaps();
      initialLoadAttempted = true;
    }

    const focusTapId = sessionStorage.getItem('tapScreens.focusTapId');
    if (focusTapId) {
      sessionStorage.removeItem('tapScreens.focusTapId');
      const openWhenReady = () => {
        const target = $tapStore.taps.find((item) => String(item.tap_id) === String(focusTapId));
        if (target) {
          openDisplaySettings(target);
          return true;
        }
        return false;
      };

      if (!openWhenReady()) {
        const unsubscribe = tapStore.subscribe((state) => {
          if (state.taps?.length && openWhenReady()) {
            unsubscribe();
          }
        });
      }
    }
  });

  async function hydrateDisplayConfigs(taps) {
    const pending = taps.filter((tap) => !requestedTapConfigIds.has(tap.tap_id));
    if (!pending.length) return;

    pending.forEach((tap) => requestedTapConfigIds.add(tap.tap_id));

    await Promise.all(pending.map(async (tap) => {
      try {
        const config = await tapStore.fetchTapDisplayConfig(tap.tap_id);
        displayConfigs = {
          ...displayConfigs,
          [tap.tap_id]: config,
        };
      } catch (error) {
        displayConfigErrors = {
          ...displayConfigErrors,
          [tap.tap_id]: error?.message || 'Не удалось загрузить guest-facing override.',
        };
      }
    }));
  }

  function openDisplaySettings(tap) {
    if (!$roleStore.permissions.display_override) {
      uiStore.notifyWarning('Настройки экрана доступны только management / engineering ролям.');
      return;
    }
    focusedTap = tap;
    isTapDisplayModalOpen = true;
  }

  function closeDisplaySettings() {
    isTapDisplayModalOpen = false;
    focusedTap = null;
  }

  function handleDisplaySettingsSaved(event) {
    if (focusedTap?.tap_id && event.detail?.config) {
      displayConfigs = {
        ...displayConfigs,
        [focusedTap.tap_id]: event.detail.config,
      };
      delete displayConfigErrors[focusedTap.tap_id];
      displayConfigErrors = { ...displayConfigErrors };
    }
    closeDisplaySettings();
  }

  function snapshotFor(tap) {
    return buildTapGuestDisplaySnapshot(tap, displayConfigs[tap.tap_id]);
  }

  function runtimeClass(state) {
    if (['critical', 'error', 'offline'].includes(state)) return 'critical';
    if (['warning', 'degraded', 'unknown'].includes(state)) return 'warning';
    return 'ok';
  }
</script>

{#if !$roleStore.permissions.display_override}
  <section class="ui-card restricted">
    <h1>Гостевые экраны кранов</h1>
    <p>Текущая роль не предусматривает доступ к обзору гостевых экранов кранов.</p>
  </section>
{:else}
  <div class="page-header">
    <div>
      <h1>Гостевой экран конкретного крана</h1>
      <p>Ниже видно, какой сценарий, брендирование и runtime-состояние сейчас видит гость на каждом tap display.</p>
    </div>
  </div>

  <section class="screen-grid">
    <div class="section-header">
      <div>
        <h2>Что сейчас показывает каждый кран</h2>
        <p class="section-hint">Карточка сразу собирает summary из tap.operations, override экрана и beverage/display полей — без открытия модалки.</p>
      </div>
    </div>

    {#if $tapStore.loading && $tapStore.taps.length === 0}
      <p>Загрузка кранов...</p>
    {:else if $tapStore.error}
      <p class="error">Ошибка загрузки кранов: {$tapStore.error}</p>
    {:else if $tapStore.taps.length === 0}
      <p>Краны не найдены в системе.</p>
    {:else}
      <div class="display-list">
        {#each $tapStore.taps as tap (tap.tap_id)}
          {@const snapshot = snapshotFor(tap)}
          <article class="display-card ui-card">
            <div class="display-card__head">
              <div>
                <div class="eyebrow">Tap #{tap.tap_id}</div>
                <h3>{tap.display_name}</h3>
                <p>{tap.operations?.beverageName || 'Напиток не назначен'}</p>
              </div>
              <button class="secondary-action" on:click={() => openDisplaySettings(tap)}>Настройки экрана</button>
            </div>

            <section class="preview-card" aria-label={`Guest preview ${tap.display_name}`}>
              <div class="preview-topline">
                <span class:ok={snapshot.enabled} class:off={!snapshot.enabled} class="status-pill">
                  {snapshot.enabled ? 'Tap display включён' : 'Tap display выключен'}
                </span>
                <span class={`runtime-pill ${runtimeClass(snapshot.runtimeTone)}`}>
                  {snapshot.runtimeSummary}
                </span>
              </div>

              <div class="preview-copy">
                <div>
                  <span class="preview-label">Текущий guest-facing сценарий</span>
                  <strong>{snapshot.scenarioLabel}</strong>
                </div>
                <div>
                  <span class="preview-label">Гостевой заголовок</span>
                  <strong>{snapshot.title}</strong>
                  <p>{snapshot.subtitle}</p>
                </div>
              </div>

              <div class="preview-assets">
                <span class:supported={snapshot.background.present} class="asset-chip">{snapshot.background.source}</span>
                <span class:supported={snapshot.logo.present} class="asset-chip">{snapshot.logo.source}</span>
              </div>

              <div class="branding-summary">
                <span class="preview-label">Branding summary</span>
                <p>{snapshot.brandingSummary}</p>
              </div>
            </section>

            <dl class="meta-grid">
              <div><dt>Сценарий крана</dt><dd>{tap.operations?.productStateLabel || 'Нет данных'}</dd></div>
              <div><dt>Display runtime</dt><dd>{tap.operations?.displayStatus?.label || 'Нет данных'}</dd></div>
              <div><dt>Controller</dt><dd>{tap.operations?.controllerStatus?.label || 'Нет данных'}</dd></div>
              <div><dt>Operator note</dt><dd>{tap.operations?.operatorStateReason || tap.operations?.liveStatus || 'Нет данных'}</dd></div>
            </dl>

            <div class="operator-summary">
              <span class="preview-label">Operator-readable summary</span>
              <ul>
                {#each snapshot.operatorSummary as line}
                  <li>{line}</li>
                {/each}
                {#if displayConfigErrors[tap.tap_id]}
                  <li class="warning-text">Override summary недоступен: {displayConfigErrors[tap.tap_id]}</li>
                {/if}
              </ul>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
{/if}

{#if isTapDisplayModalOpen && focusedTap}
  <Modal on:close={closeDisplaySettings}>
    <TapDisplaySettingsModal
      tap={focusedTap}
      on:cancel={closeDisplaySettings}
      on:saved={handleDisplaySettingsSaved}
    />
  </Modal>
{/if}

<style>
  .page-header,
  .section-header,
  .display-card__head,
  .meta-grid div,
  .preview-topline {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }
  .page-header { margin-bottom: 1rem; }
  .page-header h1, .section-header h2, .display-card__head h3 { margin: 0; }
  .page-header p, .section-hint, .eyebrow, .display-card__head p, dt, .preview-label {
    margin: 0.3rem 0 0;
    color: var(--text-secondary, #64748b);
  }
  .screen-grid, .display-list, .display-card, .preview-card, .preview-copy, .operator-summary, .operator-summary ul {
    display: grid;
    gap: 1rem;
  }
  .display-list { grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
  .display-card { padding: 1rem; }
  .preview-card {
    padding: 1rem;
    border: 1px solid #dbe4f0;
    border-radius: 16px;
    background: linear-gradient(180deg, #fbfdff 0%, #f8fafc 100%);
  }
  .preview-copy strong, dd { font-weight: 700; }
  .preview-copy p, .branding-summary p, .operator-summary ul, dd { margin: 0; }
  .preview-assets { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .status-pill, .runtime-pill, .asset-chip {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.35rem 0.7rem;
    font-weight: 700;
    background: #eef2ff;
    color: #1d4ed8;
  }
  .status-pill.off, .runtime-pill.critical { background: #fee2e2; color: #b91c1c; }
  .runtime-pill.warning, .asset-chip { background: #fff7ed; color: #9a3412; }
  .runtime-pill.ok, .status-pill.ok, .asset-chip.supported { background: #ecfdf3; color: #166534; }
  .meta-grid { margin: 0; display: grid; gap: 0.7rem; }
  dt, dd { margin: 0; }
  .operator-summary {
    padding-top: 0.25rem;
    border-top: 1px solid #e2e8f0;
  }
  .operator-summary ul { padding-left: 1.1rem; }
  .secondary-action {
    border: 1px solid #cbd5e1;
    background: #fff;
    color: #0f172a;
    border-radius: 10px;
    padding: 0.65rem 0.85rem;
    font-weight: 600;
  }
  .warning-text, .error { margin: 0; color: #b91c1c; }
  .restricted { padding: 1rem; }
  @media (max-width: 980px) {
    .page-header, .section-header, .display-card__head, .meta-grid div, .preview-topline { grid-template-columns: 1fr; display: grid; }
  }
</style>
