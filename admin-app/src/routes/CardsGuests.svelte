<script>
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { guestStore } from '../stores/guestStore.js';
  import { visitStore } from '../stores/visitStore.js';
  import { lostCardStore } from '../stores/lostCardStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { shiftStore } from '../stores/shiftStore.js';
  import { pourStore } from '../stores/pourStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { normalizeError } from '../lib/errorUtils.js';
  import { formatDateTimeRu, formatRubAmount } from '../lib/formatters.js';
  import GuestDetail from '../components/guests/GuestDetail.svelte';
  import CardLookupPanel from '../components/guests/CardLookupPanel.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';
  import Modal from '../components/common/Modal.svelte';
  import GuestForm from '../components/guests/GuestForm.svelte';

  let phoneQuery = '';
  let selectedGuestId = null;
  let selectedLookup = null;
  let lookupError = '';
  let pageError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';
  let isManagementModalOpen = false;
  let formError = '';
  let initialLoadAttempted = false;
  let pendingScenario = '';
  let reissueUidInput = '';
  let reissueError = '';
  let reissueStatus = '';
  let isReissueBusy = false;

  $: cardPermissions = $roleStore.permissions;
  $: canAccessCardsGuests = Boolean(cardPermissions.cards_lookup);
  $: canOpenVisit = Boolean(cardPermissions.cards_open_active_session);
  $: canViewHistory = Boolean(cardPermissions.cards_history_view);
  $: canTopUp = Boolean(cardPermissions.cards_top_up);
  $: canToggleBlock = Boolean(cardPermissions.cards_block_manage);
  $: canReissue = Boolean(cardPermissions.cards_reissue_manage);

  const fullName = (guest) => [guest?.last_name, guest?.first_name, guest?.patronymic].filter(Boolean).join(' ');

  $: {
    if (!initialLoadAttempted) {
      guestStore.fetchGuests();
      visitStore.fetchActiveVisits();
      initialLoadAttempted = true;
    }
  }

  $: guests = $guestStore.guests || [];
  $: activeVisits = $visitStore.activeVisits || [];
  $: phoneCandidates = guests.filter((guest) => {
    const q = phoneQuery.trim().toLowerCase();
    if (!q) return false;
    return [
      guest.phone_number,
      guest.id_document,
      guest.guest_id,
      fullName(guest),
      ...(guest.cards || []).map((card) => card.card_uid),
    ].filter(Boolean).some((value) => String(value).toLowerCase().includes(q));
  }).slice(0, 12);
  $: quickLookupResults = phoneCandidates.map((guest) => ({
    guest_id: guest.guest_id,
    label: fullName(guest),
    meta: [guest.phone_number, guest.id_document].filter(Boolean).join(' · ') || 'Без контактов',
    trailing: activeVisits.some((visit) => visit.guest_id === guest.guest_id) ? 'Активный визит' : formatRubAmount(guest.balance),
  }));
  $: selectedGuest = selectedGuestId ? guests.find((guest) => guest.guest_id === selectedGuestId) : null;
  $: selectedGuest = !selectedGuest && selectedLookup?.guest?.guest_id
    ? guests.find((guest) => guest.guest_id === selectedLookup.guest.guest_id) || null
    : selectedGuest;
  $: selectedVisit = selectedGuest ? activeVisits.find((visit) => visit.guest_id === selectedGuest.guest_id) || null : null;
  $: recentGuestPours = selectedGuest
    ? $pourStore.pours.filter((item) => item?.guest?.guest_id === selectedGuest.guest_id).slice(0, 6)
    : [];
  $: lastTapLabel = recentGuestPours[0]?.tap?.display_name || (recentGuestPours[0]?.tap_id ? `Кран #${recentGuestPours[0].tap_id}` : '—');
  $: recentEvents = buildRecentEvents(selectedGuest, selectedVisit, selectedLookup, recentGuestPours);
  $: lookupGuestName = selectedGuest ? fullName(selectedGuest) : (selectedLookup?.guest?.full_name || 'Гость не определён');
  $: hasLookupTarget = Boolean(selectedLookup?.guest?.guest_id || selectedLookup?.active_visit?.visit_id || selectedLookup?.lost_card?.visit_id || selectedLookup?.card_uid || selectedLookup?.card?.uid);
  $: quickActions = buildQuickActions(selectedLookup, selectedGuest, selectedVisit);

  function buildRecentEvents(guest, visit, lookup, pours) {
    if (!guest) return [];
    const items = [];
    if (lookup?.is_lost) {
      items.push({ title: 'Карта в статусе lost', description: lookup.lost_card?.comment || 'Нужна проверка и перевыпуск карты.', timestamp: lookup.lost_card?.reported_at });
    }
    if (visit) {
      items.push({ title: 'Активный визит открыт', description: visit.active_tap_id ? `Сейчас есть лок на кране #${visit.active_tap_id}.` : 'Визит активен, локов сейчас нет.', timestamp: visit.opened_at || visit.updated_at });
    }
    for (const pour of pours.slice(0, 4)) {
      items.push({
        title: `Налив ${pour.beverage?.name || ''}`.trim(),
        description: `${pour.tap?.display_name || `Кран #${pour.tap_id || '—'}`} · ${formatRubAmount(pour.amount_charged || 0)}`,
        timestamp: pour.poured_at,
      });
    }
    for (const tx of (guest.transactions || []).slice(0, 3)) {
      items.push({
        title: tx.type || 'Операция по балансу',
        description: `${formatRubAmount(tx.amount || 0)}`,
        timestamp: tx.created_at,
      });
    }
    return items.filter((item) => item.timestamp).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 6);
  }

  function buildQuickActions(lookup, guest, visit) {
    return [
      {
        id: 'check-card',
        title: 'Проверить карту',
        description: 'Посмотреть статус карты, гостя и последние события без углубления в профиль.',
        disabled: !lookup,
      },
      {
        id: 'top-up',
        title: 'Пополнить баланс',
        description: canTopUp ? 'Сразу открыть пополнение после идентификации гостя.' : 'Недоступно для роли оператора без права на пополнение.',
        disabled: !guest || !canTopUp,
      },
      {
        id: 'open-visit',
        title: 'Открыть активную сессию',
        description: canOpenVisit ? 'Перейти в текущий визит, если карта уже участвует в сессии.' : 'Недоступно без права на переход в активную сессию.',
        disabled: !canOpenVisit || !(visit?.visit_id || lookup?.active_visit?.visit_id || lookup?.lost_card?.visit_id),
      },
      {
        id: 'toggle-block',
        title: guest?.is_active ? 'Блокировать гостя' : 'Разблокировать гостя',
        description: canToggleBlock ? 'Ограничить операции по гостю, не уходя в мастер-данные.' : 'Недоступно без отдельного права на блокировку.',
        disabled: !guest || !canToggleBlock,
      },
      {
        id: 'reissue',
        title: lookup?.is_lost ? 'Перевыпустить lost-карту' : 'Lost / перевыпуск',
        description: canReissue ? 'Отдельный сценарий для lost → перевыпуск → перенос контекста сессии.' : 'Недоступно без права на lost / перевыпуск.',
        disabled: !canReissue || !(guest && (lookup?.is_lost || visit?.visit_id || lookup?.active_visit?.visit_id)),
        tone: lookup?.is_lost ? 'danger' : 'muted',
      },
    ];
  }

  function selectGuest(guestId) {
    selectedGuestId = guestId;
    pageError = '';
    if (!pendingScenario && guestId) pendingScenario = 'check-card';
  }

  async function handleLookup(event) {
    lookupError = '';
    pageError = '';
    reissueError = '';
    reissueStatus = '';
    try {
      selectedLookup = await lostCardStore.resolveCard(event.detail.uid);
      pendingScenario = selectedLookup?.is_lost && canReissue ? 'reissue' : 'check-card';
      if (selectedLookup?.guest?.guest_id) {
        selectedGuestId = selectedLookup.guest.guest_id;
      }
      await visitStore.fetchActiveVisits();
    } catch (error) {
      lookupError = normalizeError(error);
      selectedLookup = null;
    }
  }

  async function handleRestoreLost(event) {
    if (!canReissue) {
      uiStore.notifyWarning('Снятие отметки lost доступно только ролям с правом на перевыпуск.');
      return;
    }
    const uid = event.detail.uid;
    if (!uid) return;
    try {
      await lostCardStore.restoreLostCard(uid);
      selectedLookup = await lostCardStore.resolveCard(uid);
      reissueStatus = 'Отметка lost снята. Можно привязать новую карту и перенести активную сессию.';
      uiStore.notifySuccess('Отметка lost снята');
    } catch (error) {
      lookupError = normalizeError(error);
    }
  }

  function handleOpenVisit() {
    if (!canOpenVisit) {
      uiStore.notifyWarning('Открытие активной сессии недоступно для текущей роли.');
      return;
    }
    const visitId = selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id || selectedLookup?.lost_card?.visit_id;
    if (!visitId) return;
    sessionStorage.setItem('visits.lookupVisitId', visitId);
    window.location.hash = '/sessions';
  }

  function handleOpenHistory() {
    if (!canViewHistory) {
      uiStore.notifyWarning('Просмотр истории недоступен для текущей роли.');
      return;
    }
    const cardUid = selectedLookup?.card_uid || selectedGuest?.cards?.[0]?.card_uid || '';
    if (cardUid) sessionStorage.setItem('sessions.history.cardUid', cardUid);
    window.location.hash = '/sessions/history';
  }

  async function handleOpenNewVisit(event) {
    if (!canOpenVisit) {
      uiStore.notifyWarning('Открытие нового визита недоступно для текущей роли.');
      return;
    }
    try {
      const opened = await visitStore.openVisit({ guestId: event.detail.guestId });
      sessionStorage.setItem('visits.lookupVisitId', opened.visit_id);
      await visitStore.fetchActiveVisits();
      pendingScenario = 'open-visit';
      uiStore.notifySuccess('Открыт новый визит');
    } catch (error) {
      lookupError = normalizeError(error);
    }
  }

  function handleOpenTopUpModal() {
    if (!canTopUp) {
      uiStore.notifyWarning('Пополнение баланса недоступно для текущей роли.');
      return;
    }
    if (!selectedGuest) return;
    if (!get(shiftStore).isOpen) {
      uiStore.notifyWarning('Сначала откройте смену на дашборде, затем выполните пополнение.');
      return;
    }
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
    topUpError = '';
    try {
      await guestStore.topUpBalance(selectedGuest.guest_id, event.detail);
      isTopUpModalOpen = false;
      uiStore.notifySuccess(`Баланс пополнен на ${formatRubAmount(event.detail.amount)}`);
    } catch (error) {
      topUpError = normalizeError(error);
    }
  }

  async function handleToggleBlock() {
    if (!canToggleBlock) {
      uiStore.notifyWarning('Блокировка гостя недоступна для текущей роли.');
      return;
    }
    if (!selectedGuest) return;
    pageError = '';
    try {
      await guestStore.updateGuest(selectedGuest.guest_id, {
        last_name: selectedGuest.last_name,
        first_name: selectedGuest.first_name,
        patronymic: selectedGuest.patronymic || '',
        phone_number: selectedGuest.phone_number,
        date_of_birth: selectedGuest.date_of_birth,
        id_document: selectedGuest.id_document,
        is_active: !selectedGuest.is_active,
      });
      uiStore.notifySuccess(selectedGuest.is_active ? 'Гость заблокирован' : 'Гость разблокирован');
    } catch (error) {
      pageError = normalizeError(error);
    }
  }

  async function handleMarkLost() {
    if (!canReissue) {
      uiStore.notifyWarning('Lost / перевыпуск недоступны для текущей роли.');
      return;
    }
    const visitId = selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id;
    if (!visitId) {
      uiStore.notifyWarning('Пометить lost можно из активного визита с привязанной картой.');
      return;
    }
    try {
      await visitStore.reportLostCard({ visitId, reason: 'operator_marked_lost', comment: null });
      const uid = selectedLookup?.card_uid || selectedGuest?.cards?.[0]?.card_uid;
      if (uid) selectedLookup = await lostCardStore.resolveCard(uid);
      await visitStore.fetchActiveVisits();
      pendingScenario = 'reissue';
      reissueStatus = 'Карта переведена в lost. Для продолжения считайте новую карту и выполните перевыпуск.';
      uiStore.notifySuccess('Карта помечена как lost');
    } catch (error) {
      pageError = normalizeError(error);
    }
  }

  async function handleScenarioAction(event) {
    const { actionId } = event.detail;
    pendingScenario = actionId;
    if (actionId === 'top-up') {
      handleOpenTopUpModal();
      return;
    }
    if (actionId === 'open-visit') {
      handleOpenVisit();
      return;
    }
    if (actionId === 'toggle-block') {
      await handleToggleBlock();
      return;
    }
    if (actionId === 'reissue') {
      reissueError = '';
      reissueStatus = selectedLookup?.is_lost
        ? 'Снимите lost при необходимости, затем считайте новую карту и завершите перевыпуск.'
        : 'Считайте новую карту и перенесите контекст активного визита на неё.';
    }
  }

  async function submitReissue() {
    if (!canReissue) {
      uiStore.notifyWarning('Перевыпуск карты недоступен для текущей роли.');
      return;
    }
    const nextUid = reissueUidInput.trim();
    if (!selectedGuest || !nextUid) return;
    isReissueBusy = true;
    reissueError = '';
    reissueStatus = '';
    try {
      const currentUid = selectedLookup?.card_uid || selectedLookup?.card?.uid || selectedGuest?.cards?.[0]?.card_uid || '';
      if (selectedLookup?.is_lost && currentUid) {
        await lostCardStore.restoreLostCard(currentUid);
      }
      await guestStore.bindCardToGuest(selectedGuest.guest_id, nextUid);
      const targetVisitId = selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id || selectedLookup?.lost_card?.visit_id;
      if (targetVisitId) {
        await visitStore.assignCardToVisit({ visitId: targetVisitId, cardUid: nextUid });
      }
      await Promise.allSettled([guestStore.fetchGuests(), visitStore.fetchActiveVisits()]);
      selectedLookup = await lostCardStore.resolveCard(nextUid);
      selectedGuestId = selectedGuest.guest_id;
      pendingScenario = targetVisitId ? 'open-visit' : 'check-card';
      reissueUidInput = '';
      reissueStatus = targetVisitId
        ? 'Новая карта привязана, активная сессия переведена на неё. Можно открыть сессию дальше.'
        : 'Новая карта привязана к гостю. Активного визита не было — контекст обновлён на новой карте.';
      uiStore.notifySuccess('Перевыпуск карты завершён');
    } catch (error) {
      reissueError = normalizeError(error);
    } finally {
      isReissueBusy = false;
    }
  }

  async function handleSaveGuest(event) {
    if (!canReissue && !canToggleBlock) {
      uiStore.notifyWarning('Редактирование гостя недоступно для текущей роли.');
      return;
    }
    formError = '';
    try {
      await guestStore.updateGuest(selectedGuest.guest_id, event.detail);
      isManagementModalOpen = false;
      uiStore.notifySuccess('Данные гостя обновлены');
    } catch (error) {
      formError = normalizeError(error);
    }
  }

  onMount(async () => {
    await Promise.allSettled([guestStore.fetchGuests(), visitStore.fetchActiveVisits()]);
  });
</script>

{#if !canAccessCardsGuests}
  <section class="access-denied ui-card">
    <h2>Доступ ограничен</h2>
    <p>Текущая роль не предусматривает операции с картами и гостями.</p>
  </section>
{:else}
  <section class="cards-guests-page">
    <header class="page-header ui-card">
      <div>
        <h1>Карты и гости</h1>
        <p>Lookup panel — основной вход для оператора: считайте карту, выберите сценарий и только потом раскрывайте компактный контекст гостя.</p>
      </div>
      <div class="header-actions">
        <button on:click={() => Promise.allSettled([guestStore.fetchGuests(), visitStore.fetchActiveVisits()])} disabled={$guestStore.loading || $visitStore.loading}>Обновить данные</button>
      </div>
    </header>

    <div class="quick-grid">
      <CardLookupPanel
        title="Lookup и решение оператора"
        description="Сначала идентифицируйте карту, затем выберите доступное для роли действие: проверка, сессия, история или разрешённые management-операции."
        result={selectedLookup}
        searchQuery={phoneQuery}
        searchResults={quickLookupResults}
        searchPlaceholder="Номер телефона, UID или идентификатор"
        searchResultLabel="Поиск по номеру / идентификатору"
        error={lookupError}
        loading={$lostCardStore.loading || $visitStore.loading}
        allowRestoreLost={canReissue}
        allowOpenVisit={canOpenVisit}
        allowOpenGuest={Boolean(selectedGuest)}
        allowOpenNewVisit={canOpenVisit}
        openVisitLabel="Открыть активную сессию"
        openGuestLabel="Показать контекст гостя"
        openNewVisitLabel="Открыть новый визит"
        actions={quickActions}
        selectedActionId={pendingScenario}
        on:lookup={handleLookup}
        on:restore-lost={handleRestoreLost}
        on:open-visit={handleOpenVisit}
        on:open-guest={(event) => selectGuest(event.detail.guestId)}
        on:open-new-visit={handleOpenNewVisit}
        on:scenario-action={handleScenarioAction}
        on:search-change={(event) => { phoneQuery = event.detail.value; }}
      />
    </div>

    <div class="operator-layout">
      <section class="ui-card detail-panel">
        {#if selectedGuest}
          <GuestDetail
            guest={selectedGuest}
            activeVisit={selectedVisit}
            cardLookup={selectedLookup}
            recentActivity={recentGuestPours}
            recentEvents={recentEvents}
            lastTapLabel={lastTapLabel}
            variant="operator"
            on:close={() => { selectedGuestId = null; selectedLookup = null; phoneQuery = ''; pendingScenario = ''; }}
            canTopUp={canTopUp}
            canToggleBlock={canToggleBlock}
            canMarkLost={canReissue}
            canOpenHistory={canViewHistory}
            canOpenVisit={canOpenVisit}
            canManageProfile={canReissue || canToggleBlock}
            on:top-up={handleOpenTopUpModal}
            on:toggle-block={handleToggleBlock}
            on:mark-lost={handleMarkLost}
            on:open-history={handleOpenHistory}
            on:open-visit={handleOpenVisit}
            on:open-management={() => { if (!(canReissue || canToggleBlock)) { uiStore.notifyWarning('Редактирование гостя недоступно для текущей роли.'); return; } formError = ''; isManagementModalOpen = true; }}
          />
        {:else}
          <div class="empty-state">
            <h3>Lookup — первый шаг</h3>
            <p>Сначала считайте карту. После успешной идентификации здесь появится компактный операторский контекст: имя, статус карты, баланс, визит, последний кран и события.</p>
          </div>
        {/if}

        {#if pageError || $guestStore.error || $visitStore.error}
          <p class="error">{pageError || $guestStore.error || $visitStore.error}</p>
        {/if}
      </section>

      <section class="ui-card scenario-panel">
        <div class="section-top">
          <div>
            <h2>Текущий сценарий</h2>
            <p>Основное решение принимается сразу после lookup. Детальный профиль гостя остаётся вторичным контекстом справа.</p>
          </div>
          {#if pendingScenario}
            <span class="scenario-badge">{pendingScenario}</span>
          {/if}
        </div>

        {#if !hasLookupTarget}
          <div class="empty-state compact">
            <h3>Нет идентификации</h3>
            <p>Сначала выполните lookup по NFC или UID, чтобы активировать сценарии оператора.</p>
          </div>
        {:else}
          <div class="scenario-stack">
            <section class:active={pendingScenario === 'check-card'} class="scenario-card">
              <h3>Проверить карту</h3>
              <p>Только оперативный summary без перехода в guest master-data.</p>
              <dl>
                <div><dt>Имя</dt><dd>{lookupGuestName}</dd></div>
                <div><dt>Статус карты</dt><dd>{selectedLookup?.is_lost ? 'Lost' : (selectedLookup?.card?.status || selectedGuest?.cards?.[0]?.status || 'Неизвестно')}</dd></div>
                <div><dt>Баланс</dt><dd>{selectedGuest ? formatRubAmount(selectedGuest.balance) : '—'}</dd></div>
                <div><dt>Активный визит</dt><dd>{selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id || 'Нет'}</dd></div>
                <div><dt>Последний кран</dt><dd>{lastTapLabel}</dd></div>
              </dl>
            </section>

            {#if canTopUp}<section class:active={pendingScenario === 'top-up'} class="scenario-card">
              <h3>Пополнить баланс</h3>
              <p>Primary CTA уже доступен в lookup. Здесь — только подтверждение текущего контекста.</p>
              <div class="scenario-note">Гость: <strong>{lookupGuestName}</strong>{selectedGuest ? ` · баланс ${formatRubAmount(selectedGuest.balance)}` : ''}</div>
            </section>{/if}

            {#if canOpenVisit}<section class:active={pendingScenario === 'open-visit'} class="scenario-card">
              <h3>Открыть активную сессию</h3>
              <p>Используйте, когда lookup показал активный визит или lost-карту в рамках действующей сессии.</p>
              <div class="scenario-note">Визит: <strong>{selectedVisit?.visit_id || selectedLookup?.active_visit?.visit_id || selectedLookup?.lost_card?.visit_id || '—'}</strong></div>
            </section>{/if}

            {#if canToggleBlock}<section class:active={pendingScenario === 'toggle-block'} class="scenario-card">
              <h3>{selectedGuest?.is_active ? 'Блокировать гостя' : 'Разблокировать гостя'}</h3>
              <p>Используйте, если нужно немедленно остановить работу по гостю без открытия мастер-данных.</p>
              <div class="scenario-note">Текущий статус гостя: <strong>{selectedGuest?.is_active ? 'активен' : 'заблокирован'}</strong></div>
            </section>{/if}

            {#if canReissue}<section class:active={pendingScenario === 'reissue'} class="scenario-card reissue-card">
              <h3>Lost → перевыпуск → перенос контекста</h3>
              <p>Отдельный операторский flow: потерянную карту можно восстановить, затем привязать новую и перенести на неё активную сессию.</p>
              {#if canReissue && selectedLookup?.is_lost}
                <div class="scenario-warning">
                  <strong>Текущая карта в статусе lost.</strong>
                  <span>Отмечена {formatDateTimeRu(selectedLookup.lost_card?.reported_at)}.</span>
                </div>
              {/if}
              <div class="reissue-input-row">
                <input
                  type="text"
                  bind:value={reissueUidInput}
                  placeholder="Считайте или введите UID новой карты"
                  on:keydown={(event) => event.key === 'Enter' && submitReissue()}
                />
                <button on:click={submitReissue} disabled={isReissueBusy || !reissueUidInput.trim() || !selectedGuest}>Завершить перевыпуск</button>
              </div>
              <ol class="reissue-steps">
                <li>Проверить, что перед вами нужный гость: <strong>{lookupGuestName}</strong>.</li>
                <li>При lost-статусе система снимет отметку и привяжет новую карту к гостю.</li>
                <li>Если у гостя есть активный визит, контекст сессии будет перенесён на новую карту автоматически.</li>
              </ol>
              {#if reissueStatus}
                <p class="reissue-status">{reissueStatus}</p>
              {/if}
              {#if reissueError}
                <p class="error">{reissueError}</p>
              {/if}
            </section>{/if}
          </div>
        {/if}
      </section>
    </div>

    {#if canReissue && selectedLookup?.is_lost}
      <section class="ui-card incident-strip">
        <strong>Карта в статусе lost.</strong>
        <span>Оператор может снять отметку, запустить перевыпуск и перенести активную сессию без перехода в глубокий guest profile.</span>
      </section>
    {/if}
  </section>

  {#if isTopUpModalOpen && selectedGuest}
    <TopUpModal
      guestName={fullName(selectedGuest)}
      isSaving={$guestStore.loading}
      on:close={() => { isTopUpModalOpen = false; }}
      on:save={handleSaveTopUp}
    />
    {#if topUpError}<p class="error">{topUpError}</p>{/if}
  {/if}

  {#if isManagementModalOpen && selectedGuest}
    <Modal on:close={() => { isManagementModalOpen = false; }}>
      <section class="management-modal">
        <div class="section-top">
          <div>
            <h2>Управление профилем гостя</h2>
            <p>Глубокий management path: мастер-данные и редактирование вынесены из основного lookup-flow.</p>
          </div>
        </div>
        <GuestForm guest={selectedGuest} on:save={handleSaveGuest} on:cancel={() => { isManagementModalOpen = false; }} isSaving={$guestStore.loading} />
      </section>
      {#if formError}<p class="error">{formError}</p>{/if}
    </Modal>
  {/if}
{/if}

<style>
  .cards-guests-page { display: grid; gap: 1rem; }
  .page-header { display: flex; justify-content: space-between; gap: 1rem; align-items: end; }
  .page-header h1, .page-header p { margin: 0; }
  .page-header p { color: var(--text-secondary); }
  .quick-grid { display: grid; gap: 1rem; grid-template-columns: 1fr; }
  .operator-layout { display: grid; gap: 1rem; grid-template-columns: minmax(380px, 1fr) minmax(320px, 0.9fr); }
  .detail-panel, .scenario-panel, .management-modal { display: grid; gap: 0.8rem; }
  .section-top { display: flex; justify-content: space-between; gap: 0.75rem; align-items: start; }
  .section-top h2, .section-top p { margin: 0; }
  .empty-state { min-height: 280px; display: grid; align-content: center; gap: 0.5rem; }
  .empty-state.compact { min-height: 180px; }
  .empty-state h3, .empty-state p { margin: 0; }
  .scenario-badge {
    border-radius: 999px; padding: 0.35rem 0.7rem; background: #eef2ff; color: #1d4ed8; font-weight: 700;
    text-transform: capitalize;
  }
  .scenario-stack { display: grid; gap: 0.75rem; }
  .scenario-card {
    display: grid; gap: 0.65rem; padding: 0.9rem; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff;
  }
  .scenario-card.active { border-color: #2563eb; box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12); }
  .scenario-card h3, .scenario-card p, .scenario-card dl { margin: 0; }
  .scenario-card dl { display: grid; gap: 0.45rem; }
  .scenario-card dl div { display: flex; justify-content: space-between; gap: 0.75rem; }
  .scenario-card dt { color: var(--text-secondary); }
  .scenario-note { color: #0f172a; background: #f8fafc; border-radius: 10px; padding: 0.7rem 0.8rem; }
  .reissue-card { background: #fffaf5; border-color: #fdba74; }
  .scenario-warning {
    display: flex; justify-content: space-between; gap: 0.75rem; align-items: center;
    background: #fff7ed; border: 1px solid #fed7aa; border-radius: 12px; padding: 0.75rem 0.85rem;
  }
  .reissue-input-row { display: flex; gap: 0.6rem; flex-wrap: wrap; }
  .reissue-input-row input { flex: 1 1 260px; }
  .reissue-steps { margin: 0; padding-left: 1.15rem; display: grid; gap: 0.35rem; }
  .reissue-status { margin: 0; color: #166534; font-weight: 600; }
  .incident-strip { display: flex; gap: 0.75rem; align-items: center; background: #fff7ed; border-color: #fed7aa; }
  .error { color: #c61f35; margin: 0; }
  @media (max-width: 1180px) {
    .quick-grid, .operator-layout { grid-template-columns: 1fr; }
  }
  @media (max-width: 1024px) {
    .page-header, .section-top, .scenario-warning { flex-direction: column; align-items: start; }
  }
</style>
