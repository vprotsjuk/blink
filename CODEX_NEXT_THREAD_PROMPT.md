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

Вопросы, которые нельзя потерять после компакта: `Paste Screenshot` принимает любое изображение из буфера (включая обычное скопированное фото) и делает timestamped JPEG; Excel/PDF/file URLs и папки импортируются только через `Attach Files`; каталоги не копируются рекурсивно. Drag-and-drop на строки пока не реализован отдельным путём: если добавлять, принимать только обычные файлы, использовать существующую draft-папку, подсвечивать строку, отклонять каталоги и запрещать drop в замороженную History.
