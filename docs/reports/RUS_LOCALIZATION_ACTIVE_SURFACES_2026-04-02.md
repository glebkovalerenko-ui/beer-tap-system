# Русификация активных пользовательских поверхностей

Дата: 2026-04-02  
Репозиторий: `beer-tap-system`  
Рабочая ветка на момент оформления: `feature/guest-visit-card-consolidation-sprint1`

## 1. Что закрыто в этом проходе

В этом проходе доведена до русского языка активная операторская поверхность, которая используется в текущем продукте и демо-сценариях:

- `admin-app`: активные маршруты и компоненты для гостей, карт, визитов, потерянных карт, кранов, кегов и напитков, инцидентов и системного обзора;
- `tap-display-client`: пользовательский заголовок вкладки и связанные локализационные хвосты;
- `tap-display-agent`: fallback-экран, который показывается при отсутствии собранного display client;
- нормализация пользовательских ошибок и backend-originated строк, которые раньше доходили в UI на английском;
- статические проверки, чтобы англоязычная копирайт-деградация не возвращалась в активные экраны.

Внутренние enum/reason codes, API payload shape, backend-схемы и служебные runtime-коды в этом проходе не переименовывались.

## 2. Основные изменения по зонам

### Гости, карты, визиты, lost-card flow

- Убраны английские вкрапления в рабочих сценариях поиска карты по NFC/UID, открытия визита, перевыпуска, восстановления и возврата потерянной карты.
- Выровнена терминология вокруг режима только просмотра, недоступных действий, восстановления визита и перевыпуска карты.
- Расширена нормализация типовых ошибок авторизации, поиска сущностей, конфликтов визита/карты и backend detail-сообщений.

### Краны, кеги и напитки

- Переведены mixed-language подписи в карточках кранов, drawer-экранах и настройках Tap Display.
- Закрыты пользовательские хвосты наподобие `Tap Display`, `Fallback`, `override`, `backend`, `sync`.
- Убран показ raw price-mode кодов наподобие `per_100ml` из пользовательского UI.

### Инциденты и система

- Добавлен слой runtime-нормализации для входящих backend-строк, которые приходят в UI как текст, а не как локализованный код.
- Локализованы проблемные строки наподобие `Controller heartbeat stale`, `display assigned`, `reader ready`, `Line is quiet and ready for the next operator action.`, `Emergency stop`, `Incident mutation`, `Session mutation`, `Tap control`, `Visit force unlock`, `flow-closed-valve`.
- В деталях инцидента главным заголовком теперь показывается локализованный тип инцидента вместо сырого `incident_id`.

### Tap Display

- Переведён `<title>` в `tap-display-client`.
- Переведён fallback HTML в `tap-display-agent`.
- Внутренние state/reason codes display-контура оставлены без переименования.

## 3. Техническая реализация

Ключевые изменения собраны в следующих областях:

- UI-слой `admin-app`: маршруты `Guests`, `Visits`, `LostCards`, `System`, `Incidents`, `TapsWorkspace` и связанные активные компоненты;
- store/view-model слой `admin-app`: `visitStore`, `tapStore`, `systemStore`, `incidentStore`, `roleStore`, `errorUtils`, `formatters`, `incidentsViewModel`;
- новый модуль `admin-app/src/lib/copyNormalization.js`, который централизует нормализацию пользовательских backend-строк, blocked-action labels и incident labels;
- тестовые защиты `copyGuard`, `errorUtils.test.js`, `formatters.test.js`, `copyNormalization.test.js`, `incidentsViewModel.test.js`, `tap-display-client/test/localization-copy.test.js`.

## 4. Проверки

В рамках этого прохода были пройдены целевые проверки локализации:

- `node --test src/lib/copyNormalization.test.js src/lib/incidentsViewModel.test.js src/lib/formatters.test.js src/lib/errorUtils.test.js src/lib/operator/copyGuard.test.js src/lib/operator/actionPolicyAdapter.test.js src/lib/operator/cardsGuestsModel.test.js`
  - результат: `20/20` тестов успешно;
- `npm run smoke:error-normalizer` в `admin-app`
  - результат: `passed`;
- `npm test` в `tap-display-client`
  - результат: `passed`;
- `npm run build` в `tap-display-client`
  - результат: `passed`.

## 5. Что осталось вне объёма

- Неактивные legacy-экраны и исторические документы в этом проходе не доочищались.
- Полный `npm run check` для `admin-app` не использовался как критерий этой задачи, потому что в репозитории остаётся большой исторический пласт нерелевантных type-check diagnostics вне локализационного объёма.
- Логическая неконсистентность отдельных tap-status сценариев, где свежие события могут конфликтовать с отсутствием активного визита, не относится к локализации и требует отдельного продуктового/состоянийного прохода.
