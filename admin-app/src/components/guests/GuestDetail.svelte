<script>
  import { createEventDispatcher } from 'svelte';
  import { formatCardStatus, formatDateTimeRu, formatRubAmount } from '../../lib/formatters.js';

  export let guest;
  export let recentActivity = [];
  export let activeVisit = null;
  export let cardLookup = null;
  export let recentEvents = [];
  export let lastTapLabel = '—';
  export let variant = 'full';
  export let canTopUp = true;
  export let topUpDisabled = false;
  export let topUpReason = '';
  export let canToggleBlock = true;
  export let toggleBlockDisabled = false;
  export let toggleBlockReason = '';
  export let canMarkLost = true;
  export let markLostDisabled = false;
  export let markLostReason = '';
  export let canOpenVisit = true;
  export let openVisitDisabled = false;
  export let openVisitReason = '';
  export let canOpenHistory = true;
  export let openHistoryDisabled = false;
  export let openHistoryReason = '';
  export let canManageProfile = true;

  const dispatch = createEventDispatcher();
  let showSecondary = false;

  $: cards = Array.isArray(guest?.cards) ? guest.cards : [];
  $: primaryCard = cardLookup?.card || cards[0] || null;
  $: cardStatusLabel = cardLookup?.is_lost
    ? 'Потеряна'
    : primaryCard?.status
      ? formatCardStatus(primaryCard.status)
      : 'Нет карты';
  $: cardStatusTone = cardLookup?.is_lost || primaryCard?.status === 'lost'
    ? 'danger'
    : primaryCard?.status === 'blocked'
      ? 'warning'
      : primaryCard?.status === 'active'
        ? 'ok'
        : 'muted';
  $: transactions = Array.isArray(guest?.transactions) ? guest.transactions.slice(0, 4) : [];
  $: activity = Array.isArray(recentActivity) ? recentActivity.slice(0, 4) : [];
  $: operatorEvents = Array.isArray(recentEvents) ? recentEvents.slice(0, 5) : [];
  $: isOperatorVariant = variant === 'operator';
  $: guestDisplayName = `${guest.last_name} ${guest.first_name} ${guest.patronymic || ''}`.trim();
  $: visitLabel = activeVisit?.visit_id || cardLookup?.active_visit?.visit_id || 'Нет активного визита';
  $: visitHint = activeVisit?.active_tap_id || cardLookup?.active_visit?.active_tap_id
    ? `Лок на кране #${activeVisit?.active_tap_id || cardLookup?.active_visit?.active_tap_id}`
    : (lastTapLabel !== '—' ? `Последний кран: ${lastTapLabel}` : 'Кран не выбран');
</script>

<div class="detail-container" class:operator={isOperatorVariant}>
  <div class="detail-header">
    <div>
      <h3>{guestDisplayName}</h3>
      <p>{isOperatorVariant ? 'Короткая рабочая сводка для оператора' : (guest.phone_number || 'Телефон не указан')}</p>
    </div>
    <div class="header-actions">
      {#if !isOperatorVariant}
        <button class="ghost-btn" on:click={() => (showSecondary = !showSecondary)}>
          {showSecondary ? 'Скрыть подробности' : 'Показать подробности'}
        </button>
      {/if}
      <button class="close-btn" on:click={() => dispatch('close')} title="Закрыть">×</button>
    </div>
  </div>

  <section class="hero ui-card" class:operator={isOperatorVariant}>
    <div>
      <span class="label">Статус карты</span>
      <strong class={`card-status ${cardStatusTone}`}>{cardStatusLabel}</strong>
      <div class="subtle mono">{primaryCard?.card_uid || cardLookup?.card_uid || 'Карта не привязана'}</div>
    </div>
    <div>
      <span class="label">Баланс</span>
      <strong class:is-compact-balance={isOperatorVariant} class="balance">{formatRubAmount(guest.balance)}</strong>
    </div>
    <div>
      <span class="label">Активный визит</span>
      <strong>{visitLabel}</strong>
      <div class="subtle">{visitHint}</div>
    </div>
    <div>
      <span class="label">Последний кран</span>
      <strong>{lastTapLabel}</strong>
    </div>
<div class="hero-actions">
      {#if canTopUp}
        <button
          class="top-up-btn"
          title={topUpDisabled ? (topUpReason || 'Action unavailable') : ''}
          disabled={topUpDisabled}
          on:click={() => dispatch('top-up')}
        >Пополнить</button>
      {/if}
      {#if canToggleBlock}
        <button
          title={toggleBlockDisabled ? (toggleBlockReason || 'Action unavailable') : ''}
          disabled={toggleBlockDisabled}
          on:click={() => dispatch('toggle-block')}
        >{guest.is_active ? 'Заблокировать' : 'Разблокировать'}</button>
      {/if}
      {#if canMarkLost}
        <button
          class="danger-btn"
          title={markLostDisabled ? (markLostReason || 'Action unavailable') : ''}
          on:click={() => dispatch('mark-lost')}
          disabled={markLostDisabled || (!primaryCard?.card_uid && !cardLookup?.card_uid)}
        >Пометить lost / перевыпустить</button>
      {/if}
      {#if canOpenHistory}
        <button
          title={openHistoryDisabled ? (openHistoryReason || 'Action unavailable') : ''}
          disabled={openHistoryDisabled}
          on:click={() => dispatch('open-history')}
        >История</button>
      {/if}
      {#if canOpenVisit}
        <button
          title={openVisitDisabled ? (openVisitReason || 'Action unavailable') : ''}
          on:click={() => dispatch('open-visit')}
          disabled={openVisitDisabled || (!activeVisit && !cardLookup?.active_visit && !cardLookup?.lost_card?.visit_id)}
        >Активная сессия</button>
      {/if}
    </div>
  </section>

  <section class="info-block">
    <div class="section-head">
      <h4>Последние события</h4>
      <span class:active={guest.is_active} class:inactive={!guest.is_active} class="guest-state">
        {guest.is_active ? 'Гость активен' : 'Гость заблокирован'}
      </span>
    </div>
    {#if operatorEvents.length > 0}
      <ul class="event-list">
        {#each operatorEvents as item, index (`event-${index}`)}
          <li>
            <div>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </div>
            <small>{formatDateTimeRu(item.timestamp)}</small>
          </li>
        {/each}
      </ul>
    {:else if activity.length > 0}
      <ul class="event-list">
        {#each activity as item (item.pour_id)}
          <li>
            <div>
              <strong>Налив</strong>
              <p>{item.beverage?.name || 'Напиток'} · {item.tap?.display_name || `Кран #${item.tap_id || '—'}`}</p>
            </div>
            <small>{formatDateTimeRu(item.poured_at)}</small>
          </li>
        {/each}
      </ul>
    {:else if transactions.length > 0}
      <ul class="event-list">
        {#each transactions as tx (tx.transaction_id)}
          <li>
            <div>
              <strong>{tx.type || 'Операция'}</strong>
              <p>{formatRubAmount(tx.amount || 0)}</p>
            </div>
            <small>{formatDateTimeRu(tx.created_at)}</small>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="hint">Пока нет событий для этого гостя.</p>
    {/if}
  </section>

  {#if isOperatorVariant && canManageProfile}
    <section class="info-block management-callout">
      <div class="section-head">
        <h4>Расширенное управление</h4>
      </div>
      <p class="hint">Полный профиль гостя, редактирование и дополнительные поля вынесены из рабочего сценария и открываются отдельно.</p>
      <div class="management-actions">
        <button class="ghost-btn" on:click={() => dispatch('open-management')}>Открыть полный профиль</button>
      </div>
    </section>
  {/if}

  {#if !isOperatorVariant && showSecondary}
    <section class="info-block secondary-block">
      <div class="section-head">
        <h4>Подробности и редактирование</h4>
        <button class="ghost-btn" on:click={() => dispatch('edit')}>Редактировать гостя</button>
      </div>

      <div class="secondary-grid">
        <div>
          <span class="label">Телефон</span>
          <strong>{guest.phone_number || '—'}</strong>
        </div>
        <div>
          <span class="label">Документ</span>
          <strong>{guest.id_document || '—'}</strong>
        </div>
        <div>
          <span class="label">Создан</span>
          <strong>{formatDateTimeRu(guest.created_at)}</strong>
        </div>
        <div>
          <span class="label">Обновлён</span>
          <strong>{formatDateTimeRu(guest.updated_at)}</strong>
        </div>
        <div>
          <span class="label">ID гостя</span>
          <strong class="mono">{guest.guest_id}</strong>
        </div>
      </div>

      <div>
        <div class="section-head compact">
          <h5>Legacy card bindings</h5>
          <button class="ghost-btn" on:click={() => dispatch('bind-card')}>Открыть service reissue flow</button>
        </div>
        {#if cards.length > 0}
          <ul class="card-list">
            {#each cards as card (card.card_uid)}
              <li>
                <span class="mono">{card.card_uid}</span>
                <span>{formatCardStatus(card.status)}</span>
              </li>
            {/each}
          </ul>
        {:else}
          <p class="hint">Операционная карта теперь живёт на визите; здесь остаются только legacy compatibility записи.</p>
        {/if}
      </div>
    </section>
  {/if}
</div>

<style>
  .detail-container { padding: 0.5rem; display: grid; gap: 1rem; }
  .detail-header, .section-head { display: flex; justify-content: space-between; gap: 1rem; align-items: start; }
  .detail-header { border-bottom: 1px solid #e2e8f0; padding-bottom: 0.75rem; }
  .detail-header h3, .detail-header p, h4, h5 { margin: 0; }
  .detail-header p, .subtle, .hint { color: var(--text-secondary); }
  .header-actions, .hero-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .hero {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    padding: 1rem;
  }
  .hero.operator { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
  .hero-actions { grid-column: 1 / -1; }
  .label { font-size: 0.78rem; color: #64748b; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.04em; }
  .balance { font-size: 1.9rem; color: #155e4a; }
  .balance.is-compact-balance { font-size: 1.45rem; }
  .card-status.ok { color: #15803d; }
  .card-status.warning { color: #b45309; }
  .card-status.danger { color: #b91c1c; }
  .card-status.muted { color: #64748b; }
  .info-block { border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.95rem; display: grid; gap: 0.8rem; }
  .secondary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; }
  .event-list, .card-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 0.5rem; }
  .event-list li, .card-list li {
    display: flex; justify-content: space-between; gap: 1rem; align-items: start;
    border: 1px solid #edf0f4; border-radius: 10px; padding: 0.7rem 0.8rem; background: #fafcff;
  }
  .event-list p { margin: 0.2rem 0 0; color: var(--text-secondary); }
  .guest-state.active { color: #15803d; }
  .guest-state.inactive { color: #b91c1c; }
  .mono { font-family: monospace; }
  .ghost-btn, .close-btn { background: #edf2fb; color: #23416b; }
  .close-btn { border-radius: 999px; width: 40px; min-width: 40px; padding: 0; font-size: 1.3rem; }
  .secondary-block { background: #fbfdff; }
  .compact { align-items: center; }
  .management-callout { background: #fbfdff; }
  .management-actions { display: flex; justify-content: flex-start; }
  @media (max-width: 720px) {
    .detail-header, .section-head { flex-direction: column; }
  }
</style>
