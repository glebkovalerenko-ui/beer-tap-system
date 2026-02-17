<script>
  export let taps = [];
  export let kegs = [];
  export let pours = [];
  export let emergencyStop = false;

  const LOW_KEG_THRESHOLD = 0.15;

  function toNumber(value) {
    const parsed = Number.parseFloat(String(value ?? '0').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function isToday(isoValue) {
    if (!isoValue) return false;
    const d = new Date(isoValue);
    const now = new Date();
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  }

  $: poursToday = pours.filter((p) => isToday(p.poured_at));
  $: revenueToday = poursToday.reduce((sum, p) => sum + toNumber(p.amount_charged), 0);
  $: litersToday = poursToday.reduce((sum, p) => sum + (toNumber(p.volume_ml) / 1000), 0);
  $: averageCheck = poursToday.length > 0 ? (revenueToday / poursToday.length) : 0;

  $: activeTaps = taps.filter((t) => t.status === 'active').length;
  $: blockedTaps = taps.filter((t) => t.status === 'locked').length;

  $: lowKegs = kegs.filter((k) => {
    const initial = toNumber(k.initial_volume_ml);
    const current = toNumber(k.current_volume_ml);
    if (!initial || initial <= 0) return false;
    return (current / initial) <= LOW_KEG_THRESHOLD;
  });

  $: beverageStatMap = poursToday.reduce((acc, p) => {
    const name = p?.beverage?.name || 'Неизвестный напиток';
    acc[name] = (acc[name] || 0) + 1;
    return acc;
  }, {});

  $: topBeverage = Object.entries(beverageStatMap).sort((a, b) => b[1] - a[1])[0];

  $: riskItems = [
    emergencyStop
      ? { level: 'critical', text: 'Экстренная остановка активна: наливы заблокированы.' }
      : null,
    lowKegs.length > 0
      ? { level: 'warning', text: `Кеги на исходе: ${lowKegs.length}. Рекомендуется подготовить замену.` }
      : null,
    blockedTaps > 0
      ? { level: 'info', text: `Заблокированных кранов: ${blockedTaps}. Проверьте статус готовности.` }
      : null,
  ].filter(Boolean);

  function fmtMoney(v) {
    return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 2 }).format(v);
  }
</script>

<section class="investor-panel" aria-label="Экран ценности для владельца">
  <div class="panel-header">
    <div>
      <h2>Экран ценности для владельца бара</h2>
      <p>Ключевые показатели за сегодня: выручка, нагрузка, риски и точки роста.</p>
    </div>
  </div>

  <div class="kpi-grid">
    <article class="kpi-card">
      <span class="label">Выручка за сегодня</span>
      <strong>{fmtMoney(revenueToday)}</strong>
      <small>{poursToday.length} наливов</small>
    </article>

    <article class="kpi-card">
      <span class="label">Объем продаж</span>
      <strong>{litersToday.toFixed(1)} л</strong>
      <small>Средний чек: {fmtMoney(averageCheck)}</small>
    </article>

    <article class="kpi-card">
      <span class="label">Активные краны</span>
      <strong>{activeTaps} / {taps.length || 0}</strong>
      <small>Заблокировано: {blockedTaps}</small>
    </article>

    <article class="kpi-card">
      <span class="label">Топ-напиток дня</span>
      <strong>{topBeverage ? topBeverage[0] : 'Недостаточно данных'}</strong>
      <small>{topBeverage ? `${topBeverage[1]} наливов` : 'Добавьте активность для аналитики'}</small>
    </article>
  </div>

  <div class="risk-block">
    <h3>Операционные риски</h3>
    {#if riskItems.length === 0}
      <p class="ok">Критичных рисков не обнаружено. Система работает стабильно.</p>
    {:else}
      <ul>
        {#each riskItems as item}
          <li class={item.level}>{item.text}</li>
        {/each}
      </ul>
    {/if}
  </div>
</section>

<style>
  .investor-panel {
    background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    border: 1px solid #e5edf8;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1.25rem;
  }

  .panel-header h2 { margin: 0; font-size: 1.2rem; }
  .panel-header p { margin: 0.35rem 0 0; color: #5f6c80; font-size: 0.92rem; }

  .kpi-grid {
    margin-top: 1rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.75rem;
  }

  .kpi-card {
    background: #fff;
    border: 1px solid #edf2fa;
    border-radius: 10px;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .kpi-card .label { color: #667085; font-size: 0.83rem; }
  .kpi-card strong { font-size: 1.25rem; color: #101828; line-height: 1.2; }
  .kpi-card small { color: #475467; font-size: 0.82rem; }

  .risk-block { margin-top: 1rem; }
  .risk-block h3 { margin: 0 0 0.5rem; font-size: 1rem; }
  .risk-block ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
  .risk-block li {
    border-radius: 8px;
    padding: 0.6rem 0.75rem;
    border: 1px solid transparent;
    font-size: 0.9rem;
  }
  .risk-block li.critical { background: #fff1f1; border-color: #ffd2d2; color: #9b1c1c; }
  .risk-block li.warning { background: #fff9ec; border-color: #ffebb5; color: #8a5b00; }
  .risk-block li.info { background: #f2f8ff; border-color: #d6e7ff; color: #1d4f91; }
  .risk-block .ok { margin: 0; color: #157347; background: #ecfdf3; border: 1px solid #c7f0d7; border-radius: 8px; padding: 0.6rem 0.75rem; }
</style>
