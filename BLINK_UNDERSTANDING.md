# Blink — что я понял о программе

**Снимок понимания:** 14 сентября 2026 года  
**Рабочая папка:** `/Users/vitaliiprotsiuk/Desktop/Blink`

Этот документ описывает моё понимание Blink после чтения исходного кода,
тестов, README и актуальных контрактов. В проекте есть исторические отчёты,
которые описывают уже пройденные этапы или старые диагностики. Для текущего
состояния приоритет имеют код, `README.md`,
`docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`,
`docs/implementation/BLINK_REMAINING_ROADMAP.md` и
`docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md`.

## 1. Коротко

Blink — это локальный однопользовательский планировщик событий для macOS.
Он хранит события и настройки в JSON внутри папки проекта, показывает их в
нативном SwiftUI-интерфейсе, а отдельный Python-процесс `watcher.py` следит за
временем и отправляет уведомления через ntfy на iPhone. Тот же watcher владеет
состоянием аппаратного blinker/lamp, когда аппаратный этап будет подключён.

Главная идея проекта: **Mac — источник истины; SwiftUI только редактирует и
показывает данные; watcher — единственный планировщик и отправитель.**

```text
SwiftUI Blink.app
        │
        ├── agenda.json, location.json, weather/*, astronomy/*
        └── event_data/attachments/<event-id>/
                         │
                         ▼
                    watcher.py
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        ntfy → iPhone   Weather   Astronomy
              │
              └── Done / Files через iPhone Shortcuts
```

В проекте намеренно нет SQLite, облачной базы, AI-памяти, второго sender’а или
второго scheduler’а.

## 2. Из чего состоит программа

### SwiftUI-приложение

Исходный код находится в `app/BlinkSwiftUI/`. Это native macOS-приложение с
двумя исполняемыми целями: основная GUI и отдельный
`BlinkSwiftUITestRunner`. GUI:

- читает `agenda.json` и производные JSON-файлы;
- показывает вкладки Today, Upcoming, History, Astronomy, Weather, Location и
  Health;
- создаёт, редактирует, отключает, завершает и удаляет личные события;
- поддерживает календарь, 24-часовое время, повторения, несколько reminders и
  отдельный blinker offset;
- работает с локальными вложениями через Finder, Paste и drag-and-drop внутри
  редактора;
- отображает поиск по заголовку, описанию, дате, статусу и именам файлов;
- показывает внимание через цвет строки/вкладки, Dock и menu bar;
- автоматически обновляет данные после внешней атомарной замены `agenda.json`,
  а также сохраняет 30-секундный polling как fallback.

SwiftUI не отправляет ntfy и не управляет расписанием push-уведомлений.

### Python watcher

`watcher.py` — долгоживущий процесс, запускаемый через LaunchAgent. В каждом
цикле он:

1. записывает heartbeat;
2. загружает и проверяет location, astronomy, weather и события;
3. при необходимости обновляет локальное astronomy-расписание;
4. обрабатывает погодный briefing;
5. строит или сверяет rolling remote queue для личных и astronomy-событий;
6. отправляет due reminders через ntfy;
7. обновляет dedupe/state-файлы;
8. поддерживает состояние blinker до завершения события;
9. опционально сканирует входящие iPhone-пакеты в отдельном mailbox worker.

Ошибки отдельных подсистем не должны останавливать watcher. Для сетевых
ошибок, временно недоступных iCloud-файлов и ошибок отправки предусмотрены
retry/pending-состояния.

### Доменные модули

| Модуль | Ответственность |
|---|---|
| `app/agenda_store.py` | JSON событий, блокировка, атомарная запись, lifecycle, recurrence |
| `app/attachment_store.py` | локальные файлы, draft/finalize, manifest, Trash и миграции |
| `app/event_timing.py` | разбор timezone-aware времени и effective start |
| `app/mailbox_importer.py` | безопасный разбор CREATE/DONE-пакетов и транзакционное применение |
| `app/notification_format.py` | текст уведомлений, ntfy headers и actions |
| `app/ntfy_schedule.py` | rolling 24-hour remote queue и reconciliation |
| `app/to_phone_store.py` | детерминированные пакеты вложений для просмотра на iPhone |
| `app/weather_store.py` | Open-Meteo, нормализация cache, briefing и retry |
| `app/location_store.py` | координаты, IANA timezone, геокодирование и validation |
| `astronomy/generate_astronomy.py` | локальные Sun/Moon расчёты и 24-месячное расписание |
| `app/personal_briefing.py` | pure-логика optional Today briefing, пока отключённая в продукте |
| `app/watcher_lifecycle.py` | heartbeat, runtime status и sleep-gap диагностика |

## 3. События и их жизненный цикл

Событие хранится в `agenda.json`. Минимально важные поля: `id`, `title`,
`start`, `reminders_minutes_before`, `enabled`; для нового GUI-события также
сохраняются `requires_done`, `done`, `done_at`, `attention_level` и metadata
вложений.

`start` обязан содержать явный UTC offset, например
`2026-09-22T06:59:00-07:00`. Это нужно, чтобы Mac, watcher, повторения и
переходы DST одинаково понимали момент события.

Смысл состояний:

```text
Upcoming → Active → Done → History
```

- **Upcoming** — активное будущее событие.
- **Active** — enabled, unfinished и уже наступившее событие; оно может
  привлекать внимание бесконечно долго, пока его не завершат.
- **Done** — завершённое событие с `done_at`; его исходный `start` сохраняется.
- **History** — завершённые, отключённые или устаревшие записи, доступные для
  просмотра.

`Done` и `Off` — разные действия. `Off` прекращает eligibility для напоминаний
и attention, но не удаляет запись. Историческое событие заморожено: его нельзя
редактировать, но можно продублировать как новое. Удаление — отдельное
подтверждаемое действие.

Повторения поддерживают два основных режима:

- `weekly_fixed` — следующий заданный weekday и time;
- `after_done_days` — следующее событие через заданное число дней после Done.

Следующий occurrence получает новый event ID и пустую папку вложений.
Создание successor защищено от повторного добавления.

## 4. Reminders, внимание и blinker

Reminders — это независимый список неотрицательных целых минут до события.
Поддерживаются стандартные значения `1440, 720, 300, 60, 30, 10, 5, 0` и
произвольные целые значения. `0` означает «At time».

Blinker — отдельный единственный offset, а не один из reminder rows. Он также
выражается в целых минутах. Его изменение не меняет reminders и наоборот.

Ограничение lead-time применяется к новым и дублированным событиям. При
редактировании существующего незамороженного события старое или новое
значение reminder/blinker остаётся доступным даже после того, как его lead
time уже прошёл. Это позволяет исправить timing с сохранением того же event
ID. History по-прежнему заморожен.

У события есть три уровня важности:

- green — обычное;
- yellow — важное;
- red — критическое.

Attention начинается в `start - blinker_minutes_before`, а если отдельный
offset не выбран — в момент события. После Done внимание и blinker
останавливаются. GUI отражает общий максимальный уровень внимания в строках,
на вкладке Today, в menu bar и Dock. Это визуальное состояние приложения; его
не следует путать с отправкой reminders.

Watcher предотвращает повторы по комбинации события, occurrence и reminder
offset. Для отправки с задержкой используется rolling queue примерно на 24
часа; уже поставленная в удалённую очередь запись не отправляется вторично
локальным direct-send путём.

## 5. Локальные вложения

Байты файлов живут только внутри проекта:

```text
event_data/
  attachments/<event-id>/   сохранённые файлы события
  drafts/<draft-id>/        временные файлы открытого редактора
```

В JSON хранится только manifest: владелец, количество и наличие файлов. Пути,
байты и содержимое файлов в `agenda.json` не записываются.

Поведение такое:

- новый/редактируемый event сначала получает draft-папку;
- Finder, Paste и drop в attachment panel добавляют файлы в draft;
- Save финализирует их в папку event ID и обновляет manifest;
- Cancel/Escape удаляет только draft и не трогает уже сохранённые файлы;
- добавление из контекстного меню строки может завершиться сразу, без открытия
  редактора;
- файлы в Finder можно положить напрямую в папку события, после чего GUI при
  reload сверит manifest с фактическим содержимым;
- скрытые файлы, symlink и вложенные папки не включаются;
- при удалении события его Blink-owned папка перемещается в macOS Trash.

Файлы не пересылаются в теле ntfy. В обычном личном уведомлении показывается
только `📎` и количество/наличие вложений.

### Просмотр вложений на iPhone

Для `Files` Mac строит производный детерминированный пакет:

```text
<package-id>.manifest.json
<package-id>__01__<safe-name>
<package-id>__02__<safe-name>
<package-id>.ready
```

Затем создаётся package-scoped `ToPhoneView/<package-id>/`, где лежат только
безопасные исходные имена файлов. Manifest, `.ready`, transport ID и чужие
пакеты на iPhone не показываются.

Кнопки `Done` и `Files` независимы:

- `Done` передаёт EventID через `blink-done-v1|<event-id>`;
- `Files` передаёт PackageID через `blink-files-v1|<package-id>`.

Подтверждён физический Acceptance one-file путь: ntfy → Shortcut → chooser с
оригинальным именем → Quick Look PDF. Multi-file acceptance и полный переход к
чистым production-деревьям ещё не завершены.

## 6. iPhone → Mac обмен

iPhone Shortcuts — это transport adapters, а не вторая база событий. CREATE и
DONE записывают flat-пакеты в iCloud-папку `ToMac`, где Mac может их обработать.
`.ready` пишется последним и означает, что пакет собран.

CREATE поддерживает прямой запуск и Share Sheet с максимум одним вложением.
Mac сам создаёт окончательный `event-<UUID>` и сохраняет событие под общим
`agenda.lock`.

DONE содержит только `event_id`. Importer:

- проверяет имя, структуру, timestamps, reminders и безопасные basenames;
- различает malformed package и `PENDING_SYNC`, когда iCloud ещё не скачал
  байты;
- применяет изменение транзакционно и атомарно;
- ведёт journal и бессрочный processed ledger для защиты от replay;
- удаляет ровно обработанный пакет только после успешного commit;
- для нового remote DONE может отправить одну короткую confirmation push.

Mailbox worker встроен в существующий watcher и отключён по умолчанию. Его
нельзя включать только потому, что iCloud-папка существует: нужны оба явных
параметра `BLINK_MAILBOX_ENABLED` и `BLINK_MAILBOX_ROOT`.

## 7. Weather

Weather использует Open-Meteo только для geocoding и прогноза. Нормализованный
cache сохраняется локально в `weather/weather_cache.json`.

В briefing могут входить:

- температура;
- влажность за текущую локальную дату и значение «сейчас»;
- дождь и вероятность осадков;
- снег;
- ветер и пороговые предупреждения.

Weather не помещается в remote 24-hour queue. В момент наступления локального
времени briefing watcher сначала запрашивает свежий прогноз, затем отправляет
его напрямую. Ошибка fetch оставляет состояние недоставленным; повторная
попытка разрешена не чаще чем примерно раз в 15 минут.

## 8. Astronomy

Astronomy считает данные локально с помощью Skyfield, NumPy и JPL ephemeris
`de440s.bsp`. Используются координаты и IANA timezone из единого location
tuple.

Генерируется rolling schedule примерно на 24 месяца. Для каждого дня могут
быть:

- civil twilight end, solar noon, sunrise, sunset;
- длина дня и ночи;
- moonrise/moonset;
- фаза и illumination;
- waxing/waning trend;
- Moon status at sunset;
- точные New Moon и Full Moon и расстояние до следующего события.

Если событие не происходит в конкретной географической точке, записывается
явное no-event состояние, а не выдумывается время.

Индивидуальные Sun/Moon push отправляются в момент астрономического события.
Опциональный Astronomy briefing имеет собственное время и не является
вторым scheduler’ом. Eclipse-события намеренно исключены из активного
продукта, UI, конфигурации и расписания.

## 9. Location и timezone

`location.json` — корень зависимостей Weather и Astronomy. В нём хранятся
display name, latitude, longitude, IANA timezone и источник координат.

Есть два режима:

- city search через Open-Meteo, где имя, координаты и timezone выбираются одной
  связкой;
- custom coordinates, где пользователь вводит координаты и явно выбирает
  timezone.

Сохранение проверяет диапазоны координат, существование IANA timezone и
соответствие timezone координатам. При изменении location производные weather
cache и astronomy schedule инвалидируются, а watcher перестраивает astronomy
перед использованием уведомлений.

## 10. Надёжность и эксплуатация

Записи JSON делаются через временный файл, `fsync` и `replace`. GUI и Python
используют общий POSIX `flock` через `agenda.lock`, поэтому конкурентная запись
не должна разрушать `agenda.json`.

GUI различает «пустой корректный agenda» и ошибку чтения. При временной ошибке
он удерживает последний хороший snapshot и показывает диагностическое
сообщение, а не ложный пустой список.

Watcher и Blink.app запускаются отдельными LaunchAgents при входе в macOS.
Watcher использует проектный `.venv/bin/python`. `status_watcher.command`
показывает heartbeat, PID и состояние LaunchAgent.

Для работы нужны:

- активный Mac и запущенный watcher;
- сеть для ntfy, geocoding и Weather;
- доступность iCloud/Shortcuts для mailbox-обмена;
- разрешения уведомлений на iPhone.

## 11. Что реально подтверждено в текущей папке

Локальный runtime-снимок на момент изучения:

- в `agenda.json` было 17 личных событий;
- 10 отмечены Done, 14 включены;
- 2 события имели локальные вложения;
- активная локация — Sunnyvale, California, с timezone
  `America/Los_Angeles`;
- astronomy schedule имел статус `fresh`, 732 дневные записи и горизонт до
  сентября 2028 года;
- watcher имел свежий heartbeat и состояние `running`;
- rolling state содержал 8 запланированных и 60 доставленных записей.

Эти числа — наблюдение за текущими локальными данными, а не постоянный
контракт: они могут измениться после следующего действия пользователя.

Результат проверок кода:

- `.venv/bin/python -m unittest -q` — 225 тестов, `OK`;
- `swift run -c release BlinkSwiftUITestRunner` — все Swift contract tests
  прошли;
- `swift build -c release` — release build прошёл;
- watcher status — `running`.

## 12. Что пока не завершено

Главный незавершённый продуктовый участок — не Python-ядро, а финальная
связка с iPhone Shortcuts:

1. завершить multi-file Acceptance для Files;
2. собрать чистые кандидаты `Blink`, `Blink DONE`, `Blink Files`;
3. после каждого изменения выполнить реальный Save-touch в Mac Shortcuts GUI,
   дождаться iCloud и проверить полный action tree в iPhone Editor;
4. явно перевести пути `Blink_Acceptance/*` в `Blink_Production/*` и провести
   production smoke test;
5. только после этого удалить диагностические и старые candidate-объекты.

Имя Shortcut само по себе не доказывает синхронизацию тела: это уже было
проверено на практике. Нужна проверка полного дерева и build marker.

Есть также WIP-блок `app/personal_briefing.py`: backend-логика optional Today
Morning Briefing и её watcher-интеграция уже существуют и покрыты focused
тестами, но постоянного SwiftUI-переключателя/редактора времени и финального
acceptance пока нет. Поэтому feature остаётся disabled-by-default.

USB RGB-лампа — самый последний этап. Она должна подключаться отдельным
fail-safe adapter’ом к уже существующему состоянию Blink, не становясь вторым
sender’ом, scheduler’ом или источником истины.

## 13. Итоговая ментальная модель

Я понимаю Blink как локальный «мозг» напоминаний:

- SwiftUI — окно управления и просмотра;
- JSON и папки — каноническое состояние;
- watcher — единственный исполнитель времени и доставки;
- ntfy — канал уведомлений;
- Shortcuts — ограниченный транспорт между iPhone и Mac;
- Weather/Astronomy — производные данные от Location;
- attention/blinker — реакция на незавершённые события;
- History — неизменяемый журнал завершённых записей.

Поэтому безопасное изменение Blink должно проходить через полный путь данных:
модель → JSON/файлы → watcher → формат ntfy/queue → GUI или iPhone-поведение →
тесты. Нельзя добавлять параллельный scheduler, скрытую базу или менять
production Shortcuts только по имени, не проверив их реальное тело.
