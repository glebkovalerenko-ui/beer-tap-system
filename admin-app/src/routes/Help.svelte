<script>
  import { roleStore } from '../stores/roleStore.js';
  import { demoGuideStore } from '../stores/demoGuideStore.js';
  import DebugManagementEntry from '../components/system/DebugManagementEntry.svelte';
  import ActivityTrail from '../components/system/ActivityTrail.svelte';

  const regulations = [
    {
      title: 'Золотые правила смены',
      items: [
        'Сначала проверяем документ и возраст гостя, потом регистрируем или обслуживаем карту.',
        'В спорной ситуации оператор не импровизирует: зовёт старшего смены и фиксирует контекст.',
        'При техническом сбое сохраняем спокойствие, объясняем гостю статус и действуем по playbook.'
      ]
    },
    {
      title: 'Что считать инцидентом',
      items: [
        'Налив не стартует или зависает, когда гость уже у крана.',
        'Карта не читается повторно или NFC-ридер показывает ошибку.',
        'Система ушла в degraded/offline, очередь синхронизации растёт или нужна аварийная остановка.'
      ]
    }
  ];

  const sops = [
    {
      title: 'SOP: регистрация и карта гостя',
      steps: [
        'Попросить документ, сверить возраст 21+ и корректность данных.',
        'Открыть админ-панель, найти или создать гостя, заполнить поля точно как в документе.',
        'При выдаче карты выбрать гостя, привязать карту через NFC и подтвердить пополнение при необходимости.'
      ]
    },
    {
      title: 'SOP: проблема с NFC-ридером',
      steps: [
        'Проверить USB-подключение и питание ридера на рабочем месте.',
        'Перезапустить admin-app или вкладку, затем повторить чтение карты.',
        'Если ошибка сохраняется — сменить USB-порт или перезагрузить ПК, после чего эскалировать администратору.'
      ]
    },
    {
      title: 'SOP: деградация сети или backend',
      steps: [
        'Сверить, что используется правильный backend URL, а не адрес Vite dev server.',
        'Открыть раздел «Система» и проверить backend, устройства и состояние синхронизации.',
        'Если URL меняли недавно, зафиксировать изменение и передать инженеру детали: когда, на какой адрес и что перестало работать.'
      ]
    }
  ];

  const playbooks = [
    {
      title: 'Карта гостя не работает на кране',
      severity: 'warning',
      actions: [
        'Проверить, что карта привязана к нужному гостю и у визита/баланса нет блокирующих причин.',
        'Уточнить на каком кране проблема и открыть этот кран для проверки статуса.',
        'Если проблема повторяется на нескольких кранах, перейти в «Система» и проверить devices/sync.'
      ]
    },
    {
      title: 'Очередь синхронизации растёт',
      severity: 'critical',
      actions: [
        'Открыть «Система» и посмотреть, где деградация: backend, контроллеры или sync.',
        'Не менять конфигурацию в спешке; сначала стабилизировать обслуживание и собрать детали инцидента.',
        'Если требуется, создать инцидент с указанием времени, affected taps и симптомов очереди.'
      ]
    },
    {
      title: 'Нужна аварийная остановка',
      severity: 'critical',
      actions: [
        'Использовать аварийную остановку только в реальной экстренной ситуации или по прямой команде старшего/инженера.',
        'Сразу после остановки предупредить смену и гостей, что новые наливы временно заблокированы.',
        'Дальше работать через раздел «Система» и инциденты: зафиксировать причину, affected devices и условия снятия стопа.'
      ]
    }
  ];

  $: canOpenDemoGuide = $roleStore.permissions.debug_tools;
  $: canOpenDebugEntry = $roleStore.permissions.debug_tools || $roleStore.permissions.role_switch;
  $: canViewActivityTrail = $roleStore.permissions.debug_tools || $roleStore.permissions.system_engineering_actions;
  $: canViewSupportWorkbench = canOpenDemoGuide || canOpenDebugEntry || canViewActivityTrail;
</script>

{#if !$roleStore.permissions.system_health_view}
  <section class="ui-card restricted">
    <h1>Справка / регламенты</h1>
    <p>Раздел с SOP и operator playbooks доступен старшему смены и инженерным ролям.</p>
  </section>
{:else}
  <section class="page help-page">
    <header class="page-header">
      <div>
        <span class="eyebrow">Справка / регламенты</span>
        <h1>Справка / регламенты</h1>
        <p>Структура экрана повторяет действующие инструкции: золотые правила, пошаговые SOP и короткие сценарии для эскалации. Для технической диагностики переходите в «Система», а service/dev entry-point находится ниже и открывается только ролям с отдельными правами.</p>
      </div>
      <a class="route-link" href="#/system">К health и устройствам</a>
    </header>

    <section class="regulations-grid">
      {#each regulations as section}
        <article class="ui-card regulation-card">
          <h2>{section.title}</h2>
          <ul>
            {#each section.items as item}
              <li>{item}</li>
            {/each}
          </ul>
        </article>
      {/each}
    </section>

    <section class="ui-card sop-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">SOP</span>
          <h2>Пошаговые процедуры</h2>
        </div>
        <p>Используйте их как короткие памятки для старшего смены и оператора у стойки.</p>
      </div>

      <div class="sop-grid">
        {#each sops as sop}
          <article class="sop-item">
            <h3>{sop.title}</h3>
            <ol>
              {#each sop.steps as step}
                <li>{step}</li>
              {/each}
            </ol>
          </article>
        {/each}
      </div>
    </section>

    <section class="ui-card playbook-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">Playbooks</span>
          <h2>Короткие сценарии для смены</h2>
        </div>
        <p>Только быстрые шаги: понять симптом, удержать сервис и эскалировать с правильным контекстом.</p>
      </div>

      <div class="playbook-list">
        {#each playbooks as item}
          <article class="playbook-item" data-severity={item.severity}>
            <h3>{item.title}</h3>
            <ol>
              {#each item.actions as action}
                <li>{action}</li>
              {/each}
            </ol>
          </article>
        {/each}
      </div>
    </section>

    {#if canViewSupportWorkbench}
      <section class="ui-card support-workbench">
        <div class="section-head">
          <div>
            <span class="eyebrow">Support / dev</span>
            <h2>Сервисные entry-point'ы</h2>
          </div>
          <p>Эти инструменты убраны из левой колонки и видны только ролям с инженерными или debug-правами.</p>
        </div>

        {#if canOpenDemoGuide}
          <div class="support-action-row">
            <div>
              <h3>DemoGuide</h3>
              <p>Тренировочный сценарий для demo-mode и сервисной демонстрации без засорения operator shell.</p>
            </div>
            <button class="demo-button" type="button" on:click={() => demoGuideStore.open()}>Открыть DemoGuide</button>
          </div>
        {/if}

        {#if canOpenDebugEntry}
          <div class="support-panel">
            <h3>Debug / management</h3>
            <p>Скрытая точка входа для role switch, demo/server settings и инженерных операций.</p>
            <DebugManagementEntry />
          </div>
        {/if}

        {#if canViewActivityTrail}
          <div class="support-panel">
            <h3>Activity trail</h3>
            <p>Локальный журнал интерфейса для диагностики сервисных действий и повторяемости сценариев.</p>
            <ActivityTrail />
          </div>
        {/if}
      </section>
    {/if}
  </section>
{/if}

<style>
  .restricted,.regulation-card,.sop-card,.playbook-card,.support-workbench{padding:1rem}
  .help-page{display:grid;gap:1rem}
  .page-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}
  .page-header h1,.page-header p,.page-header .eyebrow,.support-action-row h3,.support-panel h3{margin:0}
  .page-header div{display:grid;gap:.35rem}
  .eyebrow{font-size:.8rem;color:var(--text-secondary);text-transform:uppercase}
  .route-link{display:inline-flex;align-items:center;justify-content:center;padding:.7rem 1rem;border-radius:.85rem;background:#eef2ff;color:#1e3a8a;text-decoration:none;font-weight:700;white-space:nowrap}
  .regulations-grid,.sop-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}
  .regulation-card h2,.sop-item h3,.playbook-item h3,.sop-card h2,.playbook-card h2,.support-workbench h2{margin:0 0 .75rem}
  .regulation-card ul,.sop-item ol,.playbook-item ol{margin:0;padding-left:1.2rem;display:grid;gap:.65rem}
  .section-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;margin-bottom:1rem}
  .section-head p,.support-action-row p,.support-panel p{margin:0;color:var(--text-secondary);max-width:34rem}
  .sop-item{padding:1rem;border-radius:1rem;background:var(--surface-muted,#f8fafc)}
  .playbook-list,.support-workbench{display:grid;gap:.85rem}
  .playbook-item{padding:1rem;border-radius:1rem;border:1px solid #e5e7eb}
  .playbook-item[data-severity='warning']{background:#fffdf2;border-color:#fde68a}
  .playbook-item[data-severity='critical']{background:#fff5f5;border-color:#fda29b}
  .support-action-row,.support-panel{display:grid;gap:.75rem;padding:1rem;border:1px solid var(--border-soft);border-radius:1rem;background:var(--bg-surface-muted)}
  .support-action-row{grid-template-columns:1fr auto;align-items:center}
  .demo-button{border:1px solid #c7d2fe;background:#eef2ff;color:#1e3a8a;border-radius:.8rem;padding:.8rem 1rem;font-weight:700}
  :global(.support-panel .trail){margin-top:0;padding:0;border:0;box-shadow:none;background:transparent}
  @media (max-width: 960px){.page-header,.regulations-grid,.sop-grid,.support-action-row{grid-template-columns:1fr;display:grid}.route-link,.demo-button{width:max-content}}
</style>
