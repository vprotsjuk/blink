# Prompt for a new Codex thread — Blink continuation

Работаем с существующим проектом Blink:
`/Users/vitaliiprotsiuk/Desktop/Blink`

## Главная задача нового треда

Продолжить работу без потери контекста и без восстановления устаревших функций.
Сначала прочитай текущие документы и проверь состояние Git. Не начинай с кода.
Текущий незавершённый workstream — отдельный feasibility/robustness spike для
будущего обмена Blink ↔ iPhone через private iCloud Drive. Это пока не production
feature.

## Источники истины

Сначала прочитать:

1. `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
2. `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
3. `docs/HANDOFF.md`
4. `docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md`

Текущие contract/full description/HANDOFF authoritative. Старые планы и дизайны
имеют пометку `HISTORICAL / SUPERSEDED`; не восстанавливай функции только потому,
что они подробно описаны в старом документе. В частности, Snooze не является
production-функцией: это была документационная ошибка, а не скрытый runtime-код.

## Git и rollback

- ветка: `main`
- текущий HEAD может быть новее этого документа; проверь его через
  `git log -4 --oneline --decorate`
- commits результата spike и handoff-документа: `3f2dc8e`, `f82ce49`,
  `6d10e32`, `a1a3668`
- rollback до начала iCloud spike:
  `rollback-before-icloud-feasibility-2026-09-10`
- rollback-tag указывает на commit `d6476b6`
- перед работой проверь `git status --short`; не сбрасывай и не перезаписывай
  пользовательские изменения
- production attachments не должны попадать в Git; `.gitignore` уже проверен

## Что уже есть в production Blink

Не ломать существующую архитектуру:

- SwiftUI GUI → локальные JSON-файлы → `watcher.py` → ntfy → iPhone;
- personal events остаются локальными событиями с отдельными attachment-папками;
- History заморожен: прошедшее событие нельзя редактировать, только удалить или
  duplicate as new event;
- Today/Upcoming: double-click открывает редактор; context-menu Paste/Add Files
  выполняются сразу над сохранённым событием, без Editor и Save;
- Editor attachments проходят draft/staging и фиксируются только Save; Cancel
  отменяет draft;
- несколько файлов обрабатываются all-or-nothing с transactional rollback;
- `has_files` участвует в invalidation уже запланированного personal ntfy push;
- reload при ошибке не заменяет последний хороший список пустым состоянием;
- Weather не ставится в remote schedule: после заданного времени выполняется
  fresh Open-Meteo fetch и один direct briefing за local day;
- Astronomy может заранее ставиться в remote ntfy schedule;
- все текущие UI-функции, календарь, редактор, папки и previews уже покрыты
  существующими тестами.

## Жёсткая граница iCloud spike

Для текущего spike запрещено:

- менять `watcher.py`, `agenda.json`, production SwiftUI behavior или ntfy;
- синхронизировать agenda через iCloud;
- создавать public iCloud links или использовать “Anyone with the link”;
- использовать HTTP/ntfy для обратной передачи файлов;
- читать/сканировать Photos, Documents, Downloads, Desktop или другие
  пользовательские папки;
- создавать symbolic links;
- подключать iPhone exchange к production до отдельного ручного acceptance-теста.

Mailbox — только transport, не database и не source of truth. iPhone никогда
напрямую не изменяет `agenda.json`. Будущие команды: `CREATE_EVENT`, `DONE`.

## Результаты Mac-аудита

- macOS `26.5.2`, build `25F84`;
- фактический iCloud Drive:
  `/Users/vitaliiprotsiuk/Library/Mobile Documents/com~apple~CloudDocs`;
- тестовая зона:
  `iCloud Drive/Shortcuts/Blink_Feasibility/ToMac/`
  `iCloud Drive/Shortcuts/Blink_Feasibility/ToPhone/`;
- `Shortcuts` ранее отсутствовала, создана только эта dedicated test area;
- обычный filesystem API успешно проверен: create/read/rename/delete,
  subdirectory, Unicode, пробелы, одинаковые display names с разными UUID,
  atomic temp→rename;
- flat mailbox packages с финальным `.ready` проверены для CREATE_EVENT, DONE и
  Mac→iPhone manifest;
- `/usr/bin/shortcuts` найден, но на этой системе имеет только `run`, `list`,
  `view`, `sign`; create/import Shortcut с Mac невозможен;
- cross-device iCloud sync и iPhone Share Sheet с Mac не симулировались и не
  считаются подтверждёнными;
- outgoing PDF/JPG в test area — минимальные placeholders для проверки формы
  пакета, не пользовательские документы.

## Формат mailbox под тестом

Incoming:

```text
ToMac/<transfer_id>.event.json
ToMac/<transfer_id>.attachment.<extension>   # optional
ToMac/<transfer_id>.ready                    # last
```

DONE:

```text
ToMac/<command_id>.done.json
ToMac/<command_id>.ready                     # last
```

Mac → iPhone:

```text
ToPhone/<occurrence_id>.manifest.json
ToPhone/<occurrence_id>__01__Permit.pdf
ToPhone/<occurrence_id>__02__Estimate.pdf
ToPhone/<occurrence_id>__03__Photo.jpg
ToPhone/<occurrence_id>.ready                # last
```

Reader в будущем должен игнорировать package без `.ready`, валидировать JSON и
все перечисленные файлы, обрабатывать пакет один раз и помечать/перемещать его
только после успешной обработки.

## Что осталось сделать вручную на реальном iPhone

Mac не может честно выполнить эту часть. Нужно проверить:

1. Shortcut `Blink Test` виден в Files Share Sheet.
2. PDF принимается.
3. Явно переданная фотография/картинка принимается.
4. Ограничение — максимум одно attachment.
5. Запуск без input работает.
6. Собираются Title, Description, Event Date/Time, Priority green/yellow/red,
   Blink Date/Time.
7. Создаётся UUID `transfer_id`.
8. Сначала пишется JSON, затем attachment, затем `.ready`.
9. Destination фиксирован:
   `iCloud Drive/Shortcuts/Blink_Feasibility/ToMac`, без выбора папки при каждом
   запуске.
10. Mac видит полный пакет.

Если iOS заставляет выбирать папку каждый раз, зафиксируй это как architecture
blocker. Не добавляй workaround до отдельного решения.

Будущий `Blink Files` должен читать только `ToPhone`, выбирать по
`occurrence_id`, игнорировать manifest/ready и открывать один файл напрямую или
показывать список при двух и более файлах. Никаких public links, HTTP или ntfy.

## Правила продолжения

1. Если задача касается только spike — работай исключительно в dedicated iCloud
   test area и его отчёте.
2. Если предлагается production-изменение — сначала остановись и явно раздели
   его от spike; не смешивай workstreams.
3. Не утверждай, что iPhone или cross-device sync проверены, пока это не сделал
   пользователь на реальном iPhone.
4. Перед завершением повтори подходящие проверки, покажи фактические результаты,
   проверь `git diff --check` и чистоту Git.
5. В финале укажи: изменённые файлы, commits/tag, что реально проверено, что
   осталось ручным blocker’ом и следующий безопасный шаг.

Начни с read-only аудита текущего состояния и отчёта spike. Код production не
меняй.
