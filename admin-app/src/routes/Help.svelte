<script>
  import { roleStore } from '../stores/roleStore.js';
  import { demoGuideStore } from '../stores/demoGuideStore.js';
  import DebugManagementEntry from '../components/system/DebugManagementEntry.svelte';
  import ActivityTrail from '../components/system/ActivityTrail.svelte';
  import { ROUTE_COPY } from '../lib/operator/routeCopy.js';

  const regulations = [
    {
      title: 'Золотые правила смены',
      items: [
        'Сначала проверяем документ и возраст гостя, потом регистрируем или обслуживаем карту.',
        'В спорной ситуации оператор не импровизирует: зовёт старшего смены и фиксирует контекст.',
        'При техническом сбое сохраняем спокойствие, объясняем гостю статус и действуем по сценарию смены.'
      ]
    },
    {
      title: 'Что считать инцидентом',
      items: [
        'Налив не стартует или зависает, когда гость уже у крана.',
        'Карта не читается повторно или NFC-ридер показывает ошибку.',
        'Система ушла в деградацию или офлайн, очередь синхронизации растёт или нужна аварийная остановка.'
      ]
    }
  ];

  const procedures = [
    {
      title: 'Регламент: регистрация и карта гостя',
      steps: [
        'Попросить документ, сверить возраст 21+ и корректность данных.',
        'Открыть админ-панель, найти или создать гостя, заполнить поля точно как в документе.',
        'При выдаче карты выбрать гостя, привязать карту через NFC и подтвердить пополнение при необходимости.'
      ]
    },
    {
      title: 'Регламент: проблема с NFC-ридером',
      steps: [
        'Проверить USB-подключение и питание ридера на рабочем месте.',
        'Перезапустить admin-app или вкладку, затем повторить чтение карты.',
        'Если ошибка сохраняется — сменить USB-порт или перезагрузить ПК, после чего эскалировать администратору.'
      ]
    },
    {
      title: 'Регламент: деградация сети или центрального контура',
      steps: [
        'Сверить, что точка подключена к нужному рабочему адресу, а не к тестовому окружению.',
        'Открыть раздел «Система» и проверить центральный контур, устройства и состояние синхронизации.',
        'Если адрес меняли недавно, зафиксировать изменение и передать инженеру детали: когда, на какой адрес и что перестало работать.'
      ]
    }
  ];

  const responseScenarios = [
    {
      title: 'Карта гостя не работает на кране',
      severity: 'warning',
      actions: [
        'Проверить, что карта привязана к нужному гостю и у визита/баланса нет блокирующих причин.',
        'Уточнить на каком кране проблема и открыть этот кран для проверки статуса.',
        'Если проблема повторяется на нескольких кранах, перейти в «Система» и проверить устройства и синхронизацию.'
      ]
    },
    {
      title: 'Очередь синхронизации растёт',
      severity: 'critical',
      actions: [
        'Открыть «Система» и посмотреть, где деградация: центральный контур, контроллеры или обмен данными.',
        'Не менять конфигурацию в спешке; сначала стабилизировать обслуживание и собрать детали инцидента.',
        'Если требуется, создать инцидент с указанием времени, затронутых кранов и симптомов очереди.'
      ]
    },
    {
      title: 'Нужна аварийная остановка',
      severity: 'critical',
      actions: [
        'Использовать аварийную остановку только в реальной экстренной ситуации или по прямой команде старшего/инженера.',
        'Сразу после остановки предупредить смену и гостей, что новые наливы временно заблокированы.',
        'Дальше работать через раздел «Система» и инциденты: зафиксировать причину, затронутые устройства и условия снятия стопа.'
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
    <h1>Справка смены</h1>
    <p>Раздел с регламентами и сценариями смены доступен старшему смены и инженерным ролям.</p>
  </section>
{:else}
  <section class="page help-page">
    <header class="page-header">
      <div>
        <span class="eyebrow">Справка смены</span>
        <h1>{ROUTE_COPY.help.title}</h1>
        <p>{ROUTE_COPY.help.description} Для технической диагностики переходите в «Система», а сервисные инструменты ниже открываются только по отдельным правам.</p>
      </div>
      <a class="route-link" href="#/system">К состоянию системы</a>
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
          <span class="eyebrow">Регламенты</span>
          <h2>Пошаговые процедуры</h2>
        </div>
        <p>Используйте их как короткие памятки для старшего смены и оператора у стойки.</p>
      </div>

      <div class="sop-grid">
        {#each procedures as procedure}
          <article class="sop-item">
            <h3>{procedure.title}</h3>
            <ol>
              {#each procedure.steps as step}
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
          <span class="eyebrow">Сценарии</span>
          <h2>Короткие сценарии для смены</h2>
        </div>
        <p>Только быстрые шаги: понять симптом, удержать сервис и эскалировать с правильным контекстом.</p>
      </div>

      <div class="playbook-list">
        {#each responseScenarios as item}
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
            <span class="eyebrow">Сервис и инженерия</span>
            <h2>Сервисные точки входа</h2>
          </div>
          <p>Эти инструменты убраны из левой колонки и видны только ролям с инженерными или сервисными правами.</p>
        </div>

        {#if canOpenDemoGuide}
          <div class="support-action-row">
            <div>
              <h3>Сценарий демо</h3>
              <p>Тренировочный сценарий для демо-режима и сервисного показа без перегрузки операторской оболочки.</p>
            </div>
            <button class="demo-button" type="button" on:click={() => demoGuideStore.open()}>Открыть сценарий демо</button>
          </div>
        {/if}

        {#if canOpenDebugEntry}
          <div class="support-panel">
            <h3>Сервисный вход</h3>
            <p>Скрытая точка входа для переключения роли, настроек подключения и инженерных операций.</p>
            <DebugManagementEntry />
          </div>
        {/if}

        {#if canViewActivityTrail}
          <div class="support-panel">
            <h3>Журнал действий интерфейса</h3>
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
