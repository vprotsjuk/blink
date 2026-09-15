# Blink — полный статус, ошибки и план развития

> **Current-state notice (2026-09-14):** This report is a historical status
> record. For execution, use [`BLINK_REMAINING_ROADMAP.md`](BLINK_REMAINING_ROADMAP.md),
> [`BLINK_CURRENT_STATE_CONTRACT.md`](../contracts/BLINK_CURRENT_STATE_CONTRACT.md),
> and [`BLINK_SHORTCUT_TREES_2026-09-14.md`](BLINK_SHORTCUT_TREES_2026-09-14.md).
> The current roadmap corrects the earlier Stage-2 diagnostic wording and
> requires final physical acceptance of clean `Blink`, `Blink DONE`, and
> `Blink Files` before Production cutover.

**Дата:** 14 сентября 2026 года  
**Статус:** one-file Files flow принят; multi-file acceptance, production cutover, cleanup и лампа ещё впереди.

## 1. Цель

Blink должен создавать события на Mac и отправлять их на iPhone через ntfy.
Для личного события с вложением нужны две независимые кнопки: `Done` и
`Files`. `Files` должен открыть вложения именно этого события, показать
настоящие имена файлов, скрыть manifest/`.ready`/transport ID и открыть
выбранный файл в Quick Look.

Mac остаётся источником истины. CREATE/DONE, канонический `Blink Files`,
backup и production mailbox нельзя ломать или менять до отдельного этапа.

## 2. Изначальный план

1. Зафиксировать архитектуру и inventory существующих Shortcuts.
2. Сохранить flat transport package для проверки целостности.
3. Добавить opt-in Files action в ntfy только для личных событий с файлами.
4. Собрать чистые production-кандидаты CREATE/DONE/Files.
5. После каждого изменения Shortcut делать Mac GUI save-touch, ждать iCloud и
   подтверждать полный action tree на iPhone.
6. Пройти физическую acceptance-проверку.
7. Выполнить Acceptance → Production cutover.
8. Провести безопасный inventory/cleanup старых Test/WORK/Diagnostic объектов.
9. Подключить физическую USB RGB-лампу последним отдельным этапом.

## 3. Что сделано

### Код и transport

- Mac `agenda.json` и локальные attachments остаются каноническими.
- В `Blink_Acceptance/ToPhone` создаётся event-specific flat package с
  manifest, `.ready` и attachment bytes.
- Package ID имеет вид `blink-files-v1-<sha256-prefix>`.
- Добавлена производная папка
  `Blink_Acceptance/ToPhoneView/<package-id>/`.
- В неё копируются только вложения под исходными безопасными именами.
  Служебные объекты и transport prefixes туда не попадают.
- View строится атомарно, проверяет unsafe/duplicate basenames и удаляется
  вместе с пакетом при cleanup.
- Flat package сохранён как integrity-слой.

### ntfy

- `Done` и `Files` — независимые `view` actions в порядке `Done`, затем
  `Files`, разделённые штатным `;`.
- `Done` несёт `blink-done-v1|<event-id>`; `Files` —
  `blink-files-v1|<package-id>`.
- URL параметры кодируются percent-encoding (`%20`, не `+`); `clear=true` не
  используется.
- Files action opt-in и не добавляется к Weather/Astronomy/system pushes.
- Контракт и регрессионный тест явно фиксируют раздельность кнопок.

### Проверенный Candidate

Финальное дерево Candidate:

```text
Get file from Shortcuts at path
    Blink_Acceptance/ToPhoneView/<package-id>
Get Contents of Folder
Choose from List
Show Selected Item in Quick Look
```

Физически на iPhone принято:

- зелёная кнопка Files в ntfy нажимается;
- открывается Shortcut и chooser;
- отображается только настоящее имя, например
  `Appointment Schedule (1).pdf`;
- выбор пункта открывает PDF в Quick Look.

Канонический `Blink Files`, backup, WORK и production не менялись.

## 4. Ошибки и причины задержки

### 4.1 Синхронизировалось имя, но не action tree

Плитка Shortcut и её имя появлялись на iPhone раньше полного тела. Поэтому
часть тестов запускала старую WORK-версию, хотя мы считали, что проверяем
новую. Имя не является доказательством синхронизации.

Правило теперь такое:

```text
Изменить Shortcut на Mac
        ↓
Реальный GUI save-touch в Shortcuts
        ↓
Проверить полный tree и marker в iPhone Edit
        ↓
Только потом запускать или отправлять push
```

Добавление/удаление `Stop Shortcut` доказало механизм, но не является
production-процедурой.

### 4.2 База Shortcuts не всегда публиковала изменения

Прямое изменение внутренней Mac-базы не всегда инициировало публикацию в
iCloud. Обычная harmless GUI-правка и сохранение в приложении Shortcuts
заставляли Mac опубликовать новое тело. Поэтому ранние запуски были
версионно неоднозначными.

### 4.3 Папка обрабатывалась как файл

Первый Candidate использовал `Get Contents of File` после получения папки.
На iPhone это давало ошибку, что transport package нельзя открыть.

Правильная цепочка — `Get Contents of Folder`, затем выбор из `Folder
Contents`. После замены chooser и Quick Look заработали.

### 4.4 В chooser попадали служебные файлы

Flat package обязан содержать manifest и `.ready`. Сложная динамическая
фильтрация в длинном WORK Shortcut (`Filter Files`, regex, Count и If) была
ненадёжна на iPhone. Поэтому фильтрация вынесена на Mac: iPhone получает
простую package-scoped view-папку.

### 4.5 Не совпало имя Shortcut в ntfy

Одна кнопка вызывала Candidate `…20260913-A`, а Shortcut временно назывался
`…20260914-B`. iPhone корректно сообщил `Could not find the shortcut`.
Имя было возвращено к точному имени в URL.

### 4.6 Повторяющийся `{"detail":"Bad Request"}`

Это были разрывы/ошибки инструментального соединения Codex, а не ошибка
Shortcuts, ntfy или файла. Они прерывали управление, но не означали сбой
самого телефона или transport-пакета.

## 5. Текущее состояние

Принято:

- one-file Files flow через acceptance Candidate;
- оригинальное имя файла в chooser;
- открытие PDF в Quick Look;
- отдельные `Done` и `Files` buttons в контракте;
- обязательный GUI-touch и iPhone sync gate.

Ожидает выполнения:

- physical multi-file acceptance;
- универсальный dynamic package path для всех будущих событий;
- Acceptance → Production cutover на `Blink`, `Blink DONE`, `Blink Files`;
- финальный cleanup Shortcuts и iCloud transport;
- включение production mailbox;
- подключение лампы.

Production mailbox и `Blink_Production/ToMac` пока выключены/не используются.

## 6. План будущих апгрейдов Shortcuts

### Этап A — multi-file acceptance

Создать acceptance-пакет с двумя или более вложениями и проверить:

- view содержит только оригинальные имена;
- порядок задаётся `__01__`, `__02__` до построения view;
- chooser показывает только эти файлы;
- каждый выбранный файл открывается в Quick Look.

Все preset reminder/blinker значения не нужно проверять физически по одному.
Mapping проверяется программно, а на iPhone достаточно representative-тестов:
preset, custom minute, несколько reminders и multi-file.

### Этап B — production cutover

После multi-file acceptance:

1. зафиксировать финальные деревья и build markers;
2. заменить Acceptance paths на Production paths, если включается mailbox;
3. заменить Candidate URL names на `Blink`, `Blink DONE`, `Blink Files`;
4. выполнить GUI-touch и подтвердить tree на iPhone;
5. выполнить production smoke test;
6. только после этого включить production controls.

### Экран Shortcuts

Пока его не убираем. `shortcuts://run-shortcut` передаёт управление системному
приложению Shortcuts, поэтому промежуточный экран ожидаем. Устранение требует
другого, вероятно публичного или менее приватного транспорта. Текущий экран
приемлем, потому что надёжный приватный путь уже принят.

## 7. Cleanup

Cleanup начинается только после принятого production replacement. Перед ним
нужен финальный inventory в трёх местах:

1. библиотека Shortcuts;
2. iCloud `Blink_Acceptance`, `Blink_Feasibility`, `Blink_Production`;
3. `/Users/vitaliiprotsiuk/Desktop/Blink` и runtime folders.

Для каждого объекта фиксируется `KEEP / DELETE / WHY`. Удаляются только
agent-created diagnostic/candidate объекты после сохранения нужных backup и
принятия replacement. Пользовательские документы, canonical data, source
code и authoritative docs не удаляются.

Желаемый конечный набор:

```text
Blink
Blink DONE
Blink Files
```

## 8. Лампа — последний этап

Лампа уже есть у пользователя, но подключение откладывается до самого конца.
Она не должна усложнять CREATE/DONE/Files и не должна становиться вторым
scheduler, sender или source of truth.

Последовательность:

1. определить точную модель, питание и интерфейс управления;
2. проверить безопасный локальный control path;
3. сделать отдельный adapter без изменения watcher/ntfy ownership;
4. связать лампу только с принятым состоянием Blink/Attention;
5. добавить fail-safe: отсутствие лампы не блокирует Blink;
6. провести hardware smoke test отдельно от production cutover;
7. описать отключение и восстановление.

## 9. Рабочие правила после compact

Перед следующим изменением агент читает этот отчёт, current-state contract,
inventory и roadmap; проверяет `git status`, последние commits и конфликты
документации. После изменения Shortcut обязательны GUI-touch, iPhone tree gate
и только затем физический тест. После каждого этапа обновляются отчёт и
authoritative docs, выполняются `git diff --check` и соответствующие focused/
full tests. Cleanup выполняется только в разрешённых границах.

## 10. Рекомендуемый порядок обсуждения

```text
Обсудить этот отчёт
        ↓
Multi-file acceptance
        ↓
Production cutover
        ↓
Финальный inventory и cleanup
        ↓
Подключение лампы
```

## 11. Актуализация 14 сентября 2026

Документация reconciled после фактической проверки Mac Shortcuts. Единый
план находится в
`docs/superpowers/plans/2026-09-14-blink-production-reconciliation.md`,
а точные текущие деревья и inventory — в
`docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md`.

В библиотеке Mac обнаружено 17 Shortcut-объектов; чистых production-имён
`Blink`, `Blink DONE`, `Blink Files` пока нет. Поэтому переименование и
cleanup отложены до прохождения acceptance всех трёх деревьев.

Проверки после reconciliation:

- focused Python: 92 теста, PASS;
- полный Python suite: 219 тестов, 1 skipped, PASS;
- Swift release build: PASS;
- Swift contract runner: PASS;
- `git diff --check`: PASS.

Это не означает, что физические CREATE/DONE/Files production-тесты уже
пройдены: one-file Files принят, multi-file и финальные canonical trees ещё
являются рабочими этапами roadmap.

## 12. Acceptance boundary: Files Stage2, 14 сентября 2026

Физически подтверждено на iPhone через Shortcuts:

- package-scoped папка
  `Blink_Acceptance/ToPhoneView/blink-files-v1-b7125ae665b167365d197f0bb7785b2c`
  содержит `485 Notice.jpeg` и `Appointment Scheduled (1).pdf`;
- прямой 5-action Shortcut с жёстким путём к этой папке показывает chooser
  `Which one?` с обоими файлами;
- значит, iCloud-файлы, чтение папки и Quick Look сами по себе рабочие.

Отдельно подтверждено поведение вложенного запуска: `Run Shortcut` из
другого Shortcut выполняется (зелёная галочка), но UI дочернего Shortcut
(Show Alert / Quick Look) не возвращается наружу. Поэтому helper/injector не
может служить физическим доказательством отображения chooser; acceptance
Files должен запускаться непосредственно из ntfy.

Для Stage2-кандидатов зафиксирована граница отказа: старое дерево читает
`ToPhone`, затем отбрасывает вложения по имени, построенному из
`PackageID`; для package-scoped `ToPhoneView` такой prefix не совпадает с
реальными basename, и `AttachmentCount` становится 0, после чего Shortcut
тихо останавливается. Наличие `.ready`/`.manifest.json` в этой папке также не
предполагается: package-scoped view содержит только attachment files.

Следующий безопасный шаг — прямой iPhone-тест acceptance Stage2 с тем же
ntfy action и GUI-touch после публикации дерева. Production mailbox,
canonical names и старое рабочее дерево до этого не менять.

В ходе этого прогона тестовое уведомление дошло до ntfy и показало кнопку
`Files` в ленте. Нажатие кнопки внутри открытой ленты не передало управление
в Shortcuts; это не смешивается с ранее подтверждённым live-banner запуском
из шторки уведомлений и требует отдельной проверки именно live banner.
