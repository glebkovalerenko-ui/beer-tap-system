# Operator App IA Refactor Result

Дата: 2026-03-25

## Что изменилось

В `admin-app` выполнен переход от system-first структуры к operator-first IA:

- home-маршрут переведён на `#/shift`
- основной навигационный контур теперь: `Визиты`, `Гости`, `Краны`, `Потерянные карты`, `Наливы`, `Кеги и напитки`, `Инциденты`, `Система`
- вторичный тихий блок: `Настройки`, `Справка`
- legacy alias сохранены:
  - `#/today -> #/shift`
  - `#/sessions` и `#/sessions/history -> #/visits`
  - `#/cards-guests -> #/guests`
  - `#/tap-screens -> #/kegs-beverages?tab=screens`

## Operator-first экраны

### Смена

Экран `Смена` собран как обзор живой смены:

- фиксированная KPI-линейка:
  - `Активные визиты`
  - `Льют сейчас`
  - `Инциденты`
  - `Объём за смену`
  - `Выручка за смену`
- левая колонка `Требует внимания`
- правая колонка `Живые события`
- нижние блоки:
  - активные визиты
  - активные наливы
  - краны без кеги / заблокированные

Глобальный `ShellTopBar` сохранён как общая рабочая полоса смены и не дублируется внутри экрана.

### Визиты

Старый session journal переосмыслен как visit-first экран:

- верхняя панель поиска и фильтров под operator flow
- плотный список визитов
- detail view через right drawer
- единые canonical visit statuses:
  - `Активен`
  - `Ожидает действия`
  - `Льёт сейчас`
  - `Завершён`
  - `Требует внимания`
  - `Заблокирован`

### Гости

`Guests` вынесен в primary nav и перестроен под работу с человеком:

- поиск по имени, телефону, карте
- открытие визита
- пополнение
- перевыпуск / привязка карты
- переход в lost-card flow

### Краны

`TapsWorkspace` сохранён как основа, но приведён к операторскому языку:

- первый слой карточек показывает статус, напиток, гостя, налив и primary actions
- второй слой телеметрии остаётся quieter
- display settings вынесены в contextual entry через `Кеги и напитки -> Screens`

### Потерянные карты

`LostCards` переориентирован на фронтовой сценарий:

- поиск
- перевыпуск
- переход к гостю
- переход к визиту
- отмена пометки потерянной карты

### Наливы

Добавлен отдельный operator-раздел `Наливы`:

- журнал платных, non-sale и denied pour episodes
- фильтры по дате, крану, гостю, статусу и problem-class
- detail panel с lifecycle и operator actions

### Кеги и напитки

Раздел оставлен объединённым, но разведен на 3 тихих режима:

- `Напитки`
- `Кеги`
- `Screens`

`Tap Screens` больше не является самостоятельным top-level navigation item.

### Инциденты

`Incidents` сохранён как action queue, а не технический лог:

- связи и переходы переведены на `визит` и `налив`
- поддержаны двусторонние переходы в tap/visit/guest/system context

## Backend и интерфейсы

Добавлены operator-specific projections:

- `GET /api/operator/pours`
- `GET /api/operator/pours/{pour_ref}`
- `GET /api/operator/search`

При этом backend compatibility layer на internal `session` naming сохранён. Operator UI больше не показывает `session` как пользовательский термин.

## Frontend stores и shared модели

Добавлены новые части frontend operator layer:

- `operatorPoursStore`
- `operatorSearchStore`
- `visitStatus.js`

Обновлены:

- `actionRouting`
- `routeCopy`
- realtime route normalization в `operatorConnectionStore`
- shell navigation smoke

## Документированные ограничения

- internal backend/Tauri/auth naming на уровне `session*` не переименовывался массово
- `ShellTopBar` остаётся общей shift bar
- detail view визита пока реализован через drawer, а не отдельную detail route

## Follow-Up: Operator Polish Sprint

После фиксации IA refactor выполнен отдельный узкий polish sprint:

- RU-first cleanup operator copy
- усиление guest/visit-first flows на `Смена`, `Визиты`, `Гости`, `Краны`
- снижение first-layer density
- canonical KPI order для `Смена`
- canonical statuses для `Кранов`, `Визитов`, `Наливов`
- incident hygiene, role wording и degraded UX polish

Этот этап не менял базовую operator-first IA.

Подробный отчёт:

- `docs/admin-app/13-operator-polish-sprint.md`

Что сделано именно в polish sprint:

- operator-facing `session` окончательно убран из active UI
- `Система` и `Справка` приведены к русскоязычному operational language
- `Инциденты` получили severity/aging/dedupe projection
- first layer ключевых экранов стал менее шумным и более action-oriented

Что оставлено на later phases:

- любые новые большие IA moves
- отдельный POS
- массовый rename internal backend/Tauri naming
- отдельная optimisation phase по bundle splitting и расширенным smoke сценариям

## Проверка

Подтверждено следующими командами:

```bash
npm --prefix admin-app run build
npm --prefix admin-app run smoke:navigation-ia
node --test admin-app/src/lib/operator/*.test.js admin-app/src/components/sessions/*.test.js
python -m pytest backend/tests/test_operator_api.py -q
```

На момент фиксации остаются только неблокирующие warning:

- unused CSS selector `.eyebrow` в `admin-app/src/routes/Today.svelte`
- warning Vite о размере бандла > 500 kB после минификации
