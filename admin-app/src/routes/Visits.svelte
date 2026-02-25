<script>
  import { onMount } from 'svelte';
  import { visitStore } from '../stores/visitStore.js';
  import { uiStore } from '../stores/uiStore.js';
  import { roleStore } from '../stores/roleStore.js';
  import { guestStore } from '../stores/guestStore.js';
  import NFCModal from '../components/modals/NFCModal.svelte';
  import TopUpModal from '../components/modals/TopUpModal.svelte';

  let filterQuery = '';
  let forceUnlockReason = '';
  let forceUnlockComment = '';
  let closeReason = 'guest_checkout';
  let actionError = '';
  let reconcileOpen = false;
  let reconcileShortId = '';
  let reconcileVolumeMl = '';
  let reconcileAmount = '';
  let reconcileReason = 'sync_timeout';
  let reconcileComment = '';

  let openFlowVisible = false;
  let guestQuery = '';
  let openFlowError = '';

  let isNFCModalOpen = false;
  let nfcError = '';
  let isTopUpModalOpen = false;
  let topUpError = '';

  $: visit = $visitStore.currentVisit;
  $: selectedGuest = visit ? $guestStore.guests.find((g) => g.guest_id === visit.guest_id) : null;
  $: lockActive = visit?.active_tap_id !== null && visit?.active_tap_id !== undefined;
  $: lockAgeSeconds = visit?.lock_set_at ? Math.max(0, Math.floor((Date.now() - new Date(visit.lock_set_at).getTime()) / 1000)) : 0;
  $: suggestManualReconcile = lockAgeSeconds >= 60;

  const fullName = (guestLike) => {
    if (!guestLike) return 'вЂ”';
    if (guestLike.guest_full_name) return guestLike.guest_full_name;
    return [guestLike.last_name, guestLike.first_name, guestLike.patronymic].filter(Boolean).join(' ');
  };

  const matchesVisit = (item, query) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (
      (item.guest_full_name || '').toLowerCase().includes(q) ||
      (item.phone_number || '').toLowerCase().includes(q) ||
      (item.card_uid || '').toLowerCase().includes(q) ||
      (item.visit_id || '').toLowerCase().includes(q)
    );
  };

  $: filteredVisits = ($visitStore.activeVisits || []).filter((v) => matchesVisit(v, filterQuery));

  onMount(async () => {
    if ($guestStore.guests.length === 0 && !$guestStore.loading) {
      guestStore.fetchGuests();
    }
    await visitStore.fetchActiveVisits();
  });

  async function refreshVisits() {
    await visitStore.fetchActiveVisits();
    if (visit) {
      const fresh = ($visitStore.activeVisits || []).find((v) => v.visit_id === visit.visit_id);
      if (fresh) {
        visitStore.setCurrentVisit({ ...visit, ...fresh });
      }
    }
  }

  function startOpenFlow() {
    openFlowVisible = true;
    guestQuery = '';
    openFlowError = '';
  }

  $: openCandidates = ($guestStore.guests || []).filter((g) => {
    const q = guestQuery.trim().toLowerCase();
    if (!q) return false;
    const fio = fullName(g).toLowerCase();
    return fio.includes(q) || (g.phone_number || '').toLowerCase().includes(q);
  }).slice(0, 8);

  async function openVisitWithoutCard(guest) {
    openFlowError = '';
    try {
      const opened = await visitStore.openVisit({ guestId: guest.guest_id });
      visitStore.setCurrentVisit(opened);
      await refreshVisits();
      uiStore.notifySuccess('Р’РёР·РёС‚ РѕС‚РєСЂС‹С‚.');
      openFlowVisible = false;
    } catch (error) {
      const message = error?.message || error?.toString?.() || 'РћС€РёР±РєР° РѕС‚РєСЂС‹С‚РёСЏ РІРёР·РёС‚Р°';
      openFlowError = message;
    }
  }

  function selectVisit(item) {
    const fromGuests = $guestStore.guests.find((g) => g.guest_id === item.guest_id);
    visitStore.setCurrentVisit({
      ...item,
      guest_id: item.guest_id,
      guest: fromGuests || null,
    });
    actionError = '';
  }

  async function handleForceUnlock() {
    actionError = '';
    if (!visit) return;
    if (!forceUnlockReason.trim()) {
      uiStore.notifyWarning('РџСЂРёС‡РёРЅР° РѕР±СЏР·Р°С‚РµР»СЊРЅР° РґР»СЏ СЃРЅСЏС‚РёСЏ Р±Р»РѕРєРёСЂРѕРІРєРё.');
      return;
    }

    try {
      const updated = await visitStore.forceUnlock({
        visitId: visit.visit_id,
        reason: forceUnlockReason.trim(),
        comment: forceUnlockComment.trim() || null,
      });
      visitStore.setCurrentVisit(updated);
      await refreshVisits();
      uiStore.notifySuccess('Р‘Р»РѕРєРёСЂРѕРІРєР° СЃРЅСЏС‚Р°.');
      forceUnlockReason = '';
      forceUnlockComment = '';
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'РћС€РёР±РєР° СЃРЅСЏС‚РёСЏ Р±Р»РѕРєРёСЂРѕРІРєРё';
    }
  }

  async function handleCloseVisit() {
    actionError = '';
    if (!visit) return;

    try {
      const closed = await visitStore.closeVisit({
        visitId: visit.visit_id,
        closedReason: closeReason,
        cardReturned: true,
      });
      visitStore.setCurrentVisit(closed);
      await refreshVisits();
      uiStore.notifySuccess('Р’РёР·РёС‚ Р·Р°РєСЂС‹С‚.');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'РћС€РёР±РєР° Р·Р°РєСЂС‹С‚РёСЏ РІРёР·РёС‚Р°';
    }
  }

  async function handleReconcilePour() {
    actionError = '';
    if (!visit) return;
    if (!reconcileShortId.trim() || !reconcileVolumeMl || !reconcileAmount || !reconcileReason.trim()) {
      uiStore.notifyWarning('Fill short_id, volume, amount and reason');
      return;
    }

    try {
      const updated = await visitStore.reconcilePour({
        visitId: visit.visit_id,
        tapId: visit.active_tap_id,
        shortId: reconcileShortId.trim(),
        volumeMl: Number(reconcileVolumeMl),
        amount: String(reconcileAmount).trim(),
        reason: reconcileReason.trim(),
        comment: reconcileComment.trim() || null,
      });
      visitStore.setCurrentVisit(updated);
      await refreshVisits();
      reconcileOpen = false;
      reconcileShortId = '';
      reconcileVolumeMl = '';
      reconcileAmount = '';
      reconcileReason = 'sync_timeout';
      reconcileComment = '';
      uiStore.notifySuccess('Manual reconcile completed');
    } catch (error) {
      actionError = error?.message || error?.toString?.() || 'Manual reconcile failed';
    }
  }

  function handleBindCard() {
    if (!visit) return;
    nfcError = '';
    isNFCModalOpen = true;
  }

  async function handleUidRead(event) {
    nfcError = '';
    try {
      await visitStore.assignCardToVisit({ visitId: visit.visit_id, cardUid: event.detail.uid });
      await refreshVisits();
      uiStore.notifySuccess('РљР°СЂС‚Р° СѓСЃРїРµС€РЅРѕ РїСЂРёРІСЏР·Р°РЅР° Рє РІРёР·РёС‚Сѓ.');
    } catch (error) {
      nfcError = error?.message || error?.toString?.() || 'РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРёРІСЏР·Р°С‚СЊ РєР°СЂС‚Сѓ Рє РІРёР·РёС‚Сѓ';
    }
  }

  function handleOpenTopUpModal() {
    if (!visit) return;
    topUpError = '';
    isTopUpModalOpen = true;
  }

  async function handleSaveTopUp(event) {
    topUpError = '';
    try {
      await guestStore.topUpBalance(visit.guest_id, event.detail);
      await refreshVisits();
      isTopUpModalOpen = false;
      uiStore.notifySuccess(`Р‘Р°Р»Р°РЅСЃ РїРѕРїРѕР»РЅРµРЅ РЅР° ${event.detail.amount}`);
    } catch (error) {
      topUpError = error?.message || error?.toString?.() || 'РћС€РёР±РєР° РїРѕРїРѕР»РЅРµРЅРёСЏ Р±Р°Р»Р°РЅСЃР°';
    }
  }
</script>

{#if !$roleStore.permissions.guests}
  <section class="access-denied ui-card">
    <h2>Р”РѕСЃС‚СѓРї РѕРіСЂР°РЅРёС‡РµРЅ</h2>
    <p>РўРµРєСѓС‰Р°СЏ СЂРѕР»СЊ РЅРµ РїСЂРµРґСѓСЃРјР°С‚СЂРёРІР°РµС‚ СЂР°Р±РѕС‚Сѓ СЃ РІРёР·РёС‚Р°РјРё.</p>
  </section>
{:else}
  <section class="ui-card open-section">
    <h1>РђРєС‚РёРІРЅС‹Рµ РІРёР·РёС‚С‹</h1>
    <button class="primary-open" on:click={startOpenFlow}>РћС‚РєСЂС‹С‚СЊ РЅРѕРІС‹Р№ РІРёР·РёС‚</button>

    {#if openFlowVisible}
      <div class="open-flow">
        <h2>РћС‚РєСЂС‹С‚РёРµ РІРёР·РёС‚Р°</h2>
        <p class="hint">РќР°Р№РґРёС‚Рµ РіРѕСЃС‚СЏ РїРѕ Р¤РРћ РёР»Рё С‚РµР»РµС„РѕРЅСѓ Рё РІС‹Р±РµСЂРёС‚Рµ РµРіРѕ РёР· СЃРїРёСЃРєР°.</p>
        <input type="text" bind:value={guestQuery} placeholder="Р¤РРћ / С‚РµР»РµС„РѕРЅ" />

        {#if guestQuery.trim() && openCandidates.length === 0}
          <p class="not-found">Р“РѕСЃС‚СЊ РЅРµ РЅР°Р№РґРµРЅ</p>
        {/if}

        {#if openCandidates.length > 0}
          <div class="open-candidates">
            {#each openCandidates as candidate}
              <button class="candidate-item" on:click={() => openVisitWithoutCard(candidate)} disabled={$visitStore.loading}>
                <div><strong>{fullName(candidate)}</strong></div>
                <div>{candidate.phone_number} В· Р‘Р°Р»Р°РЅСЃ: {candidate.balance}</div>
              </button>
            {/each}
          </div>
        {/if}

        <button disabled title="Р’С‹РґР°С‡Р° РєР°СЂС‚С‹ Р±СѓРґРµС‚ РґРѕР±Р°РІР»РµРЅР° РѕС‚РґРµР»СЊРЅС‹Рј С€Р°РіРѕРј">Р’С‹РґР°С‡Р° РєР°СЂС‚С‹ Р±СѓРґРµС‚ РґРѕР±Р°РІР»РµРЅР° РѕС‚РґРµР»СЊРЅС‹Рј С€Р°РіРѕРј</button>

        {#if openFlowError}
          <p class="error">{openFlowError}</p>
        {/if}
      </div>
    {/if}
  </section>

  <div class="visits-layout">
    <section class="ui-card list-panel">
      <div class="list-header">
        <h2>РЎРїРёСЃРѕРє Р°РєС‚РёРІРЅС‹С… РІРёР·РёС‚РѕРІ</h2>
        <button on:click={refreshVisits} disabled={$visitStore.loading}>РћР±РЅРѕРІРёС‚СЊ</button>
      </div>
      <input type="text" bind:value={filterQuery} placeholder="Р¤РёР»СЊС‚СЂ: Р¤РРћ / С‚РµР»РµС„РѕРЅ / РєР°СЂС‚Р° / ID РІРёР·РёС‚Р°" />

      {#if $visitStore.loading && $visitStore.activeVisits.length === 0}
        <p>Р—Р°РіСЂСѓР·РєР° Р°РєС‚РёРІРЅС‹С… РІРёР·РёС‚РѕРІ...</p>
      {:else if filteredVisits.length === 0}
        <p class="not-found">Р’РёР·РёС‚ РЅРµ РЅР°Р№РґРµРЅ</p>
      {:else}
        <div class="visit-list">
          {#each filteredVisits as item}
            <button class="visit-item" on:click={() => selectVisit(item)}>
              <div><strong>{item.guest_full_name}</strong></div>
              <div>{item.phone_number}</div>
              <div>{item.card_uid ? `РљР°СЂС‚Р°: ${item.card_uid}` : 'Р‘РµР· РєР°СЂС‚С‹'}</div>
              {#if item.active_tap_id}
                <div class="sync-indicator">processing_sync (tap {item.active_tap_id})</div>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </section>

    <section class="ui-card detail-panel">
      {#if visit}
        <h2>РљР°СЂС‚РѕС‡РєР° РІРёР·РёС‚Р°</h2>
        <div class="visit-fields">
          <div><strong>Р“РѕСЃС‚СЊ:</strong> {fullName(selectedGuest || visit)}</div>
          <div><strong>РўРµР»РµС„РѕРЅ:</strong> {selectedGuest?.phone_number || visit.phone_number || 'вЂ”'}</div>
          <div><strong>РљР°СЂС‚Р°:</strong> {visit.card_uid || 'РќРµ РїСЂРёРІСЏР·Р°РЅР°'}</div>
          <div><strong>РЎС‚Р°С‚СѓСЃ:</strong> {visit.status}</div>
          <div><strong>Р‘Р°Р»Р°РЅСЃ:</strong> {selectedGuest?.balance ?? visit.balance ?? 'вЂ”'}</div>
        </div>

        <div class="lock-state" class:locked={lockActive} class:free={!lockActive}>
          {#if lockActive}
            <strong>Р‘Р»РѕРєРёСЂРѕРІРєР° РЅР° РєСЂР°РЅРµ в„–{visit.active_tap_id}</strong>
            {#if visit.lock_set_at}
              <div>lock_set_at: {new Date(visit.lock_set_at).toLocaleString()}</div>
              <div>age: ~{Math.floor(lockAgeSeconds / 60)} min</div>
            {/if}
            <div>Синхронизация: {suggestManualReconcile ? 'Нужна ручная сверка' : 'Ожидается sync'}</div>
          {:else}
            <strong>РљСЂР°РЅ СЃРІРѕР±РѕРґРµРЅ</strong>
          {/if}
        </div>

        <div class="actions-grid">
          <div class="action-panel">
            <h3>РџСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ СЃРЅСЏС‚СЊ Р±Р»РѕРєРёСЂРѕРІРєСѓ</h3>
            <input type="text" bind:value={forceUnlockReason} placeholder="РџСЂРёС‡РёРЅР° (РѕР±СЏР·Р°С‚РµР»СЊРЅРѕ)" />
            <textarea bind:value={forceUnlockComment} rows="2" placeholder="РљРѕРјРјРµРЅС‚Р°СЂРёР№ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)"></textarea>
            <button on:click={handleForceUnlock} disabled={$visitStore.loading || !lockActive}>РџСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ СЃРЅСЏС‚СЊ Р±Р»РѕРєРёСЂРѕРІРєСѓ</button>
            <button on:click={() => (reconcileOpen = true)} disabled={$visitStore.loading || !lockActive}>Ручная сверка / разблокировать</button>
          </div>

          <div class="action-panel">
            <h3>Р—Р°РєСЂС‹С‚СЊ РІРёР·РёС‚</h3>
            <input type="text" bind:value={closeReason} placeholder="РџСЂРёС‡РёРЅР° Р·Р°РєСЂС‹С‚РёСЏ" />
            <button on:click={handleCloseVisit} disabled={$visitStore.loading || visit.status !== 'active'}>Р—Р°РєСЂС‹С‚СЊ РІРёР·РёС‚</button>
          </div>

          <div class="action-panel">
            <h3>РћРїРµСЂР°С†РёРё</h3>
            {#if !visit.card_uid}
              <button on:click={handleBindCard} disabled={$visitStore.loading}>РџСЂРёРІСЏР·Р°С‚СЊ РєР°СЂС‚Сѓ</button>
            {/if}
            <button on:click={handleOpenTopUpModal} disabled={$visitStore.loading}>РџРѕРїРѕР»РЅРёС‚СЊ Р±Р°Р»Р°РЅСЃ</button>
          </div>
        </div>

        {#if actionError || $visitStore.error}
          <p class="error">{actionError || $visitStore.error}</p>
        {/if}
      {:else}
        <div class="empty-state">
          <h3>Р’РёР·РёС‚ РЅРµ РІС‹Р±СЂР°РЅ</h3>
          <p>Р’С‹Р±РµСЂРёС‚Рµ РІРёР·РёС‚ РёР· СЃРїРёСЃРєР° СЃР»РµРІР°.</p>
        </div>
      {/if}
    </section>
  </div>

  {#if reconcileOpen && visit}
    <section class="ui-card reconcile-modal">
      <h3>Ручная сверка налива</h3>
      <input type="text" bind:value={reconcileShortId} placeholder="short_id (6-8)" maxlength="8" />
      <input type="number" bind:value={reconcileVolumeMl} placeholder="volume_ml" min="1" />
      <input type="number" bind:value={reconcileAmount} placeholder="amount" min="0.01" step="0.01" />
      <input type="text" bind:value={reconcileReason} placeholder="reason" />
      <textarea bind:value={reconcileComment} rows="2" placeholder="comment (optional)"></textarea>
      <div class="modal-actions">
        <button on:click={handleReconcilePour} disabled={$visitStore.loading}>Отправить</button>
        <button on:click={() => (reconcileOpen = false)} disabled={$visitStore.loading}>Отмена</button>
      </div>
    </section>
  {/if}

  {#if isNFCModalOpen}
    <NFCModal
      on:close={() => { isNFCModalOpen = false; }}
      on:uid-read={handleUidRead}
      externalError={nfcError}
    />
  {/if}

  {#if isTopUpModalOpen && visit}
    <TopUpModal
      guestName={fullName(selectedGuest || visit)}
      isSaving={$guestStore.loading}
      on:close={() => { isTopUpModalOpen = false; }}
      on:save={handleSaveTopUp}
    />
    {#if topUpError}<p class="error">{topUpError}</p>{/if}
  {/if}
{/if}

<style>
  .open-section { margin-bottom: 1rem; }
  .primary-open { margin-bottom: 0.75rem; }
  .open-flow {
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    background: var(--bg-surface-muted);
    padding: 0.75rem;
    display: grid;
    gap: 0.75rem;
  }
  .hint { margin: 0; color: var(--text-secondary); }
  .open-candidates { display: grid; gap: 0.5rem; }
  .candidate-item {
    text-align: left;
    background: #fff;
    color: var(--text-primary);
    border: 1px solid var(--border-soft);
  }

  .visits-layout { display: grid; grid-template-columns: minmax(320px, 420px) 1fr; gap: 1rem; }
  .list-panel, .detail-panel { display: grid; gap: 0.75rem; align-content: start; }
  .list-header { display: flex; justify-content: space-between; align-items: center; }
  .list-header h2 { margin: 0; }

  .visit-list { display: grid; gap: 0.5rem; }
  .visit-item {
    text-align: left;
    background: #fff;
    color: var(--text-primary);
    border: 1px solid var(--border-soft);
  }

  .sync-indicator { color: #8a5a00; font-size: 0.85rem; font-weight: 600; }
  .visit-fields { display: grid; gap: 0.4rem; }

  .lock-state { border-radius: 10px; padding: 0.75rem 1rem; border: 1px solid var(--border-soft); }
  .lock-state.locked { background: #fff3cd; border-color: #f0ad4e; color: #8a5a00; }
  .lock-state.free { background: #e9f7ef; border-color: #7bc697; color: #1f6b3d; }

  .actions-grid { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  .action-panel {
    background: var(--bg-surface-muted);
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    padding: 0.75rem;
    display: grid;
    gap: 0.5rem;
  }
  .action-panel h3 { margin: 0; }

  .error { color: #c61f35; }
  .not-found { color: var(--text-secondary); font-weight: 600; }
  .empty-state p { color: var(--text-secondary); }
  .reconcile-modal { margin-top: 1rem; display: grid; gap: 0.5rem; }
  .modal-actions { display: flex; gap: 0.5rem; }
</style>


