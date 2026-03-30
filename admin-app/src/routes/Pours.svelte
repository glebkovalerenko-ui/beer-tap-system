<script>
  import { onMount } from 'svelte';

  import DataFreshnessChip from '../components/common/DataFreshnessChip.svelte';
  import { navigateWithFocus } from '../lib/actionRouting.js';
  import { formatDateTimeRu, formatRubAmount, formatVolumeRu } from '../lib/formatters.js';
  import { buildOperatorPourPresentation, formatPourSyncState } from '../lib/operator/pourPresentation.js';
  import { canonicalPourStatusLabel, canonicalPourStatusTone, resolveCanonicalPourStatus } from '../lib/operator/pourStatus.js';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';
  import { operatorPoursStore } from '../stores/operatorPoursStore.js';
  import { operatorConnectionStore } from '../stores/operatorConnectionStore.js';

  const DEFAULT_FILTERS = {
    periodPreset: 'today',
    dateFrom: '',
    dateTo: '',
    tapId: '',
    guestQuery: '',
    status: '',
    problemOnly: false,
    nonSaleOnly: false,
    zeroVolumeOnly: false,
    timeoutOnly: false,
    deniedOnly: false,
    saleMode: 'all',
  };

  const STATUS_OPTIONS = [
    { value: 'success', label: 'Успешно' },
    { value: 'stopped', label: 'Остановлен' },
    { value: 'timeout', label: 'Таймаут' },
    { value: 'card_removed', label: 'Карта убрана' },
    { value: 'denied', label: 'Отклонён' },
    { value: 'non_sale', label: 'Без продажи' },
    { value: 'error', label: 'Ошибка' },
  ];

  let filters = { ...DEFAULT_FILTERS };
  let selectedPourRef = '';
  let showAdvancedFilters = false;

  $: items = $operatorPoursStore.items || [];
  $: filteredItems = items.filter((item) => !filters.status || resolveCanonicalPourStatus(item) === filters.status);
  $: detail = $operatorPoursStore.detail || null;
  $: detailStatus = detail ? resolveCanonicalPourStatus(detail.summary) : '';
  $: detailPresentation = detail ? buildOperatorPourPresentation(detail) : null;
  $: routeReadOnlyReason = $operatorConnectionStore.readOnly
    ? ($operatorConnectionStore.reason || 'Сервер отвечает нестабильно. Журнал налива доступен, но действия лучше выполнять после обновления данных.')
    : '';

  onMount(async () => {
    const focusedPourRef = sessionStorage.getItem('pours.focusPourRef');
    if (focusedPourRef) {
      sessionStorage.removeItem('pours.focusPourRef');
      selectedPourRef = focusedPourRef;
    }
    await refresh(true);
    if (selectedPourRef) {
      await openDetailByRef(selectedPourRef);
    }
  });

  function isoDateLocal(value) {
    const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }

  function getPeriodBounds(periodPreset) {
    if (periodPreset === 'range') {
      return { dateFrom: filters.dateFrom, dateTo: filters.dateTo };
    }
    const today = isoDateLocal(new Date());
    return { dateFrom: today, dateTo: today };
  }

  async function refresh(force = false) {
    if (filters.periodPreset !== 'range') {
      filters = { ...filters, ...getPeriodBounds(filters.periodPreset) };
    }
    await operatorPoursStore.fetchJournal({ ...filters, status: '' }, { force }).catch(() => {});
  }

  async function openDetail(item) {
    selectedPourRef = item.pour_ref;
    await operatorPoursStore.fetchDetail(item.pour_ref).catch(() => {});
  }

  async function openDetailByRef(pourRef) {
    selectedPourRef = pourRef;
    await operatorPoursStore.fetchDetail(pourRef).catch(() => {});
  }

  function closeDetail() {
    selectedPourRef = '';
    operatorPoursStore.clearDetail();
  }

  function resetFilters() {
    filters = { ...DEFAULT_FILTERS, ...getPeriodBounds(DEFAULT_FILTERS.periodPreset) };
    refresh(true);
  }

  function openVisit(item = detail?.summary) {
    if (!item?.visit_id) return;
    navigateWithFocus({ target: 'visit', visitId: item.visit_id, tapId: item.tap_id, pourRef: item.pour_ref });
  }

  function openTap(item = detail?.summary) {
    if (!item?.tap_id) return;
    navigateWithFocus({ target: 'tap', tapId: item.tap_id, visitId: item.visit_id, pourRef: item.pour_ref });
  }

  function openGuest(item = detail?.summary) {
    navigateWithFocus({
      target: 'guest',
      guestId: item?.guest_id,
      cardUid: item?.card_uid,
      visitId: item?.visit_id,
      pourRef: item?.pour_ref,
    });
  }

  function displayAmount(value) {
    return value == null ? '—' : formatRubAmount(value);
  }

  function pourStatusLabel(item) {
    return canonicalPourStatusLabel(resolveCanonicalPourStatus(item));
  }

  function pourStatusTone(item) {
    return canonicalPourStatusTone(resolveCanonicalPourStatus(item));
  }

  function pourModeLabel(item) {
    if ((item?.sale_kind || item?.saleKind) === 'non_sale') return 'Без продажи';
    return 'Продажа';
  }

  function syncStateLabel(value) {
    return formatPourSyncState(value).label;
  }
</script>

<section class="page">
  <div class="page-header">
    <div>
      <h1>{ROUTE_COPY.pours.title}</h1>
      <p>{ROUTE_COPY.pours.description}</p>
    </div>
    <DataFreshnessChip
      label="Наливы"
      lastFetchedAt={$operatorPoursStore.lastFetchedAt}
      staleAfterMs={$operatorPoursStore.staleTtlMs}
      mode={$operatorConnectionStore.mode}
      transport={$operatorConnectionStore.transport}
      reason={$operatorConnectionStore.reason}
    />
  </div>

  {#if routeReadOnlyReason}
    <div class="banner warning">
      <strong>Только просмотр.</strong>
      <span>{routeReadOnlyReason}</span>
    </div>
  {/if}

  <section class="ui-card filters-panel">
    <div class="filters-head">
      <div>
        <h2>Фильтры налива</h2>
        <p>Частые фильтры остаются сверху, редкие условия открываются по необходимости.</p>
      </div>
      <button class="secondary" on:click={() => (showAdvancedFilters = !showAdvancedFilters)}>
        {showAdvancedFilters ? 'Скрыть доп. фильтры' : 'Ещё фильтры'}
      </button>
    </div>

    <div class="filters-grid primary-filters">
      <label>
        <span>Период</span>
        <select bind:value={filters.periodPreset} on:change={() => refresh(true)}>
          <option value="today">Сегодня</option>
          <option value="shift">Смена</option>
          <option value="range">Диапазон</option>
        </select>
      </label>
      <label>
        <span>Дата от</span>
        <input type="date" bind:value={filters.dateFrom} disabled={filters.periodPreset !== 'range'} />
      </label>
      <label>
        <span>Дата до</span>
        <input type="date" bind:value={filters.dateTo} disabled={filters.periodPreset !== 'range'} />
      </label>
      <label>
        <span>Кран</span>
        <input type="number" min="1" bind:value={filters.tapId} placeholder="1" />
      </label>
      <label>
        <span>Гость / карта / short ID</span>
        <input bind:value={filters.guestQuery} placeholder="Имя, телефон, UID, номер визита, short ID" />
      </label>
      <label>
        <span>Исход налива</span>
        <select bind:value={filters.status}>
          <option value="">Все</option>
          {#each STATUS_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>
      <label>
        <span>Тип налива</span>
        <select bind:value={filters.saleMode}>
          <option value="all">Все</option>
          <option value="sale">Только продажа</option>
          <option value="non_sale">Только без продажи</option>
        </select>
      </label>
    </div>

    {#if showAdvancedFilters}
      <div class="filters-grid advanced-filters">
      <label class="checkbox"><input type="checkbox" bind:checked={filters.problemOnly} /> Только проблемные</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.nonSaleOnly} /> Только без продажи</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.zeroVolumeOnly} /> Только без объёма</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.timeoutOnly} /> Только таймаут</label>
      <label class="checkbox"><input type="checkbox" bind:checked={filters.deniedOnly} /> Только отклонённые</label>
      </div>
    {/if}
    <div class="filters-actions">
      <button on:click={() => refresh(true)} disabled={$operatorPoursStore.loading}>Применить</button>
      <button class="secondary" on:click={resetFilters}>Сбросить</button>
    </div>
  </section>

  <div class="content-grid">
    <section class="ui-card list-panel">
      <div class="list-head">
        <div>
          <h2>Журнал наливов</h2>
          <p>
            Показано {filteredItems.length} ·
            проблемных {$operatorPoursStore.header?.problem_pours || 0} ·
            без продажи {$operatorPoursStore.header?.non_sale_pours || 0}
          </p>
        </div>
      </div>

      {#if $operatorPoursStore.loading && filteredItems.length === 0}
        <p>Загрузка журнала наливов...</p>
      {:else if $operatorPoursStore.error}
        <p class="error">{$operatorPoursStore.error}</p>
      {:else if filteredItems.length === 0}
        <p class="muted">По выбранным фильтрам наливы не найдены.</p>
      {:else}
        <div class="pour-list">
          {#each filteredItems as item}
            <button class:selected={selectedPourRef === item.pour_ref} class="pour-item" on:click={() => openDetail(item)}>
              <div class="row top">
                <strong>{item.guest_full_name || item.card_uid || item.tap_label || 'Налив без гостя'}</strong>
                <span class="status" data-status={resolveCanonicalPourStatus(item)} data-tone={pourStatusTone(item)}>{pourStatusLabel(item)}</span>
              </div>
              <div class="row meta-grid">
                <span>{item.tap_label || 'Кран не указан'}</span>
                <span>{item.beverage_name || 'Напиток не указан'}</span>
                <span>{formatVolumeRu(item.volume_ml || 0)}</span>
                <span>{displayAmount(item.amount_charged)}</span>
              </div>
              <div class="row meta-grid">
                <span>{formatDateTimeRu(item.occurred_at)}</span>
                <span>{item.visit_id ? `Визит #${item.visit_id}` : 'Без визита'}</span>
                <span>{item.short_id ? `ID ${item.short_id}` : pourModeLabel(item)}</span>
                <span>{syncStateLabel(item.sync_state)}</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </section>

    <aside class="ui-card detail-panel">
      {#if detail}
        <div class="detail-head">
          <div>
            <div class="eyebrow">Детали налива</div>
            <h2>{detail.summary.beverage_name || detail.summary.tap_label || detail.summary.pour_ref}</h2>
            <p>{detail.summary.guest_full_name || detail.summary.card_uid || 'Гость не определён'} · {canonicalPourStatusLabel(detailStatus)}</p>
          </div>
          <button class="secondary" on:click={closeDetail}>Закрыть</button>
        </div>

        <section class="summary-grid">
          <article>
            <span>Статус</span>
            <strong>{canonicalPourStatusLabel(detailStatus)}</strong>
          </article>
          <article>
            <span>Кран</span>
            <strong>{detail.summary.tap_label || '—'}</strong>
          </article>
          <article>
            <span>Визит</span>
            <strong>{detail.summary.visit_id || '—'}</strong>
          </article>
          <article>
            <span>Объём</span>
            <strong>{formatVolumeRu(detail.summary.volume_ml || 0)}</strong>
          </article>
          <article>
            <span>Сумма</span>
            <strong>{displayAmount(detail.summary.amount_charged)}</strong>
          </article>
          <article>
            <span>Синхронизация</span>
            <strong>{detailPresentation?.sync.label || 'Нет данных о синхронизации'}</strong>
            {#if detailPresentation?.sync.technicalDetail}
              <small>{detailPresentation.sync.technicalDetail}</small>
            {/if}
          </article>
        </section>

        <section class="summary-note">
          <strong>{detail.summary.source_kind === 'denied' ? 'Почему налив не начался:' : 'Чем завершилось:'}</strong>
          {detailPresentation?.completion.label || 'Причина не указана'}
          {#if detailPresentation?.completion.technicalDetail}
            <small>{detailPresentation.completion.technicalDetail}</small>
          {/if}
        </section>

        <section class="action-row">
          <button on:click={() => openVisit()} disabled={!detail.safe_actions?.open_visit?.allowed}>Открыть визит</button>
          <button on:click={() => openGuest()} disabled={!detail.safe_actions?.open_guest?.allowed}>Открыть гостя</button>
          <button on:click={() => openTap()} disabled={!detail.safe_actions?.open_tap?.allowed}>Открыть кран</button>
        </section>

        <section class="detail-section">
          <h3>Ход налива</h3>
          <ul class="timeline">
            {#each detailPresentation?.lifecycle || [] as step}
              <li>
                <div class="time">{step.timestamp ? formatDateTimeRu(step.timestamp) : '—'}</div>
                <div>
                  <strong>{step.operatorLabel}</strong>
                  <p>{step.operatorValue || 'Без дополнительной отметки'}</p>
                  {#if step.technicalDetail}
                    <small>{step.technicalDetail}</small>
                  {/if}
                </div>
              </li>
            {/each}
          </ul>
        </section>

        <section class="detail-section">
          <h3>Что видел экран крана</h3>
          {#if detail.display_context?.available}
            <div class="context-grid">
              <div><strong>Кран</strong><span>{detail.display_context.tap_name || detail.display_context.tap_id || '—'}</span></div>
              <div><strong>Экран</strong><span>{detail.display_context.display_state || detail.display_context.availability_label || '—'}</span></div>
              <div><strong>Заголовок</strong><span>{detail.display_context.title || '—'}</span></div>
              <div><strong>Подзаголовок</strong><span>{detail.display_context.subtitle || '—'}</span></div>
            </div>
          {:else}
            <p class="muted">{detail.display_context?.note || 'Контекст экрана не был сохранён для этого налива.'}</p>
          {/if}
        </section>

        <section class="detail-section">
          <h3>Действия оператора</h3>
          {#if detail.operator_actions?.length}
            <ul class="timeline compact">
              {#each detail.operator_actions as action}
                <li>
                  <div class="time">{formatDateTimeRu(action.timestamp)}</div>
                  <div>
                    <strong>{action.label || action.action}</strong>
                    <p>{action.details || 'Без комментария'}</p>
                  </div>
                </li>
              {/each}
            </ul>
          {:else}
            <p class="muted">Для этого налива явных действий оператора не зафиксировано.</p>
          {/if}
        </section>
      {:else}
        <div class="empty-state">
          <div class="eyebrow">Детали налива</div>
          <h2>Выберите налив</h2>
          <p>Откройте любую строку слева, чтобы увидеть исход, ход налива и контекст по крану.</p>
        </div>
      {/if}
    </aside>
  </div>
</section>

<style>
  .page { display: grid; gap: 1rem; }
  .page-header, .list-head, .detail-head, .filters-actions, .action-row, .filters-head { display: flex; gap: 1rem; justify-content: space-between; align-items: flex-start; }
  .page-header p, .list-head p, .detail-head p { margin: 0.25rem 0 0; color: var(--text-secondary); }
  .banner { display: grid; gap: 0.35rem; padding: 0.9rem 1rem; border-radius: 16px; }
  .banner.warning { background: var(--state-warning-bg); border: 1px solid var(--state-warning-border); color: var(--state-warning-text); }
  .filters-panel, .list-panel, .detail-panel { display: grid; gap: 1rem; }
  .filters-grid { display: grid; gap: 0.75rem; grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .filters-head h2,
  .filters-head p { margin: 0; }
  .filters-head p { color: var(--text-secondary); }
  .primary-filters { align-items: end; }
  .advanced-filters { padding-top: 0.15rem; }
  .filters-grid label { display: grid; gap: 0.35rem; }
  .filters-grid label span { font-size: 0.85rem; color: var(--text-secondary); }
  .checkbox { align-self: end; grid-template-columns: auto 1fr; align-items: center; gap: 0.5rem; }
  .content-grid { display: grid; gap: 1rem; grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr); align-items: start; }
  .pour-list, .timeline { display: grid; gap: 0.75rem; }
  .pour-item { text-align: left; border: 1px solid var(--border-soft); border-radius: 14px; padding: 0.9rem; background: #fff; color: var(--text-primary); display: grid; gap: 0.5rem; }
  .pour-item.selected { border-color: var(--accent-color, #1d4ed8); box-shadow: 0 0 0 1px rgba(29, 78, 216, 0.16); }
  .row { display: flex; gap: 0.75rem; flex-wrap: wrap; justify-content: space-between; }
  .row.top { align-items: center; }
  .meta-grid { color: var(--text-secondary); font-size: 0.92rem; }
  .status { border-radius: 999px; padding: 0.3rem 0.7rem; font-size: 0.82rem; font-weight: 700; }
  .status[data-status='success'] { background: #edf7ef; color: #1f6b3d; }
  .status[data-status='timeout'],
  .status[data-status='card_removed'] { background: #fff8e9; color: #8d5b00; }
  .status[data-status='denied'],
  .status[data-status='error'] { background: #ffeef0; color: #9e1f2c; }
  .status[data-status='stopped'] { background: #eef2f7; color: #334155; }
  .status[data-status='non_sale'] { background: #eef2ff; color: #3447a3; }
  .summary-grid, .context-grid { display: grid; gap: 0.75rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-grid article, .context-grid div, .summary-note { display: grid; gap: 0.2rem; padding: 0.8rem; border-radius: 12px; background: var(--bg-surface-muted); }
  .summary-grid span, .context-grid strong, .time, .eyebrow { color: var(--text-secondary); font-size: 0.82rem; }
  .summary-note { color: var(--text-secondary); }
  .detail-section { display: grid; gap: 0.75rem; }
  .timeline li { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 0.75rem; }
  .timeline p, .empty-state p { margin: 0.2rem 0 0; color: var(--text-secondary); }
  .muted, .error { color: var(--text-secondary); }
  .error { color: var(--state-critical-text); }
  @media (max-width: 1100px) {
    .filters-grid, .content-grid, .summary-grid, .context-grid { grid-template-columns: 1fr; }
    .page-header, .list-head, .detail-head, .filters-actions, .action-row, .filters-head { flex-direction: column; align-items: stretch; }
    .timeline li { grid-template-columns: 1fr; }
  }
</style>
