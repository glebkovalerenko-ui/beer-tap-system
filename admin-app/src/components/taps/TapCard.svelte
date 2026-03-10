<!-- src/components/taps/TapCard.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { tapStore } from '../../stores/tapStore.js';
  import { kegStore } from '../../stores/kegStore.js';
  import { uiStore } from '../../stores/uiStore.js';
  import { formatTapStatus, formatVolumeRangeRu, formatVolumeRu } from '../../lib/formatters.js';

  export let tap;

  const dispatch = createEventDispatcher();

  $: keg = tap.keg;
  $: kegPercentage = keg ? (keg.current_volume_ml / keg.initial_volume_ml) * 100 : 0;
  // Логика: если нет кеги и кран закрыт или пуст - можно назначить
  $: isAssignable = !tap.keg_id && (tap.status === 'locked' || tap.status === 'empty');
  
  let isLoading = false;

  async function handleUnassign() {
    if (!keg) return;
    const approved = await uiStore.confirm({
      title: 'Подтвердите действие',
      message: `Отключить кегу "${keg.beverage.name}" с ${tap.display_name}?`,
      confirmText: 'Да, снять',
      cancelText: 'Отмена',
      danger: true
    });

    if (approved) {
      isLoading = true;
      try {
        await tapStore.unassignKegFromTap(tap.tap_id);
        kegStore.markKegAsAvailable(keg.keg_id);
      } catch (error) {
        uiStore.notifyError(`Ошибка: ${error}`);
      } finally {
        isLoading = false;
      }
    }
  }

  async function handleStatusChange(newStatus) {
    // Перевод статусов для confirm
    const statusMap = { locked: 'Заблокирован', active: 'Активен', cleaning: 'На промывке', empty: 'Пуст' };
    const approved = await uiStore.confirm({
      title: 'Изменение статуса крана',
      message: `Изменить статус ${tap.display_name} на "${statusMap[newStatus] || newStatus}"?`,
      confirmText: 'Подтвердить',
      cancelText: 'Отмена'
    });

    if (approved) {
      isLoading = true;
      try {
        await tapStore.updateTapStatus(tap.tap_id, newStatus);
      } catch (error) {
        uiStore.notifyError(`Ошибка: ${error}`);
      } finally {
        isLoading = false;
      }
    }
  }
</script>

<div class="tap-card" class:loading={isLoading}>
  {#if isLoading}
    <div class="overlay">
      <div class="spinner"></div>
    </div>
  {/if}

  <div class="card-header">
    <span class="tap-name">{tap.display_name}</span>
    <!-- Статус с цветовым кодированием -->
    <span class="status-badge {tap.status}">
      {formatTapStatus(tap.status)}
    </span>
  </div>

  <div class="card-body">
    {#if keg && keg.beverage}
      <div class="beverage-info">
        <h3 class="beverage-name">{keg.beverage.name}</h3>
        <p class="beverage-style">{keg.beverage.style || 'Стиль не указан'}</p>
      </div>
      
      <div class="progress-container" title={formatVolumeRangeRu(keg.current_volume_ml, keg.initial_volume_ml)}>
        <div class="progress-bar" style="width: {kegPercentage}%" class:low={kegPercentage < 15}></div>
      </div>
      <div class="volume-labels">
        <span>{formatVolumeRu(keg.current_volume_ml)}</span>
        <span class="text-muted">из {formatVolumeRu(keg.initial_volume_ml)}</span>
      </div>
    {:else}
      <div class="empty-state">
        <span class="empty-icon">🍺</span>
        <p>Кега не назначена</p>
      </div>
    {/if}
  </div>

  <div class="card-footer">
    {#if tap.keg_id}
      <button class="btn-action" on:click={() => handleStatusChange(tap.status === 'active' ? 'locked' : 'active')}>
        {tap.status === 'active' ? '🔒 Блок' : '🔓 Открыть'}
      </button>
      <button class="btn-action danger" on:click={handleUnassign}>⏏️ Снять</button>
    {:else}
      {#if tap.status === 'cleaning'}
        <button class="btn-action primary" on:click={() => handleStatusChange('locked')}>✅ Чисто</button>
      {:else}
        <button class="btn-action" on:click={() => handleStatusChange('cleaning')}>🧹 Чистка</button>
        <button class="btn-action primary" on:click={() => dispatch('assign', { tap })} disabled={!isAssignable}>
          📥 Назначить
        </button>
      {/if}
    {/if}
  </div>
</div>

<style>
  .tap-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    height: 100%; /* Растягиваем на всю высоту грида */
    transition: transform 0.2s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
    border: 1px solid #f0f0f0;
  }

  .tap-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  /* Header */
  .card-header {
    padding: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #f5f5f5;
  }

  .tap-name {
    font-weight: 700;
    font-size: 1.1rem;
    color: #333;
  }

  .status-badge {
    font-size: 0.75rem;
    padding: 4px 8px;
    border-radius: 6px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .status-badge.active { background-color: #e6f4ea; color: #1e7e34; }
  .status-badge.locked { background-color: #fce8e6; color: #c5221f; }
  .status-badge.cleaning { background-color: #e8f0fe; color: #1967d2; }
  .status-badge.empty { background-color: #f1f3f4; color: #5f6368; }

  /* Body */
  .card-body {
    padding: 1rem;
    flex-grow: 1; /* Толкает футер вниз */
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .beverage-name { margin: 0 0 0.25rem 0; font-size: 1.2rem; color: #202124; }
  .beverage-style { margin: 0 0 1rem 0; font-size: 0.9rem; color: #5f6368; }

  .progress-container {
    height: 8px;
    background-color: #f1f3f4;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 0.5rem;
  }

  .progress-bar {
    height: 100%;
    background-color: #34a853;
    transition: width 0.5s ease;
  }
  .progress-bar.low { background-color: #fbbc04; }

  .volume-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    font-weight: 500;
  }
  .text-muted { color: #80868b; font-weight: 400; }

  .empty-state {
    text-align: center;
    color: #9aa0a6;
    padding: 1rem 0;
  }
  .empty-icon { font-size: 2rem; display: block; margin-bottom: 0.5rem; opacity: 0.5; }

  /* Footer */
  .card-footer {
    padding: 0.75rem 1rem;
    border-top: 1px solid #f5f5f5;
    background-color: #fff;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }

  .btn-action {
    background: transparent;
    border: 1px solid #dadce0;
    border-radius: 6px;
    padding: 0.5rem;
    font-size: 0.85rem;
    font-weight: 600;
    color: #3c4043;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-action:hover { background-color: #f8f9fa; border-color: #bdc1c6; }
  
  .btn-action.primary {
    background-color: #1a73e8;
    color: white;
    border: none;
  }
  .btn-action.primary:hover { background-color: #1557b0; }
  .btn-action.primary:disabled { background-color: #e8f0fe; color: #aecbfa; cursor: not-allowed; }

  .btn-action.danger { color: #d93025; border-color: #f28b82; }
  .btn-action.danger:hover { background-color: #fce8e6; }

  /* Loading */
  .overlay {
    position: absolute; inset: 0; background: rgba(255,255,255,0.8);
    display: flex; justify-content: center; align-items: center; z-index: 10;
  }
  .spinner {
    width: 24px; height: 24px; border: 3px solid #e8f0fe;
    border-top-color: #1a73e8; border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
