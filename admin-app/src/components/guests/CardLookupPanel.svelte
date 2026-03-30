<script>
  import { createEventDispatcher } from 'svelte';
  import NFCModal from '../modals/NFCModal.svelte';
  import { formatDateTimeRu } from '../../lib/formatters.js';

  export let loading = false;
  export let error = '';
  export let title = 'Быстрый поиск по карте';
  export let description = 'Приложите карту или введите UID вручную, чтобы открыть статус карты и связанного гостя.';
  export let result = null;
  export let allowRestoreLost = false;
  export let restoreLostDisabled = false;
  export let restoreLostReason = '';
  export let allowOpenVisit = true;
  export let openVisitDisabled = false;
  export let openVisitReason = '';
  export let allowOpenGuest = true;
  export let allowOpenNewVisit = false;
  export let openVisitLabel = 'Открыть визит';
  export let openGuestLabel = 'Открыть гостя';
  export let openNewVisitLabel = 'Открыть новый визит';
  export let actions = [];
  export let selectedActionId = '';
  export let searchQuery = '';
  export let searchPlaceholder = 'Номер телефона / идентификатор';
  export let searchResults = [];
  export let searchResultLabel = 'Совпадения';
  export let operatorSummaryItems = [];

  const dispatch = createEventDispatcher();

  let uidInput = '';
  let isNfcModalOpen = false;
  let nfcError = '';

  function submitManualLookup() {
    const uid = uidInput.trim();
    if (!uid) return;
    dispatch('lookup', { uid });
  }

  function handleSearchInput(event) {
    dispatch('search-change', { value: event.currentTarget.value });
  }

  function handleUidRead(event) {
    nfcError = '';
    dispatch('lookup', { uid: event.detail.uid, source: 'nfc' });
  }

  function statusTone(value) {
    switch (value) {
      case 'danger': return 'status-danger';
      case 'warning': return 'status-warning';
      case 'info': return 'status-info';
      default: return 'status-muted';
    }
  }

  $: hasVisitTarget = Boolean(result?.active_visit?.visit_id || result?.lost_card?.visit_id);
  $: primaryAction = actions.find((item) => item.id === selectedActionId && !item.disabled) || actions.find((item) => !item.disabled) || null;
  $: lookupOutcome = result?.lookup_outcome || 'unknown_card';
  $: statusText = {
    active_visit: 'Карта назначена активному визиту',
    active_blocked_lost_card: 'Активный визит заблокирован до reissue или service-close',
    available_pool_card: 'Физическая карта доступна в пуле и может быть выдана на новый визит',
    returned_to_pool_card: 'Карта подтверждённо возвращена в пул и готова к reuse',
    lost_card: 'Физическая карта помечена как lost и не может использоваться',
    retired_card: 'Карта выведена из эксплуатации',
    unknown_card: 'Карта не зарегистрирована в inventory pool',
  }[lookupOutcome] || 'Статус карты уточняется';
  $: statusClass = lookupOutcome === 'lost_card'
    ? statusTone('danger')
    : lookupOutcome === 'active_visit' || lookupOutcome === 'active_blocked_lost_card'
      ? statusTone('info')
      : lookupOutcome === 'retired_card' || lookupOutcome === 'unknown_card'
        ? statusTone('warning')
        : statusTone();
</script>

<section class="lookup-shell ui-card">
  <div class="lookup-head">
    <div>
      <h2>{title}</h2>
      <p>{description}</p>
    </div>
    <div class="lookup-entry">
      <button on:click={() => { nfcError = ''; isNfcModalOpen = true; }} disabled={loading}>Приложить карту</button>
      <div class="uid-entry">
        <input
          type="text"
          bind:value={uidInput}
          placeholder="Введите UID"
          on:keydown={(event) => event.key === 'Enter' && submitManualLookup()}
        />
        <button on:click={submitManualLookup} disabled={loading || !uidInput.trim()}>Найти UID</button>
      </div>
      <div class="search-entry">
        <input
          type="text"
          value={searchQuery}
          placeholder={searchPlaceholder}
          on:input={handleSearchInput}
        />
      </div>
    </div>
  </div>

  {#if searchQuery.trim()}
    <div class="search-results">
      <div class="search-results-head">
        <strong>{searchResultLabel}</strong>
        <span>{searchResults.length}</span>
      </div>
      {#if searchResults.length > 0}
        <div class="search-result-list">
          {#each searchResults as item}
            <button class="search-result-item" on:click={() => dispatch('open-guest', { guestId: item.guest_id })}>
              <div>
                <strong>{item.label}</strong>
                <small>{item.meta}</small>
              </div>
              <span>{item.trailing}</span>
            </button>
          {/each}
        </div>
      {:else}
        <p class="search-empty">Ничего не найдено. Проверьте номер, UID или другой идентификатор.</p>
      {/if}
    </div>
  {/if}

  {#if result}
    <div class="lookup-result">
      <div class="operator-first-summary">
        <div class="summary-head">
          <div>
            <span class="eyebrow">Статус карты</span>
            <p class={`lookup-status ${statusClass}`}>{statusText}</p>
          </div>
          {#if primaryAction}
            <div class="primary-cta-box compact">
              <span class="eyebrow">Быстрое действие</span>
              <button class:danger-btn={primaryAction.tone === 'danger'} class="primary-cta" title={primaryAction.disabled ? (primaryAction.reason || 'Действие сейчас недоступно') : ''} on:click={() => dispatch('scenario-action', { actionId: primaryAction.id })} disabled={primaryAction.disabled || loading}>
                {primaryAction.title}
              </button>
            </div>
          {/if}
        </div>

        <div class="summary-grid">
          <div>
            <span class="eyebrow">UID карты</span>
            <strong>{result.card_uid || result.card?.uid || '—'}</strong>
          </div>
          <div>
            <span class="eyebrow">Гость</span>
            <strong>{result.guest?.full_name || result.active_visit?.guest_full_name || 'Не найден'}</strong>
          </div>
          <div>
            <span class="eyebrow">Телефон</span>
            <strong>{result.guest?.phone_number || result.active_visit?.phone_number || '—'}</strong>
          </div>
          <div>
            <span class="eyebrow">Активный визит</span>
            <strong>{result.active_visit?.visit_id || result.lost_card?.visit_id || 'Нет'}</strong>
          </div>
        </div>

        {#if operatorSummaryItems.length > 0}
          <div class="operator-summary-grid">
            {#each operatorSummaryItems as item (item.key)}
              <article class={`operator-summary-card tone-${item.tone || 'neutral'}`}>
                <span class="eyebrow">{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            {/each}
          </div>
        {/if}

        {#if result.is_lost}
          <div class="lookup-meta danger">
            <div><strong>Дата отметки:</strong> {formatDateTimeRu(result.lost_card?.reported_at)}</div>
            <div><strong>Комментарий:</strong> {result.lost_card?.comment || '—'}</div>
          </div>
        {:else if result.active_visit}
          <div class="lookup-meta">
            <div><strong>Лок:</strong> {result.active_visit.active_tap_id ? `Кран #${result.active_visit.active_tap_id}` : 'Нет активного лока'}</div>
          </div>
        {/if}
      </div>

      {#if actions.length > 0}
        <div class="scenario-rail">
          {#each actions as action (action.id)}
            <button
              class:selected={selectedActionId === action.id}
              class:warning={action.tone === 'danger'}
              class="scenario-chip"
              title={action.disabled ? (action.reason || 'Действие сейчас недоступно') : ''}
              on:click={() => dispatch('scenario-action', { actionId: action.id })}
              disabled={action.disabled || loading}
            >
              <span>{action.title}</span>
              <small>{action.description}</small>
            </button>
          {/each}
        </div>
      {/if}

      <div class="lookup-actions">
        {#if allowRestoreLost && result.is_lost}
          <button class="danger-btn" title={restoreLostDisabled ? (restoreLostReason || 'Действие сейчас недоступно') : ''} on:click={() => dispatch('restore-lost', { uid: result.card_uid || result.card?.uid })} disabled={loading || restoreLostDisabled}>
            Снять отметку потери
          </button>
        {/if}
        {#if allowOpenVisit && hasVisitTarget}
          <button title={openVisitDisabled ? (openVisitReason || 'Действие сейчас недоступно') : ''} on:click={() => dispatch('open-visit', { visitId: result.active_visit?.visit_id || result.lost_card?.visit_id })} disabled={openVisitDisabled}>{openVisitLabel}</button>
        {/if}
        {#if allowOpenGuest && result.guest?.guest_id}
          <button on:click={() => dispatch('open-guest', { guestId: result.guest.guest_id })}>{openGuestLabel}</button>
        {/if}
        {#if allowOpenNewVisit && result.guest?.guest_id && !result.active_visit}
          <button on:click={() => dispatch('open-new-visit', { guestId: result.guest.guest_id })}>{openNewVisitLabel}</button>
        {/if}
      </div>
    </div>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}
</section>

{#if isNfcModalOpen}
  <NFCModal
    on:close={() => { isNfcModalOpen = false; }}
    on:uid-read={handleUidRead}
    externalError={nfcError}
  />
{/if}

<style>
  .lookup-shell { display: grid; gap: 0.9rem; }
  .lookup-head { display: grid; gap: 0.75rem; }
  .lookup-head h2, .lookup-head p { margin: 0; }
  .lookup-head p { color: var(--text-secondary); }
  .lookup-entry { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
  .uid-entry { display: flex; gap: 0.5rem; flex: 1 1 320px; }
  .search-entry { flex: 1 1 260px; }
  .uid-entry input { flex: 1 1 auto; }
  .search-entry input { width: 100%; }
  .search-results {
    border: 1px solid var(--border-soft, #dbe4f0);
    border-radius: 12px;
    background: #fff;
    padding: 0.85rem;
    display: grid;
    gap: 0.6rem;
  }
  .search-results-head { display: flex; justify-content: space-between; gap: 0.5rem; align-items: center; }
  .search-result-list { display: grid; gap: 0.5rem; }
  .search-result-item {
    display: flex; justify-content: space-between; gap: 0.75rem; align-items: center; text-align: left;
    width: 100%; border: 1px solid #e2e8f0; border-radius: 12px; background: #f8fafc; padding: 0.75rem;
  }
  .search-result-item small, .search-empty { color: var(--text-secondary); }
  .lookup-result {
    border: 1px solid var(--border-soft, #dbe4f0);
    border-radius: 14px;
    background: var(--bg-surface-muted, #f8fafc);
    padding: 1rem;
    display: grid;
    gap: 0.85rem;
  }
  .operator-first-summary { display: grid; gap: 0.75rem; }
  .summary-head { display: flex; justify-content: space-between; gap: 0.85rem; align-items: start; }
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.75rem;
  }
  .operator-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.75rem;
  }
  .operator-summary-card {
    display: grid;
    gap: 0.3rem;
    padding: 0.75rem;
    border-radius: 12px;
    border: 1px solid #dbe4f0;
    background: #fff;
  }
  .operator-summary-card.tone-warning {
    border-color: var(--state-warning-border, #facc15);
    background: var(--state-warning-bg, #fff7e6);
    color: var(--state-warning-text, #9a6700);
  }
  .operator-summary-card.tone-info {
    border-color: var(--state-neutral-border, #bfdbfe);
    background: var(--state-neutral-bg, #eef2ff);
    color: var(--state-neutral-text, #1e3a8a);
  }
  .eyebrow { display: block; font-size: 0.75rem; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
  .lookup-status { margin: 0; font-weight: 700; }
  .status-danger { color: #b91c1c; }
  .status-warning { color: #b45309; }
  .status-info { color: #1d4ed8; }
  .status-muted { color: #475569; }
  .primary-cta-box.compact { display: grid; gap: 0.35rem; min-width: 240px; }
  .lookup-meta { display: flex; flex-wrap: wrap; gap: 1rem; color: #334155; }
  .lookup-meta.danger { color: #9a3412; }
  .scenario-rail { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.6rem; }
  .scenario-chip {
    display: grid; gap: 0.25rem; text-align: left; border: 1px solid #dbe4f0; border-radius: 12px;
    background: #fff; padding: 0.75rem;
  }
  .scenario-chip.selected { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12); }
  .scenario-chip.warning { border-color: #fdba74; background: #fff7ed; }
  .scenario-chip small { color: var(--text-secondary); }
  .lookup-actions { display: flex; flex-wrap: wrap; gap: 0.6rem; }
  .error { color: #c61f35; margin: 0; }
  @media (max-width: 720px) {
    .summary-head { flex-direction: column; }
  }
</style>
