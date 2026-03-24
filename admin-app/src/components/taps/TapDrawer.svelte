<script>
  import { createEventDispatcher } from 'svelte';
  import { formatDateTimeRu, formatRubAmount, formatVolumeRu } from '../../lib/formatters.js';
  import { TAP_COPY } from '../../lib/operatorLabels.js';

  export let tap;
  export let canDisplayOverride = false;
  export let canControl = false;
  export let canMaintain = false;

  const dispatch = createEventDispatcher();
  const HISTORY_LIMIT = 12;

  $: operations = tap?.operations || {};
  $: session = operations.activeSessionSummary;
  $: currentPour = operations.currentPour || {};
  $: operatorHistory = operations.operatorHistory || [];
  $: recentHistory = operatorHistory.slice(0, HISTORY_LIMIT);
  $: isLocked = tap?.status === 'locked';
  $: keg = tap?.keg || null;
  $: beverage = keg?.beverage || {};
  $: operatorMeta = operations.operatorStateMeta || { key: 'needs_help', tone: 'muted', icon: '?', shortLabel: 'Нет данных', eyebrow: 'Статус не определён', headline: 'Состояние не определено', badgeStyle: 'callout', iconShape: 'alert', containerStyle: 'alert' };
  $: stateKey = operatorMeta.key || operations.operatorState || operations.productState || 'needs_help';
  $: stateExplanationRows = [
    { label: 'Канонический статус', value: operations.productStateLabel || 'Нет данных', note: `${operatorMeta.eyebrow || 'Статус'} · ${operatorMeta.icon} · ${operatorMeta.headline || 'Без пояснения'}` },
    { label: 'Почему этот статус', value: operations.operatorStateReason || 'Причина не передана', note: operations.operatorStateTelemetry || 'Дополнительной телеметрии нет' },
    { label: TAP_COPY.liveSignals, value: operations.liveStatus || 'Нет данных', note: operations.syncState?.label || null },
  ];
  $: liveStateRows = [
    { label: 'Подключение', value: operations.heartbeat?.isStale ? TAP_COPY.connectivityOffline : TAP_COPY.connectivityOnline, note: operations.liveStatus || null },
    { label: TAP_COPY.reader, value: operations.readerStatus?.label || 'Нет данных', note: operations.readerStatus?.state || null },
    { label: 'Клапан', value: valveStatusLabel(tap, operations, currentPour), note: null },
    { label: 'Поток', value: currentPour.isActive ? 'Идёт налив' : 'Поток не зафиксирован', note: currentPour.volumeMl ? formatVolumeRu(currentPour.volumeMl) : null },
    { label: TAP_COPY.screen, value: operations.displayStatus?.label || 'Нет данных', note: displaySummary },
    { label: 'Последний heartbeat', value: operations.heartbeat?.at ? formatDateTimeRu(operations.heartbeat.at) : 'Нет данных', note: operations.heartbeat?.minutesAgo != null ? `${operations.heartbeat.minutesAgo} мин назад` : 'Источник не передал heartbeat' },
    { label: 'Синхронизация', value: operations.syncState?.label || 'Нет данных', note: tap?.status || null },
    { label: TAP_COPY.activeSessionCard, value: activeVisitCardLabel(session), note: session?.guestName || null },
  ];
  $: beveragePrice = beverage.sell_price_per_liter ?? tap?.sell_price_per_liter ?? null;
  $: projectedRemainingBalance = session?.projectedRemainingBalance ?? session?.projected_remaining_balance ?? computeProjectedRemaining(session, currentPour);
  $: projectedRemainingAllowanceMl = session?.projectedRemainingAllowanceMl ?? null;
  $: projectedRemainingAllowanceState = session?.allowanceState || (projectedRemainingAllowanceMl != null ? 'available' : 'telemetry_gap');
  $: projectedRemainingAllowanceNote = session?.allowanceCalculationNote || null;
  $: beverageKegRows = [
    { label: 'Название напитка', value: operations.beverageName || beverage.name || 'Напиток не назначен', note: beverage.display_brand_name || null },
    { label: 'Стиль', value: operations.beverageStyle || beverage.style || '—', note: beverage.brewery || null },
    { label: 'ABV', value: formatAbv(beverage.abv), note: null },
    { label: 'Цена', value: beveragePrice ? formatRubAmount(beveragePrice) : '—', note: beverage.price_display_mode_default || null },
    { label: 'Остаток', value: operations.remainingVolumeMl != null ? formatVolumeRu(operations.remainingVolumeMl) : '—', note: operations.remainingPercent != null ? `${operations.remainingPercent}% от полной кеги` : null },
    { label: 'Дата подключения кеги', value: keg?.tapped_at ? formatDateTimeRu(keg.tapped_at) : 'Кега не подключена', note: keg?.created_at ? `Создана ${formatDateTimeRu(keg.created_at)}` : null },
    { label: 'Сводка контента экрана', value: displaySummary, note: null },
  ];
  $: chronologyGroups = groupChronology(recentHistory);
  $: titleId = 'tap-drawer-title';
  $: descriptionId = 'tap-drawer-description';
  $: canShowServiceReady = tap?.status === 'cleaning' || tap?.status === 'empty' || isLocked;
  $: serviceActions = [
    {
      key: 'cleaning',
      label: 'Промывка',
      tone: 'secondary',
      visible: canMaintain,
      description: 'Переводит кран в сервисный режим для промывки линии.',
    },
    {
      key: 'mark-ready',
      label: 'Перевести в готовность',
      tone: 'success',
      visible: canMaintain && canShowServiceReady,
      description: 'Возвращает кран в рабочий статус после обслуживания или блокировки.',
    },
    {
      key: tap?.keg_id ? 'unassign' : 'assign',
      label: tap?.keg_id ? 'Снять кегу' : 'Назначить кегу',
      tone: 'secondary',
      visible: canControl,
      description: tap?.keg_id ? 'Отключает текущую кегу от линии.' : 'Открывает назначение новой кеги на кран.',
    },
  ].filter((action) => action.visible);

  function emit(name) {
    dispatch(name, { tap });
  }

  function openLinkedSession(visitId) {
    dispatch('open-session', { tap, visitId: visitId || session?.visitId || null });
  }

  function activeVisitCardLabel(activeSession) {
    if (!activeSession) return 'Нет активного визита';
    return `${activeSession.visitId ? `Визит #${activeSession.visitId}` : 'Визит открыт'}${activeSession.cardUid ? ` · карта ${activeSession.cardUid}` : ' · карта не привязана'}`;
  }

  function computeProjectedRemaining(activeSession, pour) {
    const balance = toNumber(activeSession?.balance);
    const amount = toNumber(pour?.amount);
    if (balance == null) return null;
    return Math.max(balance - (amount || 0), 0);
  }

  function toNumber(value) {
    if (value == null || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatAbv(value) {
    const numeric = toNumber(value);
    return numeric == null ? '—' : `${numeric}%`;
  }

  function valveStatusLabel(tapView, ops, pour) {
    if (tapView?.status === 'locked') return 'Закрыт';
    if (pour?.isActive) return 'Открыт';
    if (ops?.productState === 'maintenance') return 'Сервисный режим';
    return 'Готов';
  }

  function buildDisplaySummary(tapView, drink, ops) {
    const parts = [];
    if (tapView?.display_enabled === false) parts.push('экран отключён');
    else parts.push(ops?.displayStatus?.label || 'экран без статуса');
    if (drink?.display_brand_name) parts.push(`бренд: ${drink.display_brand_name}`);
    if (drink?.description_short) parts.push(drink.description_short);
    if (drink?.price_display_mode_default) parts.push(`режим цены: ${drink.price_display_mode_default}`);
    return parts.filter(Boolean).join(' · ') || 'Нет описания контента экрана';
  }

  $: displaySummary = buildDisplaySummary(tap, beverage, operations);

  function groupChronology(items) {
    const groups = [];

    items.forEach((item) => {
      const date = item?.happenedAt ? new Date(item.happenedAt) : null;
      const validDate = date && !Number.isNaN(date.getTime()) ? date : null;
      const groupKey = validDate ? validDate.toISOString().slice(0, 10) : 'unknown';
      const groupLabel = validDate
        ? validDate.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
        : 'Время не определено';
      const summaryBits = [
        item?.description,
        item?.volumeMl ? formatVolumeRu(item.volumeMl) : null,
        item?.amount ? formatRubAmount(item.amount) : null,
        !item?.amount && item?.rawStatus ? item.rawStatus : null,
      ].filter(Boolean);

      const entry = {
        ...item,
        timeLabel: validDate ? validDate.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '—',
        summaryLine: summaryBits.join(' · '),
      };

      const existingGroup = groups.find((group) => group.key === groupKey);
      if (existingGroup) existingGroup.items.push(entry);
      else groups.push({ key: groupKey, label: groupLabel, items: [entry] });
    });

    return groups;
  }
</script>

{#if tap}
  <div class="tap-drawer">
    <header class="drawer-head">
      <div>
        <div class="eyebrow">Карточка крана</div>
        <h2 id={titleId}>{tap.display_name}</h2>
        <div class={`drawer-status tone-${operatorMeta.tone || 'muted'} badge-${operatorMeta.badgeStyle || 'callout'} icon-${operatorMeta.iconShape || 'alert'}`} data-state={stateKey}>
          <span class="drawer-status-badge">
            <span class="drawer-status-icon" aria-hidden="true">{operatorMeta.icon}</span>
            <span>{operations.productStateLabel}</span>
          </span>
          <div class="drawer-status-copy">
            <strong>{operatorMeta.headline}</strong>
            <p id={descriptionId}>{operations.operatorStateReason || operations.liveStatus}</p>
          </div>
        </div>
      </div>
      <button class="close-btn" type="button" on:click={() => dispatch('close')}>✕</button>
    </header>

    <div class="drawer-body">
      <section class="drawer-section info-grid">
        <article class="status-explainer">
          <div class="section-head compact">
            <div>
              <h3>Почему кран в этом статусе</h3>
              <p>Сначала объясняем операторский статус, потом уже показываем сырую телеметрию устройств.</p>
            </div>
          </div>
          <dl>
            {#each stateExplanationRows as row}
              <div>
                <dt>{row.label}</dt>
                <dd>
                  <strong>{row.value}</strong>
                  {#if row.note}
                    <small>{row.note}</small>
                  {/if}
                </dd>
              </div>
            {/each}
          </dl>
        </article>

        <article>
          <div class="section-head compact">
            <div>
              <h3>Живое состояние</h3>
              <p>Поддерживающая телеметрия: помогает подтвердить статус, но не заменяет его.</p>
            </div>
          </div>
          <dl>
            {#each liveStateRows as row}
              <div>
                <dt>{row.label}</dt>
                <dd>
                  <strong>{row.value}</strong>
                  {#if row.note}
                    <small>{row.note}</small>
                  {/if}
                </dd>
              </div>
            {/each}
          </dl>
        </article>

        <article class="current-session">
          <div class="section-head compact">
            <div>
              <h3>Текущая сессия</h3>
              <p>Активный гость, налив и оперативные действия по визиту.</p>
            </div>
          </div>

          <div class="session-panel">
            <div class="session-copy">
              <strong>{session?.guestName || 'Сессия сейчас не открыта'}</strong>
              <p>
                {#if session}
                  Карта {session.cardUid || 'не привязана'} · открыта {session.openedAt ? formatDateTimeRu(session.openedAt) : 'недавно'}
                {:else}
                  Откройте сессию, если гость уже у крана, или заблокируйте линию до начала работы.
                {/if}
              </p>
              <div class="session-metrics">
                <span>Налито: {formatVolumeRu(currentPour.volumeMl || 0)}</span>
                <span>Сумма: {currentPour.amount ? formatRubAmount(currentPour.amount) : '0 ₽'}</span>
                <span>Статус: {currentPour.isActive ? 'Налив активен' : 'Поток не зафиксирован'}</span>
              </div>
              <dl class="session-details">
                <div><dt>Баланс</dt><dd>{session?.balance != null ? formatRubAmount(session.balance) : '—'}</dd></div>
                <div><dt>Прогноз остатка баланса</dt><dd>{projectedRemainingBalance != null ? formatRubAmount(projectedRemainingBalance) : '—'}</dd></div>
                <div>
                  <dt>Прогноз остатка лимита</dt>
                  <dd>
                    {#if projectedRemainingAllowanceMl != null}
                      {formatVolumeRu(projectedRemainingAllowanceMl)}
                    {:else if projectedRemainingAllowanceState === 'not_configured'}
                      Лимит не задан
                    {:else}
                      {TAP_COPY.backendNoData}
                    {/if}
                    {#if projectedRemainingAllowanceNote}
                      <small>{projectedRemainingAllowanceNote}</small>
                    {/if}
                  </dd>
                </div>
                <div><dt>{TAP_COPY.activeSessionCard}</dt><dd>{activeVisitCardLabel(session)}</dd></div>
              </dl>
            </div>

          </div>
        </article>
      </section>

      <section class="drawer-section">
        <div class="section-head">
          <div>
            <h3>Напиток и кега</h3>
            <p>Контекст напитка, установленной кеги и того, что оператор ожидает увидеть на экране.</p>
          </div>
        </div>

        <dl class="split-details">
          {#each beverageKegRows as row}
            <div>
              <dt>{row.label}</dt>
              <dd>
                <strong>{row.value}</strong>
                {#if row.note}
                  <small>{row.note}</small>
                {/if}
              </dd>
            </div>
          {/each}
        </dl>
      </section>

      <section class="drawer-section">
        <div class="section-head">
          <div>
            <h3>Действия по крану</h3>
            <p>Оперативные команды отделены от сервисных, чтобы первый слой оставался фокусом для оператора.</p>
          </div>
        </div>

        <div class="actions-layout">
          <article class="actions-panel">
            <div class="section-head compact">
              <div>
                <h4>{TAP_COPY.operatorActionsTitle}</h4>
                <p>Команды для текущей смены и реакции на ситуацию по крану.</p>
              </div>
            </div>
            <div class="action-list">
              {#if canControl && session}
                <button class="primary danger" type="button" on:click={() => emit('stop-pour')}>Остановить налив</button>
              {/if}
              {#if canControl}
                <button class="secondary" type="button" aria-label={`${isLocked ? TAP_COPY.unlockTap : TAP_COPY.lockTap} ${tap.display_name}`} on:click={() => emit('toggle-lock')}>
                  {isLocked ? TAP_COPY.unlockTap : TAP_COPY.lockTap}
                </button>
              {/if}
              {#if canDisplayOverride}
                <button class="secondary" type="button" aria-label={`Открыть настройки экрана для ${tap.display_name}`} on:click={() => dispatch('display-settings', { tap })}>Настройки экрана</button>
              {/if}
              <button class="secondary" type="button" on:click={() => openLinkedSession(session?.visitId)}>{TAP_COPY.openSession}</button>
            </div>
          </article>

          {#if serviceActions.length}
            <article class="actions-panel service-panel">
              <div class="section-head compact">
                <div>
                  <h4>{TAP_COPY.serviceActionsTitle}</h4>
                  <p>Сервисные операции доступны только после открытия деталей.</p>
                </div>
              </div>
              <div class="action-list">
                {#each serviceActions as action}
                  <button
                    class={action.tone === 'success' ? 'secondary success' : 'secondary'}
                    type="button"
                    on:click={() => emit(action.key)}
                  >
                    {action.label}
                  </button>
                  <p class="action-note">{action.description}</p>
                {/each}
              </div>
            </article>
          {/if}
        </div>
      </section>

      <section class="drawer-section">
        <div class="section-head">
          <div>
            <h3>История по крану</h3>
            <p>Последние {HISTORY_LIMIT} событий собраны в читаемую хронологию для оператора.</p>
          </div>
        </div>

        {#if chronologyGroups.length}
          <div class="chronology-groups">
            {#each chronologyGroups as group}
              <article class="chronology-group">
                <h4>{group.label}</h4>
                <ul class="events-list">
                  {#each group.items as item}
                    <li class={`tone-${item.tone}`}>
                      <div class="event-main">
                        <div class="event-headline">
                          <strong>{item.timeLabel} · {item.title}</strong>
                          <span class={`priority ${item.tone}`}>{item.priorityLabel}</span>
                        </div>
                        {#if item.summaryLine}
                          <p>{item.summaryLine}</p>
                        {/if}
                        <div class="event-links">
                          {#if item.sessionAction}
                            <a href={item.sessionAction.href} on:click|preventDefault={() => openLinkedSession(item.sessionAction.visitId)}>
                              {item.sessionAction.label}
                            </a>
                          {/if}
                          {#if item.incidentAction}
                            <a href={item.incidentAction.href}>{item.incidentAction.label}</a>
                          {/if}
                        </div>
                      </div>
                      <div class="event-meta">
                        <span>{item.happenedAt ? formatDateTimeRu(item.happenedAt) : 'Время неизвестно'}</span>
                      </div>
                    </li>
                  {/each}
                </ul>
              </article>
            {/each}
          </div>
        {:else}
          <p class="muted">{TAP_COPY.noRecentEvents}</p>
        {/if}
      </section>
    </div>
  </div>
{/if}

<style>
  .tap-drawer {
    min-height: 100%;
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
  }
  .drawer-head,
  .section-head,
  .event-meta,
  .events-list li,
  .info-grid,
  .session-panel {
    display: flex;
    gap: 1rem;
  }
  .drawer-head,
  .section-head,
  .events-list li {
    justify-content: space-between;
    align-items: flex-start;
  }
  .drawer-head {
    position: sticky;
    top: 0;
    z-index: 2;
    padding: 0 0 1rem;
    margin-bottom: 1rem;
    background: linear-gradient(180deg, rgba(248, 250, 252, 1), rgba(248, 250, 252, 0.96));
    border-bottom: 1px solid #e2e8f0;
  }
  .drawer-head h2,
  .drawer-section h3,
  .drawer-head p,
  .chronology-group h4 {
    margin: 0;
  }
  .drawer-body {
    min-height: 0;
    display: grid;
    gap: 1rem;
  }

  .drawer-status {
    margin-top: 0.75rem;
    display: grid;
    gap: 0.55rem;
    padding: 0.8rem;
    border: 1px solid var(--tap-status-hero-border, #e2e8f0);
    border-radius: var(--tap-status-hero-radius, 14px);
    background: var(--tap-status-hero-bg, rgba(255,255,255,0.88));
  }
  .drawer-status-badge {
    width: fit-content;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: var(--tap-status-badge-padding, 0.45rem 0.7rem);
    border-radius: var(--tap-status-badge-radius, 999px);
    border: 1px solid var(--tap-status-badge-border, transparent);
    background: var(--tap-status-badge-bg, #e5e7eb);
    color: var(--tap-status-badge-text, #475569);
    font-size: 0.82rem;
    font-weight: 700;
  }
  .drawer-status-icon {
    width: 1.1rem;
    height: 1.1rem;
    display: inline-grid;
    place-items: center;
    border-radius: var(--tap-status-icon-radius, 999px);
    border: 1px solid var(--tap-status-icon-border, transparent);
    background: var(--tap-status-icon-bg, rgba(255,255,255,0.6));
  }
  .drawer-status-copy {
    display: grid;
    gap: 0.2rem;
  }
  .eyebrow,
  .muted,
  small,
  dt,
  .section-head p,
  .session-copy p {
    color: var(--text-secondary, #64748b);
  }
  .close-btn,
  .primary,
  .secondary {
    border-radius: 10px;
    border: 1px solid #cbd5e1;
    background: #fff;
    padding: 0.6rem 0.8rem;
    font-weight: 600;
  }
  .close-btn {
    flex: 0 0 auto;
  }
  .drawer-section {
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 1rem;
    background: rgba(248,250,252,0.8);
    display: grid;
    gap: 0.8rem;
  }
  .info-grid,
  .session-panel {
    flex-wrap: wrap;
  }
  .info-grid article,
  .session-panel,
  .chronology-group {
    flex: 1 1 320px;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #fff;
    padding: 0.9rem;
  }
  .section-head.compact {
    margin-bottom: 0.25rem;
  }
  .current-session .session-panel {
    justify-content: space-between;
    align-items: stretch;
  }
  .session-copy {
    display: grid;
    gap: 0.55rem;
    flex: 1 1 320px;
  }
  .session-copy strong,
  .event-main strong {
    margin: 0;
  }
  .session-metrics,
  .event-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
  }
  .session-details,
  .split-details {
    margin-top: 0.25rem;
  }
  .actions-layout {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  }
  .actions-panel {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #fff;
    padding: 0.9rem;
    display: grid;
    gap: 0.75rem;
  }
  .service-panel {
    background: #f8fafc;
    border-style: dashed;
  }
  .action-list {
    display: grid;
    gap: 0.65rem;
  }
  .action-note {
    margin: -0.3rem 0 0;
    color: var(--text-secondary, #64748b);
    font-size: 0.88rem;
  }
  .primary {
    background: #1d4ed8;
    color: #fff;
    border-color: #1d4ed8;
  }
  .primary.danger {
    background: #b91c1c;
    border-color: #b91c1c;
  }
  .secondary {
    color: #0f172a;
  }
  .secondary.success {
    border-color: #86efac;
    background: #f0fdf4;
    color: #166534;
  }
  dl {
    display: grid;
    gap: 0.6rem;
    margin: 0.75rem 0 0;
  }
  .split-details {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }
  dl div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }
  dt,
  dd {
    margin: 0;
  }
  dd {
    text-align: right;
    display: grid;
    gap: 0.15rem;
    justify-items: end;
  }
  .chronology-groups,
  .events-list {
    display: grid;
    gap: 0.75rem;
  }
  .events-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .events-list li {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 0.8rem;
    background: #fff;
  }
  .events-list li.tone-critical { border-color: #fecaca; background: #fff7f7; }
  .events-list li.tone-warning { border-color: #fde68a; background: #fffbeb; }
  .events-list li.tone-info { border-color: #bfdbfe; background: #f8fbff; }
  .event-main { display: grid; gap: 0.35rem; flex: 1 1 auto; }
  .event-headline { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }
  .events-list p { margin: 0.2rem 0 0; color: var(--text-secondary, #64748b); }
  .event-links a { color: #1d4ed8; text-decoration: none; font-weight: 600; }
  .event-meta { flex-direction: column; align-items: flex-end; color: var(--text-secondary, #64748b); font-size: 0.84rem; min-width: 140px; }
  .priority { display: inline-flex; padding: 0.2rem 0.55rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
  .priority.critical { background: #fee2e2; color: #b91c1c; }
  .priority.warning { background: #fef3c7; color: #92400e; }
  .priority.info { background: #dbeafe; color: #1d4ed8; }
  .priority.neutral { background: #e5e7eb; color: #475569; }

  @media (max-width: 720px) {
    .drawer-head {
      padding-bottom: 0.85rem;
    }

    dl div,
    .events-list li {
      display: grid;
    }

    dd,
    .event-meta {
      justify-items: start;
      text-align: left;
      align-items: flex-start;
    }
  }
</style>
