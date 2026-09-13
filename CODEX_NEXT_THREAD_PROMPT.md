# Blink: Short Prompt for the Next Codex Task

For the complete current-state handoff and the exact request to send to a new
ChatGPT analysis thread, read
`docs/HANDOFF_NEXT_CODEX_2026-09-13.md`.

The authoritative remaining roadmap/checkpoint is
`docs/implementation/BLINK_REMAINING_ROADMAP.md`; Stage 1 manual acceptance
is complete and Stage 2 production attachment viewing is current. Do not
implement Stage 2–7 without a new explicit owner task.

**Current checkpoint:** 2026-09-12. Manual iPhone/iCloud feasibility, Phase 4B
real iPhone DONE-action acceptance, Phase 5 CREATE acceptance, and Phase 7 fast agenda refresh are complete; Phase 1 shared agenda locking, Phase 2A importer core, Phase 2B
canonical transactions/recovery, Phase 3's opt-in watcher worker, and Phase 4A
Mac ntfy DONE action support are implemented. Production mailbox integration
and DONE action delivery remain disabled by default after controlled acceptance. The verified private Apple
Shortcuts container is
`~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents` with
`Blink_Feasibility/ToMac`, `Blink_Acceptance/ToMac`, and `ToPhone`. Four test Shortcuts were used:
`Blink Test`, `Blink Files`, `Blink DONE Test`, and `Blink Create Test`.

Confirmed manual PASS: iPhone → Mac file transport, Mac → iPhone `ToPhone` +
Quick Look, external Shortcut URL input, real ntfy DONE → `.done.json` +
`.ready`, CREATE_EVENT direct launch, image and PDF attachments, repeated Viber
PDF after `Always Allow`, direct-launch regression after the attachment branch
fix, and Phase 5 CREATE acceptance with explicit-offset dates, arbitrary integer
reminder/blinker values, empty Description, and phone-side validation. Real
Apple Shortcuts has no native Generate UUID action, so the
production phone transport ID is `<yyyyMMddHHmmss>-<9-digit-random>`; UUIDv4
remains accepted for backward compatibility. The combined value is transport
identity only, never an event ID or event start time. The mailbox is transport
only; Mac/Blink and local JSON remain the source of truth.

The DONE acknowledgement decision is FINAL: the originating notification
remains unchanged. After a newly applied remote DONE, Mac sends one separate
short confirmation without an action button or `clear=true`; repeats, no-ops,
stale, malformed, pending, and failed commands are silent. Production
transport IDs use
`<yyyyMMddHHmmss>-<9-digit-random>` (UUIDv4 remains accepted for compatibility)
and are never event IDs. Phase 2B must reuse existing Blink Done/Create
logic, be idempotent, treat duplicate/stale DONE as NO-OP, survive malformed
packages, and delete transport files only after successful apply.

Implementation checkpoint: Phase 1 shared agenda locking is complete in commit
`98753a8`; Phase 2A is in `421963d`, Phase 2B in `aa50f96`, and Phase 3 in
`df50af7` plus diagnostics follow-up `47a381b`; Phase 4A is `a8c682b`; Phase
4B acceptance is recorded in `49eaf30`. Phase 5 manual acceptance artifacts
are archived outside the now-empty `Blink_Acceptance/ToMac` under
`Blink_Acceptance/Archive/Phase5-20260912211629`. Phase 6 controlled CREATE
and DONE acceptance passed. Early Done is implemented for Today/Upcoming and
future-start events move directly to History with preserved `start` and actual
`done_at`. Remote DONE sends one short post-apply confirmation without an
action button or `clear=true`; duplicate/no-op/stale/malformed/pending/failed
commands remain silent and notification failure does not roll back completion.
Production iCloud and production Shortcuts remain unchanged; DONE action
delivery remains disabled by default. See
`docs/implementation/BLINK_MAILBOX_IMPLEMENTATION_REPORT.md`.

Stage 2 Mac-side attachment viewing is implemented behind the controlled
`BLINK_NTFY_FILES_ACTION_ENABLED=1` plus explicit `BLINK_TO_PHONE_ROOT`
settings. The Mac snapshots canonical event attachments into deterministic flat
ToPhone packages (`blink-files-v1-<sha256-prefix>`), refreshes queued/delayed
packages during reconciliation, and freezes delivered snapshots until bounded
cleanup. The canonical ntfy action is `Files` with input
`blink-files-v1|<package-id>` and percent-encoded `shortcuts://` query values;
no `clear=true` is added. The existing `Blink Files` Shortcut must read only
the matching package, open one file directly, and chooser-select multiple
files. Physical iPhone acceptance is the remaining Stage 2 gate; production
mailbox and `Blink_Production/ToMac` remain disabled/unused. The current
`Blink Files Stage2 WORK` candidate completes on iPhone with a checkmark but
shows no PDF preview; compare it with the old `Blink Files` tree and diagnose
the actual Quick Look/file-type binding before any further edit.

Phase 6A/6B CREATE acceptance has since passed against `Blink_Acceptance/ToMac`;
iCloud `dataless` package bytes are treated as `PENDING_SYNC` and retried. The
past-start event was observed in Today/Active with Attention enabled. Phase 6
DONE acceptance has now passed: after the accepted ntfy action was tapped,
package `20260912221340-109486748.done.json` + `.ready` arrived in
`Blink_Acceptance/ToMac`, was applied, and the event became `done=true`.
Historical feasibility files remain untouched. The controlled mailbox is OFF
and production remains unused.

Current verification: `.venv/bin/python -m unittest -q` passes the current suite;
Python compile, plist lint, `./status_watcher.command`, Swift test runner, and
Swift release build passed. The alternate command with `-s tests` is not
runnable because this checkout has no importable `tests/` directory; root-level
`test_*.py` modules are covered by the default command.

Работаем в существующем проекте `/Users/vitaliiprotsiuk/Desktop/Blink`. Сначала прочитай:

1. `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
2. `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
3. `docs/HANDOFF.md`
4. `docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md`
5. `docs/implementation/BLINK_REMAINING_ROADMAP.md`

Это локальное macOS-приложение Blink. Сохраняй границу:

```text
SwiftUI GUI -> local JSON -> watcher.py -> ntfy + USB blinker
```

SwiftUI только читает/редактирует JSON и показывает состояние. `watcher.py` единственный production sender, scheduler и владелец аппаратного blinker. Не добавляй второй sender, scheduler, БД, cloud backend или смешивание блоков.

Перед кодом:

- проверь фактический source/runtime, а не только screenshots;
- запиши план и выполни его по шагам;
- проследи зависимости любого изменяемого поля через модели, JSON, watcher, notification formatter, UI и tests;
- при противоречии с контрактом остановись и уточни;
- не называй работу исправленной без тестов и ручной проверки для OS/UI поведения.

После изменений:

- обнови `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`, `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md` и `docs/HANDOFF.md`;
- если задача меняет или уточняет iPhone/iCloud mailbox contract,
  DONE/CREATE package format, `.ready` semantics, remote command behavior или
  ntfy acknowledgement behavior, обязательно обнови также
  `docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md`;
- если после принятого design меняется текущая точка продолжения проекта,
  обнови также `CODEX_NEXT_THREAD_PROMPT.md`;
- запусти релевантные Python/Swift tests, compile/build и `./status_watcher.command`;
- если менялась SwiftUI-программа, пересобери release executable, замени `Blink.app/Contents/MacOS/Blink`, закрой Blink и запусти его снова;
- в финале перечисли измененные файлы, проверки, результаты и оставшиеся риски.

Продолжай с новой задачей пользователя, сохраняя текущие правила: английский системный UI, пользовательские title/description могут быть на любом языке, 24-hour time, независимые Weather/Astronomy/Location/Personal Event/Attention блоки, единый формат Save -> Saved, и физически корректная классификация Today/Upcoming/History. Today создаёт событие круглой синей кнопкой `+` слева от заголовка; все вкладки имеют мягкую реакцию на наведение.

Вопросы, которые нельзя потерять после компакта: единая кнопка `Paste` принимает обычные file URLs из буфера (PDF, Excel, изображения и другие файлы), а при отсутствии file URLs принимает image data и делает timestamped JPEG; папки не копируются рекурсивно. Для Today/Upcoming row context-menu `Paste` и `Add Files` — немедленные действия над уже сохранённым событием: редактор не открывается и Save не нужен. Все выбранные файлы валидируются и прикрепляются атомарно; при ошибке batch откатывается целиком. В редакторе Add Files/Paste/drop остаются draft-действиями до Save/Cancel. Drag-and-drop разрешён только внутри attachment panel редактора и использует тот же staging pipeline; drop на строки не реализован, а History заморожен.

Активные/Upcoming события всегда могут открыть или создать пустую папку вложений; History только открывает существующую. Каждый occurrence владеет `event_data/attachments/<event-id>/`; `series_id` не является owner. Поиск включает имена и расширения локальных вложений. JSON и папки остаются источником истины; SQLite допустим позже только как восстанавливаемый индекс при доказанной необходимости масштабирования.

Исторические планы помечены `HISTORICAL / SUPERSEDED` и никогда не переопределяют running code или этот current contract.

Критический инвариант загрузки: `agenda.json` — единственный источник истины,
но ошибка чтения не означает `events = []`. Loaded empty и Error/Stale различаются;
Today/Upcoming/History/Search сохраняют last-good snapshot, а Health показывает
статус, count, source path, last successful load и last error. Remote queue signature
обязательно учитывает `attachments.has_files`, чтобы переходы 0→1 и 1→0 обновляли
paperclip в запланированном push без дублей при изменении только count.

Selected Day уже реализуется поверх общего snapshot: double-click не-сегодняшнего дня
в календаре редактора временно меняет первый таб на `MMM d`, показывает полную дату и
weekday, все события этой локальной даты (unfinished/Done/Off) с сортировкой local
start + event ID, `Exit` и `+ New Event` с предзаполненной датой. Поиск очищается и
после входа ограничен выбранным днём; переход по другим табам выбор сохраняет,
double-click сегодня возвращает Today, relaunch его не сохраняет. Frozen rows
сохраняют History policy. Dirty editor нельзя потерять при навигации; reload error
сохраняет last-good snapshot и не показывает ложный пустой день.
