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
  export let allowOpenVisit = true;
  export let allowOpenGuest = true;
  export let allowOpenNewVisit = false;
  export let openVisitLabel = 'Открыть визит';
  export let openGuestLabel = 'Открыть гостя';
  export let openNewVisitLabel = 'Открыть новый визит';

  const dispatch = createEventDispatcher();

  let uidInput = '';
  let isNfcModalOpen = false;
  let nfcError = '';

  function submitManualLookup() {
    const uid = uidInput.trim();
    if (!uid) return;
    dispatch('lookup', { uid });
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
    </div>
  </div>

  {#if result}
    <div class="lookup-result">
      <div class="lookup-summary">
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
      </div>

      {#if result.is_lost}
        <p class={`lookup-status ${statusTone('danger')}`}>Карта отмечена как потерянная</p>
        <div class="lookup-meta">
          <div><strong>Дата отметки:</strong> {formatDateTimeRu(result.lost_card?.reported_at)}</div>
          <div><strong>Комментарий:</strong> {result.lost_card?.comment || '—'}</div>
          <div><strong>Визит:</strong> {result.lost_card?.visit_id || '—'}</div>
        </div>
      {:else if result.active_visit}
        <p class={`lookup-status ${statusTone('warning')}`}>Карта используется в активном визите</p>
        <div class="lookup-meta">
          <div><strong>Визит:</strong> {result.active_visit.visit_id}</div>
          <div><strong>Лок:</strong> {result.active_visit.active_tap_id ? `Кран #${result.active_visit.active_tap_id}` : 'Нет активного лока'}</div>
        </div>
      {:else if result.guest}
        <p class={`lookup-status ${statusTone('info')}`}>Карта привязана к гостю, активного визита нет</p>
      {:else if result.card}
        <p class={`lookup-status ${statusTone()}`}>Карта зарегистрирована, но не привязана к гостю</p>
      {:else}
        <p class={`lookup-status ${statusTone()}`}>Карта не зарегистрирована в системе</p>
      {/if}

      <div class="lookup-actions">
        {#if allowRestoreLost && result.is_lost}
          <button class="danger-btn" on:click={() => dispatch('restore-lost', { uid: result.card_uid || result.card?.uid })} disabled={loading}>
            Снять отметку lost
          </button>
        {/if}
        {#if allowOpenVisit && hasVisitTarget}
          <button on:click={() => dispatch('open-visit', { visitId: result.active_visit?.visit_id || result.lost_card?.visit_id })}>{openVisitLabel}</button>
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
  .uid-entry input { flex: 1 1 auto; }
  .lookup-result {
    border: 1px solid var(--border-soft, #dbe4f0);
    border-radius: 14px;
    background: var(--bg-surface-muted, #f8fafc);
    padding: 1rem;
    display: grid;
    gap: 0.65rem;
  }
  .lookup-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
  }
  .eyebrow { display: block; font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 0.2rem; }
  .lookup-status { margin: 0; font-weight: 700; }
  .status-danger { color: #b91c1c; }
  .status-warning { color: #92400e; }
  .status-info { color: #1d4ed8; }
  .status-muted { color: var(--text-secondary); }
  .lookup-meta { display: grid; gap: 0.35rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  .lookup-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .error { color: #c61f35; margin: 0; }
  @media (max-width: 720px) {
    .uid-entry { flex-direction: column; }
  }
</style>
