<script>
  export let summary = { subsystems: [], health: { sections: {} }, generatedAt: null, error: null };

  const toneLabel = (state) => state === 'ok' ? 'В норме' : state === 'warning' || state === 'degraded' || state === 'unknown' ? 'Нужно проверить' : 'Требуется вмешательство';
</script>

<div class="system-layout">
  <section class="card section-card">
    <div class="section-head">
      <div>
        <span class="eyebrow">Общий статус</span>
        <h2>Критичные сервисы и контур управления</h2>
      </div>
      <span class="status-pill {summary.health.overall}">{toneLabel(summary.health.overall)}</span>
    </div>
    <div class="summary-grid">
      {#each summary.health.sections.overallStatus.items as item (item.name)}
        <article class="summary-item {item.state}">
          <strong>{item.label}</strong>
          <p>{item.detail}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="card section-card">
    <div class="section-head">
      <div>
        <span class="eyebrow">Устройства</span>
        <h2>Контроллеры, экраны и считыватели</h2>
      </div>
    </div>
    <div class="summary-grid device-grid compact">
      {#each summary.health.sections.devices.summary as item (item.key)}
        <article class="summary-item neutral">
          <strong>{item.label}</strong>
          <p>{item.value}</p>
        </article>
      {/each}
    </div>
    <div class="subsystem-grid">
      {#each summary.health.sections.devices.items as subsystem (subsystem.name)}
        <article class="subsystem-card {subsystem.state}">
          <div class="head"><h3>{subsystem.label}</h3><span>{toneLabel(subsystem.state)}</span></div>
          <p>{subsystem.detail}</p>
          {#if subsystem.devices?.length}
            <ul>
              {#each subsystem.devices as device (device.device_id)}
                <li>
                  <strong>{device.tap || device.device_id}</strong>
                  <span>{device.label}</span>
                  {#if device.detail}<small>{device.detail}</small>{/if}
                </li>
              {/each}
            </ul>
          {/if}
        </article>
      {/each}
    </div>
  </section>

  <section class="card section-card">
    <div class="section-head">
      <div>
        <span class="eyebrow">Синхронизация</span>
        <h2>Очереди обмена и свежесть данных</h2>
      </div>
    </div>
    {#each summary.health.sections.syncStatus.items as item (item.name)}
      <article class="summary-item {item.state}">
        <strong>{item.label}</strong>
        <p>{item.detail}</p>
      </article>
    {/each}
    {#if summary.generatedAt}
      <p class="meta-note">Последняя сводка получена: {new Date(summary.generatedAt).toLocaleString('ru-RU')}</p>
    {/if}
  </section>

  <section class="card section-card">
    <div class="section-head">
      <div>
        <span class="eyebrow">Накопившиеся проблемы</span>
        <h2>Что требует разбора сейчас</h2>
      </div>
      <span class="issue-count">{summary.health.sections.accumulatedIssues.subsystemCount + summary.health.sections.accumulatedIssues.deviceCount}</span>
    </div>
    {#if summary.error}
      <div class="alert">Не удалось обновить сводку: {summary.error}</div>
    {/if}
    {#if !summary.health.sections.accumulatedIssues.subsystemCount && !summary.health.sections.accumulatedIssues.deviceCount}
      <p class="empty-state">По агрегированной сводке нет накопившихся проблем. Если оператор видит сбой на точке, проверьте локальные предупреждения рабочего места отдельно.</p>
    {:else}
      <div class="issue-columns">
        <article>
          <h3>Подсистемы</h3>
          <ul>
            {#each summary.health.sections.accumulatedIssues.subsystems as item (item.name)}
              <li><strong>{item.label}</strong><span>{item.detail}</span></li>
            {/each}
          </ul>
        </article>
        <article>
          <h3>Устройства</h3>
          <ul>
            {#each summary.health.sections.accumulatedIssues.devices as item (item.device_id)}
              <li><strong>{item.tap || item.device_id}</strong><span>{item.label}</span>{#if item.detail}<small>{item.detail}</small>{/if}</li>
            {/each}
          </ul>
        </article>
      </div>
    {/if}
  </section>
</div>

<style>
  .system-layout { display:grid; gap:1rem; }
  .card { border: 1px solid #e5e7eb; border-radius: 16px; padding: 1rem; background: #fff; }
  .section-card { display:grid; gap:1rem; }
  .section-head { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
  .eyebrow { display:block; color:var(--text-secondary); font-size:.8rem; text-transform:uppercase; }
  h2,h3,p { margin:0; }
  .status-pill,.issue-count { border-radius:999px; padding:.35rem .75rem; background:#eef2ff; font-weight:700; }
  .status-pill.ok { background:#e9f8ef; color:#116d3a; }
  .status-pill.warning,.status-pill.degraded,.status-pill.unknown { background:#fff8e9; color:#8d5b00; }
  .status-pill.critical,.status-pill.error,.status-pill.offline { background:#ffeef0; color:#9e1f2c; }
  .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:.75rem; }
  .summary-item,.subsystem-card { border-radius:14px; border:1px solid #e5e7eb; padding:.85rem; display:grid; gap:.35rem; }
  .summary-item.ok,.subsystem-card.ok { background:#f8fffb; }
  .summary-item.warning,.summary-item.degraded,.summary-item.unknown,.subsystem-card.warning,.subsystem-card.degraded,.subsystem-card.unknown { background:#fffbeb; }
  .summary-item.critical,.summary-item.error,.summary-item.offline,.subsystem-card.critical,.subsystem-card.error,.subsystem-card.offline { background:#fef2f2; }
  .summary-item.neutral { background:#f8fafc; }
  .subsystem-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; }
  .head { display:flex; justify-content:space-between; gap:1rem; align-items:center; }
  ul { margin:0; padding-left:1rem; display:grid; gap:.5rem; }
  li span, small, .meta-note, .empty-state { color:var(--text-secondary); }
  small { display:block; }
  .issue-columns { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1rem; }
  .alert { padding:.85rem 1rem; border:1px solid #fecaca; border-radius:12px; background:#fef2f2; color:#991b1b; }
  @media (max-width: 860px){ .issue-columns{ grid-template-columns:1fr; } }
</style>
