# TAP_DISPLAY_ADMIN_APP_MVP

## 1. Scope of this phase

На этом этапе реализован минимально достаточный операторский workflow для управления контентом Tap Display из Admin App без ручных вызовов backend API.

Сделано:

- завершено редактирование display-полей напитка в `BeverageManager`
- добавлен UI настроек `tap_display_configs` в карточках кранов
- добавлен reusable media picker/upload для фоновых изображений и логотипов
- подтвержден end-to-end flow `Admin App -> backend APIs -> display snapshot`

Не делались новые фундаментальные системы, отдельная CMS, новый runtime или дополнительные display states.

## 2. Beverage display editing

Редактирование напитка доступно в разделе справочника напитков на экране управления кранами и кегами.

Оператор может:

- выбрать существующий напиток и отредактировать его
- создать новый напиток и сразу заполнить display-поля
- задать название для гостя
- задать бренд на экране
- заполнить короткое описание
- выбрать акцентный цвет
- выбрать тему текста
- выбрать режим показа цены по умолчанию
- назначить фон и логотип через media picker

Форма разделена на две части:

- карточка напитка
- контент Tap Display

Это помогает не смешивать служебные поля напитка с тем, что увидит гость на экране.

## 3. Tap display settings

Для каждого крана в `TapCard` добавлена отдельная точка входа `Экран`. Она открывает модальное окно настроек Tap Display и не мешает существующему workflow назначения/снятия кеги.

Оператор может настроить:

- включен ли Tap Display для крана
- fallback title
- fallback subtitle
- maintenance title
- maintenance subtitle
- override accent color
- override background asset
- show price mode override

В модальном окне также показывается краткий контекст:

- статус крана
- назначенный напиток
- эффективный режим цены
- эффективный акцент
- источник фонового изображения

Это даёт минимальную visibility без отдельного preview simulator.

## 4. Media workflow

Media workflow реализован через один reusable компонент media picker, который используется и в напитках, и в настройках крана.

Сценарий оператора:

1. открыть поле фона или логотипа
2. загрузить новый файл или выбрать уже загруженный
3. увидеть превью и базовую информацию о файле
4. сохранить форму напитка или крана

Поддержано:

- upload нового asset
- список уже загруженных asset по типу
- повторное использование asset
- очистка выбранного asset
- authenticated preview без раскрытия broad backend credentials в URL

Для превью в Admin App используется авторизованная загрузка blob и object URL. Отдельная медиатека или продуктовая media library не добавлялись.

## 5. What is intentionally deferred

Сознательно отложено:

- per-keg overrides
- отдельный guest-facing/internal split для названия напитка beyond MVP
- touch UI на Tap Display
- video backgrounds
- advanced preview simulator
- fleet management
- новые display states
- idle instruction editor в Admin App
- отдельный продуктовый media library UI
- cleanup, не связанный с этим workflow

## 6. Verification

Проверка выполнялась на уровне UI и backend contracts.

Прогнаны:

- `cd admin-app && npm run build`
- `cd admin-app/src-tauri && cargo check`
- `python -m pytest backend/tests/test_tap_display_api.py -q`
- `python scripts/encoding_guard.py --all`

Добавлен API-level e2e тест, который проверяет:

- upload background/logo assets
- update beverage display fields
- update tap display config
- assignment beverage -> keg -> tap
- формирование display snapshot с правильным precedence

Проверенный precedence:

- tap override для background и accent выигрывает у beverage default
- beverage logo попадает в snapshot без ручных правок
- tap show price mode override выигрывает у beverage price display default

## 7. Final verdict

После этой фазы Admin App уже даёт реальный MVP workflow для оператора:

- редактирование display-контента напитка
- настройка tap-level display behavior
- загрузка и повторный выбор изображений

Этого достаточно, чтобы переходить к следующему этапу Tap Display MVP без ручного ковыряния backend/API, если следующий этап не требует расширения текущего scope за пределы принятых foundation contracts.
