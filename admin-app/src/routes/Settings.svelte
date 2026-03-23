<script>
  import { roleStore } from '../stores/roleStore.js';

  const workstationActions = [
    {
      title: 'Рабочее место оператора',
      summary: 'Редкие действия для запуска и перенастройки рабочего места перед сменой или после замены оборудования.',
      items: [
        'Проверить, что устройство открыто в desktop/Tauri-режиме, а не только во вкладке dev-сервера.',
        'После замены NFC-ридера или ПК перезапустить admin-app и заново выполнить вход под рабочей ролью.',
        'Если менялся браузерный профиль или ОС-пользователь, повторно подтвердить доступ к локальным устройствам и сохранить рабочую роль.'
      ]
    },
    {
      title: 'Подключение к backend',
      summary: 'Настройки адреса backend нужны только при первичном вводе точки или переносе рабочего места на другой хост.',
      items: [
        'Использовать адрес backend приложения, а не Vite dev server: в dev-среде это отдельный URL вроде http://cybeer-hub:8000.',
        'Для desktop-режима обновить сохранённый runtime-адрес, затем выполнить тест соединения до выдачи рабочего места в смену.',
        'Менять адрес только по согласованному change request; после смены адреса зафиксировать его в инженерном журнале.'
      ]
    },
    {
      title: 'Редкие сервисные настройки',
      summary: 'Эти операции нужны редко и обычно выполняются инженером или владельцем.',
      items: [
        'Пересмотреть состав кранов, экранов и display-профилей после физической перестановки линии.',
        'Обновить служебные параметры рабочего места при вводе новой точки или замене контроллера.',
        'Перед изменением параметров предупредить смену и убедиться, что активные наливы завершены.'
      ]
    }
  ];

  const changeRules = [
    'Любое изменение конфигурации выполняется вне пикового обслуживания или в сервисном окне.',
    'Сначала зафиксируйте текущее значение и причину изменения, затем вносите новую настройку.',
    'После редких изменений вернитесь в раздел «Система» только чтобы убедиться, что health и sync не деградировали.'
  ];

  const handoffChecklist = [
    'Подтвердить, что backend URL и режим запуска записаны в локальный runbook точки.',
    'Сообщить старшему смены, какие настройки менялись и нужен ли повторный вход операторов.',
    'Оставить краткую заметку в инженерном журнале: дата, исполнитель, что изменили и как откатить.'
  ];
</script>

{#if !$roleStore.permissions.settings_manage}
  <section class="ui-card restricted">
    <h1>Настройки</h1>
    <p>Раздел с редкими административными и системными изменениями доступен только инженеру или владельцу.</p>
  </section>
{:else}
  <section class="page settings-page">
    <header class="page-header">
      <div>
        <span class="eyebrow">Настройки</span>
        <h1>Редкие административные и системные настройки</h1>
        <p>Этот экран нужен для нечастых административных изменений: подготовить рабочее место, поменять backend-адрес или скорректировать сервисные параметры точки. Ежедневная работа оператора, контроль инцидентов и health остаются в рабочих разделах и в «Системе».</p>
      </div>
      <a class="route-link" href="#/system">Открыть «Система»</a>
    </header>

    <section class="ui-card callout">
      <strong>Когда сюда заходят</strong>
      <p>Обычно сюда заходят перед запуском новой точки, после замены ПК или ридера, при переносе admin-app на другой backend либо во время согласованных инженерных работ. Для задач смены и любых текущих инцидентов используйте рабочие маршруты и раздел «Система».</p>
    </section>

    <section class="action-grid">
      {#each workstationActions as block}
        <article class="ui-card action-card">
          <div class="card-head">
            <h2>{block.title}</h2>
            <p>{block.summary}</p>
          </div>
          <ul>
            {#each block.items as item}
              <li>{item}</li>
            {/each}
          </ul>
        </article>
      {/each}
    </section>

    <section class="split-grid">
      <article class="ui-card checklist-card">
        <h2>Правила перед изменением</h2>
        <ol>
          {#each changeRules as item}
            <li>{item}</li>
          {/each}
        </ol>
      </article>

      <article class="ui-card checklist-card">
        <h2>Что передать смене после настройки</h2>
        <ol>
          {#each handoffChecklist as item}
            <li>{item}</li>
          {/each}
        </ol>
      </article>
    </section>
  </section>
{/if}

<style>
  .restricted,.callout,.action-card,.checklist-card{padding:1rem}
  .settings-page{display:grid;gap:1rem}
  .page-header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}
  .page-header h1,.page-header p,.page-header .eyebrow{margin:0}
  .page-header div{display:grid;gap:.35rem}
  .eyebrow{font-size:.8rem;color:var(--text-secondary);text-transform:uppercase}
  .route-link{display:inline-flex;align-items:center;justify-content:center;padding:.7rem 1rem;border-radius:.85rem;background:#eef2ff;color:#1e3a8a;text-decoration:none;font-weight:700;white-space:nowrap}
  .callout{display:grid;gap:.35rem;border:1px solid #bfdbfe;background:#eff6ff}
  .callout p,.action-card p{margin:0;color:var(--text-secondary)}
  .action-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}
  .action-card{display:grid;gap:.9rem}
  .card-head{display:grid;gap:.35rem}
  .action-card h2,.checklist-card h2{margin:0}
  .action-card ul,.checklist-card ol{margin:0;padding-left:1.2rem;display:grid;gap:.65rem}
  .split-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}
  @media (max-width: 960px){.page-header,.action-grid,.split-grid{grid-template-columns:1fr;display:grid}.page-header{justify-content:stretch}.route-link{width:max-content}}
</style>
