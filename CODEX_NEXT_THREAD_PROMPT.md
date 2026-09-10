# Blink: Short Prompt for the Next Codex Task

Работаем в существующем проекте `/Users/vitaliiprotsiuk/Desktop/Blink`. Сначала прочитай:

1. `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
2. `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
3. `docs/HANDOFF.md`

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
