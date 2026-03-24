<script>
  import { SESSION_COPY } from '../../lib/operatorLabels.js';

  export let filters;
  export let completionSourceLabels;
  export let loading = false;
  export let onRefresh = () => {};
  export let onApply = () => {};
  export let onReset = () => {};
  export let onPeriodPresetChange = () => {};
</script>

<section class="ui-card filters-panel">
  <div class="filters-title">
    <div>
      <h2>Общий журнал сессий</h2>
      <p>Активные визиты закреплены сверху, а история и поиск работают в одном операторском экране.</p>
    </div>
    <button on:click={onRefresh} disabled={loading}>Обновить</button>
  </div>

  <div class="filters-grid period-grid">
    <label>
      <span>Период</span>
      <select bind:value={filters.periodPreset} on:change={(event) => onPeriodPresetChange(event.currentTarget.value)}>
        <option value="today">Сегодня</option>
        <option value="shift">Текущая смена</option>
        <option value="range">Произвольный диапазон</option>
      </select>
    </label>
    <label><span>Дата от</span><input type="date" bind:value={filters.dateFrom} disabled={filters.periodPreset !== 'range'} /></label>
    <label><span>Дата до</span><input type="date" bind:value={filters.dateTo} disabled={filters.periodPreset !== 'range'} /></label>
    <label><span>Кран</span><input type="number" min="1" bind:value={filters.tapId} placeholder="1" /></label>
    <label>
      <span>Статус</span>
      <select bind:value={filters.status}>
        <option value="">Все</option>
        <option value="active">Активна</option>
        <option value="closed">Завершена</option>
        <option value="aborted">Прервана</option>
      </select>
    </label>
    <label><span>{SESSION_COPY.cardUidVisitId}</span><input bind:value={filters.cardUid} placeholder={SESSION_COPY.cardUidVisitPlaceholder} /></label>
    <label>
      <span>{SESSION_COPY.completionReason}</span>
      <select bind:value={filters.completionSource}>
        <option value="">Все</option>
        <option value="normal">{completionSourceLabels.normal}</option>
        <option value="card_removed">{completionSourceLabels.card_removed}</option>
        <option value="timeout">{completionSourceLabels.timeout}</option>
        <option value="blocked">{completionSourceLabels.blocked}</option>
        <option value="denied">{completionSourceLabels.denied}</option>
        <option value="no_sale_flow">{completionSourceLabels.no_sale_flow}</option>
      </select>
    </label>
    <label class="checkbox"><input type="checkbox" bind:checked={filters.incidentOnly} /> Только с инцидентами</label>
    <label class="checkbox"><input type="checkbox" bind:checked={filters.unsyncedOnly} /> Только с несинхронизированными данными</label>
    <label class="checkbox"><input type="checkbox" bind:checked={filters.zeroVolumeAbortOnly} /> {SESSION_COPY.zeroVolumeAbortOnly}</label>
    <label class="checkbox"><input type="checkbox" bind:checked={filters.activeOnly} /> Только активные</label>
  </div>
  <div class="actions"><button on:click={onApply}>Применить</button><button class="secondary" on:click={onReset}>Сбросить</button></div>
</section>
