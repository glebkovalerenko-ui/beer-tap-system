# Alert Policy (Operator)

Дата версии: 2026-03-24

## Цель
Этот документ фиксирует единые правила открытия и сопровождения инцидентов в рантайме beer-tap-system, чтобы снизить шум алертов и ускорить реакцию операторов.

## Общие правила
- **Incident key**: `tap_id + category` (одновременно открыт не более 1 инцидента на категорию и кран).
- **Aggregation window**: одинаковые события в окне агрегации увеличивают счётчики текущего инцидента, а не создают новый.
- **Debounce**: инцидент открывается только если условие держится дольше debounce-порога.
- **Auto-close**: закрытие выполняется автоматически после устойчивого восстановления.
- **Anti-noise**: ограничение частоты повторных оповещений и переоткрытий.
- **Escalation**: если инцидент не закрыт в заданное время или превышен лимит повторов, он эскалируется на следующую линию.

## Политика по категориям

| Категория | Условие открытия | Debounce / aggregation window | Приоритет | Авто-закрытие | Эскалация | Max repeat (anti-noise) |
|---|---|---|---|---|---|---|
| **flow без карты** | Есть `pour_started`/`flow_started`, но нет валидной `card_bound` сессии | Debounce: **5 сек** непрерывного flow без карты. Aggregation: **30 сек** | P1 | Закрыть после `flow_stopped` и 10 сек без новых flow-событий | L1 сразу; L2 если > **2 мин** открыт; L3 если > **3** инцидента за 1 час на tap | Не более **2** reopen за **15 мин**, затем mute на 30 мин и только summary |
| **reader offline** | `reader_heartbeat_missing` или `reader_disconnected` | Debounce: **15 сек** отсутствия heartbeat. Aggregation: **60 сек** | P1 | Закрыть после **3** подряд heartbeat с интервалом 5 сек (≈15 сек стабильности) | L1 сразу; L2 если > **5 мин**; L3 если > **3** раз за смену | Не более **3** reopen за **30 мин**, далее suppress до ручного ack |
| **stuck sync** | Очередь синка не уменьшается и oldest job старше порога; повторы retry исчерпаны | Debounce: **120 сек** backlog без прогресса. Aggregation: **300 сек** | P2 | Закрыть, если queue depth = 0 или oldest job < 60 сек в течение 2 мин | L1 при открытии; L2 если > **15 мин** или `retry_count >= 5`; L3 если > **60 мин** | Не более **2** reopen за **60 мин**, затем hourly digest |
| **no keg** | Сенсор/учёт: `keg_empty=true` или расход при нулевом остатке > порога | Debounce: **3 сек**. Aggregation: **20 сек** | P1 | Закрыть после `keg_replaced` и 30 сек стабильного нормального flow | L1 сразу; L2 если не решено за **10 мин** | Не более **2** reopen за **20 мин**, далее mute 20 мин |
| **high foam / unstable flow** | Колебания расхода > допустимого профиля | Debounce: 20 сек. Aggregation: 120 сек | P3 | Закрыть после 60 сек стабильного профиля | L1; L2 если > 30 мин | Не более 1 reopen за 30 мин |
| **tap offline** | Нет heartbeat от контроллера крана | Debounce: 30 сек. Aggregation: 120 сек | P1 | Закрыть после 2 успешных heartbeat | L1 сразу; L2 если > 5 мин; L3 если > 20 мин | Не более 2 reopen за 30 мин |

## Фиксированные thresholds для критичных категорий

### 1) flow без карты
- Время до открытия: **5 сек** непрерывного потока.
- Допустимые повторы (reopen): **2** за 15 минут.
- Retry count для авто-действий (например, soft-stop команды): **3** попытки с шагом 2 сек; затем эскалация L2.

### 2) reader offline
- Время до открытия: **15 сек** без heartbeat.
- Допустимые повторы (reopen): **3** за 30 минут.
- Retry count восстановления соединения: **5** попыток (`1s, 2s, 5s, 10s, 15s`), затем тикет в L2.

### 3) stuck sync
- Время до открытия: **120 сек** без прогресса очереди.
- Допустимые повторы (reopen): **2** за 60 минут.
- Retry count на job: **5**; при `retry_count >= 5` и возрасте job > 300 сек инцидент повышается до P1.

### 4) no keg
- Время до открытия: **3 сек** подтверждённого пустого кега.
- Допустимые повторы (reopen): **2** за 20 минут.
- Retry count проверки датчика/перечтения: **3** попытки каждые 2 сек перед фиксацией статуса `keg_empty`.

## Примеры: event stream → incident outcome

### Сценарий 1: flow без карты (открытие и авто-закрытие)
```
12:00:00 flow_started tap=7
12:00:01 flow_rate=0.42
12:00:03 flow_rate=0.40
12:00:05 no card_bound detected (5s reached)
12:00:05 INCIDENT OPEN: flow_without_card P1
12:00:08 flow_stopped
12:00:18 no flow events for 10s
12:00:18 INCIDENT AUTO-CLOSE
```
Outcome: открыт P1, закрыт автоматически после остановки пролива и окна стабильности.

### Сценарий 2: reader offline (флаппинг, anti-noise)
```
13:10:00 last_heartbeat
13:10:16 heartbeat_missing(16s)
13:10:16 INCIDENT OPEN: reader_offline P1
13:10:40 heartbeat restored x3
13:10:55 INCIDENT AUTO-CLOSE
13:20:10 heartbeat_missing снова
13:20:26 INCIDENT REOPEN #2
13:32:00 INCIDENT REOPEN #4 -> suppressed (anti-noise)
```
Outcome: после превышения лимита повторов включён suppress, оператор получает summary вместо потока алертов.

### Сценарий 3: stuck sync (эскалация по retry)
```
14:00:00 sync_queue_depth=48 oldest_job=130s
14:00:30 retry_count job#A = 4
14:01:10 oldest_job=250s, queue no progress
14:02:00 INCIDENT OPEN: stuck_sync P2
14:04:20 retry_count job#A = 5
14:04:20 INCIDENT ESCALATE L2 (retry threshold)
```
Outcome: инцидент открылся после 120 сек без прогресса, затем эскалирован из-за превышения retry-порога.

### Сценарий 4: no keg (подтверждение и восстановление)
```
15:22:10 keg_sensor=empty
15:22:11 verify_read #1 empty
15:22:13 verify_read #2 empty
15:22:15 verify_read #3 empty
15:22:15 INCIDENT OPEN: no_keg P1
15:28:40 keg_replaced
15:29:10 stable normal flow 30s
15:29:10 INCIDENT AUTO-CLOSE
```
Outcome: открытие только после 3 подтверждений, затем авто-закрытие после замены кега и стабильности.

### Сценарий 5: flow без карты + эскалация
```
18:45:00 flow_started tap=3 (no card)
18:45:05 INCIDENT OPEN: flow_without_card P1
18:45:07 soft-stop retry #1 failed
18:45:09 soft-stop retry #2 failed
18:45:11 soft-stop retry #3 failed
18:45:11 INCIDENT ESCALATE L2
18:47:20 operator manual stop
18:47:30 INCIDENT AUTO-CLOSE
```
Outcome: после 3 неуспешных авто-остановок включается эскалация L2.

## Правила ревизии
- Пересмотр threshold-ов: не реже 1 раза в 2 недели на основе фактической статистики false positive / MTTR.
- Любое изменение порогов должно сопровождаться обновлением этого документа и changelog релиза.
