# Operator Polish Sprint

Дата: 2026-03-26

## 1. Scope

В `admin-app` выполнен узкий operator polish sprint поверх уже внедрённой operator-first IA.

Что входило в scope:

- RU-first copy cleanup на активных operator-экранах
- усиление guest/visit-first presentation
- снижение плотности первого слоя
- фиксация canonical KPI strip на `Смена`
- фиксация canonical statuses для `Кранов`, `Визитов` и `Наливов`
- дисциплина по `Инцидентам`
- понятная role/degraded presentation

Что не входило в scope:

- новый IA rewrite
- отдельный POS
- массовое переименование internal `session*` naming в backend/Tauri/auth
- расширение доменной модели

## 2. Operator Problems Addressed

Спринт закрывает следующие проблемы, выявленные после IA refactor:

- первый слой был слишком плотным и равновесным по визуальному весу
- `Визиты` и `Гости` были продуктово слабее, чем нужно оператору на смене
- в active UI оставались mixed RU/EN формулировки
- в operator-facing copy ещё протекали `session`-термины
- `Инциденты` рисковали превращаться в шумный лог
- degraded/read-only surfaces выглядели слишком техническими

## 3. Copy Cleanup

Проведён RU-first cleanup на активных operator surfaces:

- `Смена`
- `Визиты`
- `Гости`
- `Краны`
- `Наливы`
- `Инциденты`
- `Система`
- `Справка`
- global shell/status/degraded surfaces

Что сделано:

- убраны operator-facing `session`/`sessions` там, где по смыслу речь о `Визите` или `Наливе`
- локализованы CTA, helper text, banners, status copy и drawer copy
- локализованы role-sensitive action dialogs и reason-code surfaces
- добавлен copy guard test на возврат смешанных фраз вроде `Read-only mode`, `Debug / management`, `Display context`, `DemoGuide`

## 4. Guest/Visit-First Improvements

### Смена

Экран `Смена` теперь сильнее отвечает на три вопроса:

- кто требует внимания
- кто льёт сейчас
- какие визиты активны

Нижний слой перестроен вокруг:

- `Проблемные визиты`
- `Льют сейчас`
- `Активные визиты`

### Визиты

Экран `Визиты` закреплён как visit-first screen:

- summary strip сокращён до action-driving метрик
- вторичные счётчики унесены в quieter layer
- строки списка читаются как: гость -> статус визита -> кран -> последнее действие -> следующий шаг

### Гости

В action row усилены основные operator flows:

- `Открыть визит` / `Продолжить визит`
- `Пополнить`
- `Привязать / перевыпустить карту`
- `Потерянная карта`

### Краны

Карточка крана и drawer сильнее показывают:

- что происходит
- какой гость и визит вовлечены
- что делать оператору сейчас

Системная телеметрия при этом осталась доступной, но ушла во вторичный слой.

## 5. Density Reduction Decisions

Вместо удаления полезных данных перераспределён визуальный вес:

- `Смена`: fixed KPI strip наверху, action-driven visit panels ниже, quieter secondary cues
- `Визиты`: меньше равноправных summary blocks, плотнее и быстрее читаемый журнал
- `Краны`: гость/визит и primary actions подняты выше телеметрии
- `Инциденты`: карточка сначала показывает тип проблемы, воздействие и следующий шаг
- `Система`: first layer говорит о том, что не так и что сейчас ограничено, а не о глубокой диагностике

## 6. Canonical KPI Strip

На `Смена` зафиксирован стабильный порядок KPI:

1. `Активные визиты`
2. `Льют сейчас`
3. `Инциденты`
4. `Объём за смену`
5. `Выручка за смену`

Порядок вынесен в shared model и покрыт тестом, чтобы не плавал от окружения к окружению.

## 7. Canonical Status Taxonomy

Закреплён конечный operator-facing набор статусов.

### Краны

- `Готов`
- `Льёт`
- `Нужна помощь`
- `Недоступен`
- `Синхронизация`
- `Нет кеги`

### Визиты

- `Активен`
- `Ожидает действия`
- `Льёт сейчас`
- `Завершён`
- `Требует внимания`
- `Заблокирован`

### Наливы

Добавлен shared normalizer `pourStatus.js` с canonical labels:

- `Успешно`
- `Остановлен`
- `Таймаут`
- `Карта убрана`
- `Отклонён`
- `Без продажи`
- `Ошибка`

Raw backend completion details сохранены только как secondary diagnostic detail.

## 8. Incident/Alarm Hygiene

Экран `Инциденты` и shared incident projection усилены следующим:

- dedupe exact duplicate related events по stable fingerprint
- явная UI severity:
  - `Инфо`
  - `Предупреждение`
  - `Критично`
- явный aging cue:
  - `Новый`
  - `Стареет`
  - `Просрочен`
- distinction between `инцидент, требующий действия` и `событие`

Дополнительно:

- `slaRisk` filter теперь покрывает и aging, и overdue incidents
- detail panel и list card подсказывают next step, а не только лог событий

## 9. Role Presentation

Role-aware UX copy приведён к человеческой форме:

- `Оператор`
- `Старший смены`
- `Инженер`

Что сделано:

- `engineer_owner` переведён в UI как `Инженер`
- action dialogs и confirm flows локализованы
- сервисные/опасные entry points визуально вынесены из first layer
- в `Справка` и `Система` сервисные действия отделены от operator-first surfaces

## 10. Degraded/Offline UX

Degraded/read-only surfaces приведены к понятному operational language:

- stale state не выглядит как healthy state
- read-only banners говорят `Только просмотр`, а не техническим jargon
- `Система` показывает не только состояние, но и какие действия сейчас ограничены
- shell/data freshness/system fallback surfaces локализованы

Warning/critical surfaces при этом различаются не только цветом, но и явным текстом.

## 11. Before/After Summary

До sprint:

- mixed RU/EN copy на критических operator routes
- `Визиты` и `Гости` продуктово терялись на фоне system-heavy presentation
- `Наливы` и `Инциденты` не были до конца зафиксированы в канонической operator taxonomy
- `Система` и `Справка` читались как технические, а не operational surfaces

После sprint:

- active operator UI читается как единый русскоязычный продукт
- guest/visit workflows подняты выше в `Смена`, `Визиты`, `Гости`, `Краны`
- первый слой быстрее сканируется и сильнее ведёт к действию
- KPI/status taxonomy закреплены в shared models и тестах
- incident noise стал дисциплинированнее
- degraded/role presentation стала понятнее для demo/pilot использования

## 12. Remaining Follow-Up

Позже, вне этого sprint:

- возможен отдельный pass по bundle splitting, если warning `> 500 kB` станет практической проблемой
- можно дополнительно расширить automated smoke на role-specific UI branches
- если backend когда-нибудь даст более богатую operator projection для инцидентов и degraded states, это можно сделать отдельной later phase без нового IA rewrite
