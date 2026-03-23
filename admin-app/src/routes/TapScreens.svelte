<script>
  // @ts-nocheck
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';

  import Modal from '../components/common/Modal.svelte';
  import TapDisplaySettingsModal from '../components/taps/TapDisplaySettingsModal.svelte';
  import { roleStore } from '../stores/roleStore.js';
  import { sessionStore } from '../stores/sessionStore.js';
  import { tapStore } from '../stores/tapStore.js';
  import { uiStore } from '../stores/uiStore.js';

  let initialLoadAttempted = false;
  let focusedTap = null;
  let isTapDisplayModalOpen = false;

  $: if ($sessionStore.token && !initialLoadAttempted) {
    tapStore.fetchTaps();
    initialLoadAttempted = true;
  }

  $: if (focusedTap) {
    focusedTap = $tapStore.taps.find((item) => item.tap_id === focusedTap.tap_id) || focusedTap;
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
</script>

{#if !$roleStore.permissions.display_override}
  <section class="ui-card restricted">
    <h1>Экраны кранов</h1>
    <p>Текущая роль не предусматривает доступ к управлению экранами кранов.</p>
  </section>
{:else}
  <div class="page-header">
    <div>
      <h1>Экраны кранов</h1>
      <p>Управление экранами кранов и сценариями показа для гостевых дисплеев.</p>
    </div>
  </div>

  <section class="screen-grid">
    <div class="section-header">
      <div>
        <h2>Доступные tap displays</h2>
        <p class="section-hint">Откройте настройки конкретного крана с этого экрана или переходите сюда из quick action на карточке и в drawer.</p>
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
          <article class="display-card ui-card">
            <div class="display-card__head">
              <div>
                <div class="eyebrow">Tap #{tap.tap_id}</div>
                <h3>{tap.display_name}</h3>
                <p>{tap.operations?.beverageName || 'Напиток не назначен'}</p>
              </div>
              <button on:click={() => openDisplaySettings(tap)}>Настройки экрана</button>
            </div>
            <dl>
              <div><dt>Display</dt><dd>{tap.operations?.displayStatus?.label || 'Нет данных'}</dd></div>
              <div><dt>Controller</dt><dd>{tap.operations?.controllerStatus?.label || 'Нет данных'}</dd></div>
              <div><dt>Сценарий</dt><dd>{tap.operations?.productStateLabel || 'Нет данных'}</dd></div>
            </dl>
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
      on:saved={closeDisplaySettings}
    />
  </Modal>
{/if}

<style>
  .page-header,
  .section-header,
  .display-card__head,
  dl div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
  }
  .page-header { margin-bottom: 1rem; }
  .page-header h1, .section-header h2, .display-card__head h3 { margin: 0; }
  .page-header p, .section-hint, .eyebrow, .display-card__head p, dt { margin: 0.3rem 0 0; color: var(--text-secondary, #64748b); }
  .screen-grid, .display-list { display: grid; gap: 1rem; }
  .display-list { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
  .display-card { display: grid; gap: 1rem; padding: 1rem; }
  dl { margin: 0; display: grid; gap: 0.7rem; }
  dt, dd { margin: 0; }
  .error { margin: 0; color: #b91c1c; }
  .restricted { padding: 1rem; }
  @media (max-width: 980px) {
    .page-header, .section-header, .display-card__head, dl div { grid-template-columns: 1fr; display: grid; }
  }
</style>
