<script>
  export let summary = { subsystems: [], health: { sections: {} }, generatedAt: null, error: null };
  export let canUseEngineeringActions = false;
  export let canManageSystemSettings = false;

  const PROBLEM_STATES = ['warning', 'critical', 'error', 'offline', 'unknown', 'degraded'];

  const toneLabel = (state) => state === 'ok' ? 'В норме' : state === 'warning' || state === 'degraded' || state === 'unknown' ? 'Нужно проверить' : 'Требуется вмешательство';
  const isProblemState = (state) => PROBLEM_STATES.includes(state);

  function navigateTo(path) {
    window.location.hash = path;
  }

  function focusTap(device) {
    const tapId = device?.tap_id || device?.tap || device?.device_id || null;
    if (tapId) {
      sessionStorage.setItem('incidents.focusTapId', String(tapId));
    }
    navigateTo('/taps');
  }

  function focusSystem(source) {
    if (source) {
      sessionStorage.setItem('system.focusSource', source);
    }
    navigateTo('/system');
  }

  function buildActionLink(type, item, fallbackLabel) {
    if (type === 'tap') {
      return {
        label: fallbackLabel || 'Открыть кран',
        action: () => focusTap(item),
      };
    }

    if (type === 'incident') {
      return {
        label: fallbackLabel || 'Открыть инциденты',
        action: () => navigateTo('/incidents'),
      };
    }

    return {
      label: fallbackLabel || 'Открыть sync details',
      action: () => focusSystem(item?.label || item?.name || 'Sync details'),
    };
  }

  function summarizeIssueCount(count, single, plural) {
    return count === 1 ? `1 ${single}` : `${count} ${plural}`;
  }

  function buildOperatorCopy(item, context = {}) {
    const state = item?.state || 'unknown';
    const label = item?.label || context.fallbackLabel || item?.name || 'Подсистема';
    const sourceDetail = item?.detail || '';
    const sourceName = item?.name || context.name || '';

    if (context.kind === 'subsystem') {
      switch (sourceName) {
        case 'backend':
        case 'api':
        case 'server':
          return {
            whatBroken: 'Не отвечает центральный контур управления.',
            impact: 'Операторы могут не увидеть свежие статусы, часть системных действий и подтверждений будет запаздывать.',
            firstCheck: 'Сначала проверьте, обновляется ли сводка и открываются ли связанные инциденты.',
            escalate: 'Эскалируйте инженеру сразу, если сводка не обновляется или точка не может подтвердить действие.',
            nextStep: 'Зафиксируйте масштаб проблемы и откройте список инцидентов для назначения ответственного.',
            detail: sourceDetail,
            primaryAction: buildActionLink('incident', item, 'К инцидентам'),
            secondaryAction: buildActionLink('sync', item, 'К sync details'),
          };
        case 'sync':
        case 'sync-service':
        case 'sync_queue':
        case 'queue':
          return {
            whatBroken: 'Обмен данными идёт с задержкой или остановился.',
            impact: 'Статусы кранов, инциденты и подтверждения действий могут приходить с опозданием.',
            firstCheck: 'Сначала проверьте, растёт ли очередь обмена и есть ли свежая отметка получения сводки.',
            escalate: 'Эскалируйте, если задержка держится дольше одного цикла обновления или влияет на несколько точек.',
            nextStep: 'Перейдите в детали синхронизации и посмотрите, какие очереди или каналы отстают.',
            detail: sourceDetail,
            primaryAction: buildActionLink('sync', item, 'К sync details'),
            secondaryAction: buildActionLink('incident', item, 'Открыть инциденты'),
          };
        case 'controller':
        case 'controllers': {
          const issueCount = item?.devices?.filter((device) => isProblemState(device.state)).length || 0;
          return {
            whatBroken: issueCount ? `Проблемы у контроллеров: ${summarizeIssueCount(issueCount, 'кран', 'крана')}.` : 'Есть риск потери связи с контроллерами.',
            impact: 'Краны могут не подтверждать команды, налив или состояние линии.',
            firstCheck: 'Сначала откройте проблемный кран и посмотрите, отвечает ли контроллер на этой точке.',
            escalate: 'Эскалируйте, если кран не возвращается в норму после базовой проверки на месте.',
            nextStep: 'Начните с первого проблемного крана и подтвердите, локальная это проблема или массовая.',
            detail: sourceDetail,
            primaryAction: buildActionLink('tap', item?.devices?.find((device) => isProblemState(device.state)) || item, 'Открыть проблемный кран'),
            secondaryAction: buildActionLink('incident', item, 'К инцидентам'),
          };
        }
        case 'display-agent':
        case 'display_agent':
        case 'display':
        case 'displays': {
          const issueCount = item?.devices?.filter((device) => isProblemState(device.state)).length || 0;
          return {
            whatBroken: issueCount ? `Часть экранов не показывает нужный контент: ${summarizeIssueCount(issueCount, 'экран', 'экрана')}.` : 'Есть риск, что экранный контент не обновляется.',
            impact: 'Гость может не видеть актуальный ассортимент, инструкции или состояние крана.',
            firstCheck: 'Сначала откройте проблемный кран и убедитесь, что экран работает на месте.',
            escalate: 'Эскалируйте, если экран недоступен на нескольких точках или не восстанавливается после локальной проверки.',
            nextStep: 'Перейдите к конкретному крану, чтобы проверить экран и связанный контекст точки.',
            detail: sourceDetail,
            primaryAction: buildActionLink('tap', item?.devices?.find((device) => isProblemState(device.state)) || item, 'Открыть кран'),
            secondaryAction: buildActionLink('incident', item, 'К инцидентам'),
          };
        }
        case 'reader':
        case 'readers':
        case 'nfc':
        case 'nfc-reader':
        case 'nfc_reader': {
          const issueCount = item?.devices?.filter((device) => isProblemState(device.state)).length || 0;
          return {
            whatBroken: issueCount ? `Есть проблемы со считывателями: ${summarizeIssueCount(issueCount, 'считыватель', 'считывателя')}.` : 'Считыватели работают нестабильно или не видны в сводке.',
            impact: 'Гости и операторы могут не пройти шаг идентификации у крана.',
            firstCheck: 'Сначала откройте проблемный кран и проверьте, видит ли точка карту или считыватель.',
            escalate: 'Эскалируйте, если проблема повторяется на нескольких кранах или мешает началу сессий.',
            nextStep: 'Откройте кран с проблемным считывателем и сверяйте ситуацию на месте.',
            detail: sourceDetail,
            primaryAction: buildActionLink('tap', item?.devices?.find((device) => isProblemState(device.state)) || item, 'Открыть кран'),
            secondaryAction: buildActionLink('incident', item, 'К инцидентам'),
          };
        }
        default:
          return {
            whatBroken: `${label} требует внимания.`,
            impact: 'Проблема может влиять на доступность или управляемость точки.',
            firstCheck: 'Сначала подтвердите, проблема локальная или затрагивает несколько точек.',
            escalate: 'Эскалируйте, если операторская проверка не объясняет причину или влияние расширяется.',
            nextStep: 'Зафиксируйте наблюдение и откройте связанный контекст для дальнейшего разбора.',
            detail: sourceDetail,
            primaryAction: buildActionLink('incident', item, 'К инцидентам'),
            secondaryAction: buildActionLink('sync', item, 'К деталям'),
          };
      }
    }

    if (context.kind === 'device') {
      const subsystem = (item?.subsystem || context.parentLabel || '').toLowerCase();
      const tapLabel = item?.tap || item?.device_id || label;
      const incidentId = item?.incident_id || item?.related_incident_id || item?.incident?.incident_id || null;
      const incidentLabel = incidentId ? `Инцидент #${incidentId}` : 'К инцидентам';
      if (subsystem.includes('контрол')) {
        return {
          whatBroken: `${tapLabel}: контроллер отвечает нестабильно.`,
          impact: 'Кран может не принимать команды или отдавать некорректный статус.',
          firstCheck: 'Сначала откройте карточку крана и проверьте локальный статус контроллера.',
          escalate: 'Эскалируйте, если кран недоступен для налива или не восстанавливает связь.',
          nextStep: 'Проверьте именно этот кран и сверяйте с открытыми инцидентами по точке.',
          detail: sourceDetail,
          primaryAction: buildActionLink('tap', item, 'Открыть кран'),
          secondaryAction: buildActionLink('incident', item, incidentLabel),
        };
      }

      if (subsystem.includes('экран')) {
        return {
          whatBroken: `${tapLabel}: экран требует проверки.`,
          impact: 'Гость не увидит нужный контент или подсказки по использованию.',
          firstCheck: 'Сначала откройте кран и проверьте, что происходит на экране именно этой точки.',
          escalate: 'Эскалируйте, если экран остаётся пустым или показывает неактуальный сценарий.',
          nextStep: 'Перейдите к крану и подтвердите состояние экрана на месте.',
          detail: sourceDetail,
          primaryAction: buildActionLink('tap', item, 'Открыть кран'),
          secondaryAction: buildActionLink('incident', item, incidentLabel),
        };
      }

      if (subsystem.includes('считы')) {
        return {
          whatBroken: `${tapLabel}: считыватель требует проверки.`,
          impact: 'Гость или оператор может не приложить карту и не начать нужный сценарий.',
          firstCheck: 'Сначала откройте кран и проверьте, видит ли он карту или ридер.',
          escalate: 'Эскалируйте, если проблема повторяется после базовой локальной проверки.',
          nextStep: 'Перейдите к крану и сравните состояние устройства с инцидентами по этой точке.',
          detail: sourceDetail,
          primaryAction: buildActionLink('tap', item, 'Открыть кран'),
          secondaryAction: buildActionLink('incident', item, incidentLabel),
        };
      }

      return {
        whatBroken: `${tapLabel}: устройство требует внимания.`,
        impact: 'Сбой может мешать работе точки или подтверждению действий.',
        firstCheck: 'Сначала откройте связанный кран и подтвердите текущий статус на месте.',
        escalate: 'Эскалируйте, если проблема сохраняется после первой проверки.',
        nextStep: 'Перейдите к крану и затем в инциденты, если нужен общий разбор.',
        detail: sourceDetail,
        primaryAction: buildActionLink('tap', item, 'Открыть кран'),
        secondaryAction: buildActionLink('incident', item, incidentLabel),
      };
    }

    if (context.kind === 'summary') {
      if (sourceName === 'backend') {
        return {
          title: label,
          body: isProblemState(state)
            ? 'Центральный контур требует внимания — сначала проверьте, обновляется ли сводка и список инцидентов.'
            : 'Центральный контур работает штатно.',
          detail: sourceDetail,
        };
      }

      if (sourceName === 'sync' || sourceName === 'sync-service' || sourceName === 'sync_queue' || sourceName === 'queue') {
        return {
          title: label,
          body: isProblemState(state)
            ? 'Есть задержка обмена — возможны отставание статусов и поздние подтверждения действий.'
            : 'Очереди обмена и свежесть данных без явных отклонений.',
          detail: sourceDetail,
        };
      }

      return {
        title: label,
        body: isProblemState(state) ? `${label} требуют внимания смены.` : `${label} в рабочем состоянии.`,
        detail: sourceDetail,
      };
    }

    return {
      whatBroken: `${label} требует внимания.`,
      impact: 'Нужна проверка смены.',
      firstCheck: 'Сначала откройте связанный контекст.',
      escalate: 'Эскалируйте, если проблема подтверждается.',
      nextStep: 'Перейдите в связанный раздел.',
      detail: sourceDetail,
      primaryAction: buildActionLink('incident', item, 'К инцидентам'),
      secondaryAction: buildActionLink('sync', item, 'К деталям'),
    };
  }

  function buildOverviewList(section, context) {
    return (section?.items || []).map((item) => ({ ...item, operatorCopy: buildOperatorCopy(item, context) }));
  }

  function buildIssueList(items, context) {
    return (items || []).map((item) => ({ ...item, operatorCopy: buildOperatorCopy(item, context) }));
  }

  function summarizeDevices(devices = []) {
    const problemDevices = devices.filter((device) => isProblemState(device.state));
    if (!devices.length) return 'Нет данных по устройствам';
    return problemDevices.length ? `Нужно проверить ${problemDevices.length} из ${devices.length}` : `Все ${devices.length} в рабочем состоянии`;
  }

  function buildDeviceSection(section) {
    return (section?.items || []).map((subsystem) => ({
      ...subsystem,
      operatorCopy: buildOperatorCopy(subsystem, { kind: 'subsystem', fallbackLabel: subsystem.label }),
      deviceSummary: summarizeDevices(subsystem.devices || []),
      problemDevices: buildIssueList((subsystem.devices || []).filter((device) => isProblemState(device.state)), {
        kind: 'device',
        parentLabel: subsystem.label,
      }),
    }));
  }

  const healthSections = summary?.health?.sections || {};
  $: overallItems = buildOverviewList(healthSections.overallStatus, { kind: 'summary' });
  $: syncItems = buildOverviewList(healthSections.syncStatus, { kind: 'summary' });
  $: deviceSections = buildDeviceSection(healthSections.devices);
  $: actionableSubsystems = buildIssueList(healthSections.accumulatedIssues?.subsystems, { kind: 'subsystem' });
  $: actionableDevices = buildIssueList(healthSections.accumulatedIssues?.devices, { kind: 'device' });
  $: actionableCount = (healthSections.accumulatedIssues?.subsystemCount || 0) + (healthSections.accumulatedIssues?.deviceCount || 0);
  $: engineeringDetails = [
    summary?.branch ? { label: 'Branch', value: summary.branch } : null,
    summary?.commit ? { label: 'Commit', value: summary.commit } : null,
    summary?.build ? { label: 'Build', value: summary.build } : null,
    summary?.generatedAt ? { label: 'Последнее обновление', value: new Date(summary.generatedAt).toLocaleString('ru-RU') } : null,
  ].filter(Boolean);
</script>

<div class="system-layout">
  <section class="card permission-block read-only-block">
    <div class="permission-head">
      <div>
        <span class="eyebrow">Read-only overview</span>
        <h2>Operational health для смены</h2>
      </div>
      <span class="permission-pill">operator / supervisor / engineer</span>
    </div>
    <p class="permission-copy">Первый экран отвечает на четыре операторских вопроса: что сломано, на что это влияет, что проверить первым и когда эскалировать.</p>
  </section>

  <section class="card section-card actionable-card">
    <div class="section-head">
      <div>
        <span class="eyebrow">Накопившиеся проблемы</span>
        <h2>Главный список действий для смены</h2>
      </div>
      <span class="issue-count">{actionableCount}</span>
    </div>
    {#if summary.error}
      <div class="alert">Не удалось обновить сводку: {summary.error}</div>
    {/if}
    {#if !actionableCount}
      <p class="empty-state">По агрегированной сводке нет накопившихся проблем. Если на точке всё же есть жалоба, откройте конкретный кран или инцидент и проверьте локальный контекст.</p>
    {:else}
      <div class="action-groups">
        {#if actionableSubsystems.length}
          <article class="action-group">
            <div class="group-head">
              <h3>Что требует разбора по подсистемам</h3>
              <span>{actionableSubsystems.length}</span>
            </div>
            <div class="action-list">
              {#each actionableSubsystems as item (item.name)}
                <article class="action-card {item.state}">
                  <div class="action-topline">
                    <strong>{item.label}</strong>
                    <span class="status-pill {item.state}">{toneLabel(item.state)}</span>
                  </div>
                  <dl>
                    <div><dt>Что сломано</dt><dd>{item.operatorCopy.whatBroken}</dd></div>
                    <div><dt>На что влияет</dt><dd>{item.operatorCopy.impact}</dd></div>
                    <div><dt>Что проверить первым</dt><dd>{item.operatorCopy.firstCheck}</dd></div>
                    <div><dt>Когда эскалировать</dt><dd>{item.operatorCopy.escalate}</dd></div>
                    <div><dt>Recommended next step</dt><dd>{item.operatorCopy.nextStep}</dd></div>
                  </dl>
                  <div class="action-links">
                    <button class="link-btn" on:click={item.operatorCopy.primaryAction.action}>{item.operatorCopy.primaryAction.label}</button>
                    <button class="link-btn secondary" on:click={item.operatorCopy.secondaryAction.action}>{item.operatorCopy.secondaryAction.label}</button>
                  </div>
                </article>
              {/each}
            </div>
          </article>
        {/if}

        {#if actionableDevices.length}
          <article class="action-group">
            <div class="group-head">
              <h3>Что проверить на конкретных устройствах</h3>
              <span>{actionableDevices.length}</span>
            </div>
            <div class="action-list">
              {#each actionableDevices as item (item.device_id)}
                <article class="action-card {item.state}">
                  <div class="action-topline">
                    <strong>{item.tap || item.device_id}</strong>
                    <span class="status-pill {item.state}">{toneLabel(item.state)}</span>
                  </div>
                  <p class="subsystem-caption">{item.subsystem || 'Устройство'}</p>
                  <dl>
                    <div><dt>Что сломано</dt><dd>{item.operatorCopy.whatBroken}</dd></div>
                    <div><dt>На что влияет</dt><dd>{item.operatorCopy.impact}</dd></div>
                    <div><dt>Что проверить первым</dt><dd>{item.operatorCopy.firstCheck}</dd></div>
                    <div><dt>Когда эскалировать</dt><dd>{item.operatorCopy.escalate}</dd></div>
                    <div><dt>Recommended next step</dt><dd>{item.operatorCopy.nextStep}</dd></div>
                  </dl>
                  <div class="action-links">
                    <button class="link-btn" on:click={item.operatorCopy.primaryAction.action}>{item.operatorCopy.primaryAction.label}</button>
                    <button class="link-btn secondary" on:click={item.operatorCopy.secondaryAction.action}>{item.operatorCopy.secondaryAction.label}</button>
                  </div>
                </article>
              {/each}
            </div>
          </article>
        {/if}
      </div>
    {/if}
  </section>

  <section class="card section-card">
    <div class="section-head">
      <div>
        <span class="eyebrow">Общий статус</span>
        <h2>Что сейчас требует внимания на уровне системы</h2>
      </div>
      <span class="status-pill {summary.health.overall}">{toneLabel(summary.health.overall)}</span>
    </div>
    <div class="summary-grid">
      {#each overallItems as item (item.name)}
        <article class="summary-item {item.state}">
          <strong>{item.operatorCopy.title}</strong>
          <p>{item.operatorCopy.body}</p>
        </article>
      {/each}
    </div>
  </section>

  <section class="card section-card">
    <div class="section-head">
      <div>
        <span class="eyebrow">Устройства</span>
        <h2>Где начать локальную проверку по точкам</h2>
      </div>
    </div>
    <div class="summary-grid device-grid compact">
      {#each healthSections.devices?.summary || [] as item (item.key)}
        <article class="summary-item neutral">
          <strong>{item.label}</strong>
          <p>{item.value}</p>
        </article>
      {/each}
    </div>
    <div class="subsystem-grid">
      {#each deviceSections as subsystem (subsystem.name)}
        <article class="subsystem-card {subsystem.state}">
          <div class="head"><h3>{subsystem.label}</h3><span>{toneLabel(subsystem.state)}</span></div>
          <p>{subsystem.operatorCopy.whatBroken}</p>
          <p class="muted">{subsystem.deviceSummary}</p>
          <div class="checklist">
            <div><strong>Что проверить первым</strong><span>{subsystem.operatorCopy.firstCheck}</span></div>
            <div><strong>Когда эскалировать</strong><span>{subsystem.operatorCopy.escalate}</span></div>
            <div><strong>Recommended next step</strong><span>{subsystem.operatorCopy.nextStep}</span></div>
          </div>
          <div class="action-links">
            <button class="link-btn" on:click={subsystem.operatorCopy.primaryAction.action}>{subsystem.operatorCopy.primaryAction.label}</button>
            <button class="link-btn secondary" on:click={subsystem.operatorCopy.secondaryAction.action}>{subsystem.operatorCopy.secondaryAction.label}</button>
          </div>
          {#if subsystem.problemDevices?.length}
            <ul class="problem-device-list">
              {#each subsystem.problemDevices as device (device.device_id)}
                <li>
                  <div>
                    <strong>{device.tap || device.device_id}</strong>
                    <span>{device.operatorCopy.whatBroken}</span>
                  </div>
                  <button class="inline-link" on:click={device.operatorCopy.primaryAction.action}>К крану</button>
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
        <h2>Влияет ли обмен данными на операционную работу</h2>
      </div>
    </div>
    <div class="summary-grid">
      {#each syncItems as item (item.name)}
        <article class="summary-item {item.state}">
          <strong>{item.operatorCopy.title}</strong>
          <p>{item.operatorCopy.body}</p>
          {#if isProblemState(item.state)}
            <div class="action-links compact-links">
              <button class="link-btn" on:click={() => focusSystem(item.label || item.name)}>Открыть sync details</button>
              <button class="link-btn secondary" on:click={() => navigateTo('/incidents')}>Посмотреть инциденты</button>
            </div>
          {/if}
        </article>
      {/each}
    </div>
  </section>

  {#if canUseEngineeringActions || canManageSystemSettings}
    <section class="card permission-block advanced-block">
      <div class="permission-head">
        <div>
          <span class="eyebrow">Advanced access</span>
          <h2>Инженерная зона по отдельным правам</h2>
        </div>
        <span class="permission-pill warn">permission gate</span>
      </div>
      <p class="permission-copy">Branch/commit, инженерные инструменты и глубокие настройки вынесены из первого экрана. Показывайте их только после отдельного permission gate.</p>
      {#if engineeringDetails.length}
        <details class="deep-details">
          <summary>Показать branch / commit / build context</summary>
          <ul>
            {#each engineeringDetails as item (item.label)}
              <li><strong>{item.label}:</strong> <span>{item.value}</span></li>
            {/each}
          </ul>
        </details>
      {/if}
      <div class="advanced-grid">
        {#if canUseEngineeringActions}
          <article class="advanced-card">
            <h3>Инженерные инструменты</h3>
            <p>Сервисные команды, расширенная диагностика и действия восстановления держите только в этой углублённой зоне.</p>
          </article>
        {/if}
        {#if canManageSystemSettings}
          <article class="advanced-card">
            <h3>Глубокие настройки</h3>
            <p>Конфигурационные и management-изменения должны открываться отдельно от operator-friendly health overview.</p>
          </article>
        {/if}
      </div>
    </section>
  {/if}
</div>

<style>
  .system-layout { display:grid; gap:1rem; }
  .card { border: 1px solid #e5e7eb; border-radius: 16px; padding: 1rem; background: #fff; }
  .section-card, .action-group, .action-list { display:grid; gap:1rem; }
  .section-head, .permission-head, .group-head { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
  .eyebrow { display:block; color:var(--text-secondary); font-size:.8rem; text-transform:uppercase; }
  h2,h3,p { margin:0; }
  .status-pill,.issue-count,.permission-pill { border-radius:999px; padding:.35rem .75rem; background:#eef2ff; font-weight:700; }
  .permission-pill { color:#1d4ed8; }
  .permission-pill.warn { background:#fff7ed; color:#9a3412; }
  .status-pill.ok { background:#e9f8ef; color:#116d3a; }
  .status-pill.warning,.status-pill.degraded,.status-pill.unknown { background:#fff8e9; color:#8d5b00; }
  .status-pill.critical,.status-pill.error,.status-pill.offline { background:#ffeef0; color:#9e1f2c; }
  .summary-grid, .action-groups { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:.75rem; }
  .summary-item,.subsystem-card,.advanced-card,.action-card { border-radius:14px; border:1px solid #e5e7eb; padding:.85rem; display:grid; gap:.6rem; }
  .summary-item.ok,.subsystem-card.ok,.action-card.ok { background:#f8fffb; }
  .summary-item.warning,.summary-item.degraded,.summary-item.unknown,.subsystem-card.warning,.subsystem-card.degraded,.subsystem-card.unknown,.action-card.warning,.action-card.degraded,.action-card.unknown { background:#fffbeb; }
  .summary-item.critical,.summary-item.error,.summary-item.offline,.subsystem-card.critical,.subsystem-card.error,.subsystem-card.offline,.action-card.critical,.action-card.error,.action-card.offline { background:#fef2f2; }
  .summary-item.neutral,.advanced-card { background:#f8fafc; }
  .permission-block { display:grid; gap:.75rem; }
  .read-only-block { background:#f8fbff; border-color:#bfdbfe; }
  .advanced-block { background:#fffbeb; border-color:#fcd34d; }
  .actionable-card { border-color:#f59e0b; box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.18); }
  .permission-copy, .muted, .subsystem-caption, .empty-state, .meta-note { color:var(--text-secondary); }
  .subsystem-grid, .advanced-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; }
  .head { display:flex; justify-content:space-between; gap:1rem; align-items:center; }
  .checklist, .deep-details ul { display:grid; gap:.5rem; }
  .checklist div { display:grid; gap:.15rem; }
  .problem-device-list, .deep-details ul { margin:0; padding-left:1rem; }
  .problem-device-list { display:grid; gap:.5rem; }
  .problem-device-list li { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
  .problem-device-list li div { display:grid; gap:.2rem; }
  dl { margin:0; display:grid; gap:.65rem; }
  dl div { display:grid; gap:.15rem; }
  dt { font-weight:700; color:#0f172a; }
  dd { margin:0; color:#334155; }
  .action-topline { display:flex; justify-content:space-between; gap:.75rem; align-items:flex-start; }
  .action-links { display:flex; flex-wrap:wrap; gap:.5rem; }
  .compact-links { margin-top:.35rem; }
  .link-btn, .inline-link { border-radius:10px; border:1px solid #bfdbfe; background:#eff6ff; color:#1d4ed8; padding:.55rem .8rem; font-weight:700; cursor:pointer; }
  .link-btn.secondary, .inline-link { background:#fff; border-color:#cbd5e1; color:#0f172a; }
  .inline-link { padding:.4rem .65rem; }
  .alert { padding:.85rem 1rem; border:1px solid #fecaca; border-radius:12px; background:#fef2f2; color:#991b1b; }
  .deep-details summary { cursor:pointer; font-weight:700; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
  @media (max-width: 860px){ .problem-device-list li { display:grid; } }
</style>
