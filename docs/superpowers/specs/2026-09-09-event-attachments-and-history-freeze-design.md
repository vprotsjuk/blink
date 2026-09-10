# Event Attachments and History Freeze Design

**Date:** 2026-09-09  
**Status:** Approved direction; implementation not started

## Goal

Add local event attachments, multiline event text, safe screenshot paste, and direct row editing without coupling the personal-event feature to Weather, Astronomy, ntfy transport, or a second scheduler. Historical events are immutable: they may be duplicated as a new event or deleted, but never edited in place.

## Non-negotiable boundaries

```text
SwiftUI GUI -> local JSON + Blink-local event files -> watcher.py -> ntfy/lamp
```

- `watcher.py` remains the only production sender and scheduler.
- Weather and Astronomy contracts are unchanged.
- Attachment bytes never travel through ntfy and never enter `agenda.json`.
- All Blink-owned runtime data stays below `/Users/vitaliiprotsiuk/Desktop/Blink` so the project can be backed up or removed as one folder.
- Public GitHub source must continue to exclude private runtime data, attachments, drafts, the app bundle, and build/runtime artifacts.
- Existing event IDs, completion state, recurrence, queue deduplication, and blinker behavior must remain compatible unless explicitly covered below.

## Storage model

The project root gains one ignored runtime directory:

```text
event_data/
  attachments/<owner-id>/       saved files for one event or recurring series
  drafts/<draft-id>/            files selected before Save
```

`owner-id` is the ordinary event `id` for non-recurring events and the stable `series_id` for a recurring series. Existing recurring occurrences keep their unique internal occurrence IDs (`series_id-gN`) so queue dedupe and Done transitions remain safe; their attachments resolve through the common series owner.

The persisted event metadata adds only a small attachment manifest, for example:

```json
"attachments": {
  "owner_id": "event-…",
  "count": 2,
  "has_files": true
}
```

No absolute paths or file contents are stored in `agenda.json`. A missing or malformed manifest is treated as no attachments, allowing old events to migrate safely.

## Draft lifecycle

Opening New Event creates a draft UUID and a Blink-owned draft directory. File selection and screenshot paste copy bytes into that directory immediately. The event is not written to `agenda.json` until Save.

On Save, the app validates the draft, chooses the permanent event/series owner, materializes the staged files under `event_data/attachments/<owner-id>`, and atomically persists the event metadata. The draft marker is removed only after the JSON save succeeds; if persistence fails, the staged draft is retained and the user sees a recoverable error. Cancel, Escape, or a rejected dirty-modal close removes only the current Blink-created draft. Startup removes only stale directories under `event_data/drafts/` that carry Blink's draft marker; it never scans or deletes arbitrary user folders.

Deleting an event with attachments requires confirmation and moves the Blink-owned attachment directory to the macOS Trash rather than silently deleting user files. A later dedicated cleanup action is not part of the first implementation.

## Text and notification behavior

- Title and Description use multiline editors and preserve internal newlines and paragraphs locally.
- Title remains fully stored in `agenda.json`, but the ntfy title/header is a compact single-line projection (first useful line, safely bounded to ntfy's title limit).
- Description remains fully stored locally. The push body uses the largest safe UTF-8 byte length supported by the current ntfy contract and truncates only the push projection, never the source text.
- Links remain ordinary user-entered Description text; no separate link subsystem is introduced.
- If the attachment manifest says files exist, personal push titles/bodies include one `📎` marker. They do not include local paths or filenames.

## Attachments UX

The editor shows an attachment control that opens an `NSOpenPanel` with multiple selection. Existing saved events expose `Open Attachments Folder`. A screenshot can be pasted through the event context menu; the first image representation on the macOS pasteboard is converted to a unique JPEG name such as `screenshot-20260909-114500.jpg`.

Every event row supports a hover treatment and a single click on its content area opens the same editor as Edit in Today, Upcoming, and History. Action buttons remain independent and must not trigger row editing.

The contextual menu is supplemental to visible controls and contains the applicable actions: Edit (only for non-History events), Duplicate as new event, Add Files, Paste Attachment or Paste Screenshot according to the current pasteboard, Open Attachments Folder, On/Off, Done, and Delete. History has no Edit action.

## ID and History semantics

- New ordinary event: new UUID, new owner folder.
- Edit from Today or Upcoming: same event ID and same owner folder.
- History: frozen record. It cannot be edited; only Duplicate as new event or Delete is offered.
- Duplicate as new event: new UUID and new owner folder; source event remains untouched. The first implementation does not share folders between the source and duplicate. Copying source files into the duplicate is an explicit duplicate action choice, not implicit sharing.
- Recurring events: preserve current unique occurrence IDs and stable `series_id`; one attachment owner/folder per series.

## Error and compatibility rules

- File names are sanitized only for the destination basename; original display names remain in the manifest/UI where useful.
- Copy failures, unsupported pasteboard content, permission errors, and missing folders are shown in the editor and never partially published as an event with a false attachment count.
- Old events with no attachment fields continue to load and send exactly as before.
- The watcher reads only the boolean/count metadata needed to add `📎`; it does not inspect attachment files or become a file manager.

## Verification expectations

The implementation must cover draft creation/cancel cleanup, save/move atomicity, multiline round-trip, UTF-8 push projection, paperclip formatting, JPEG paste, per-event and recurring-series ownership, immutable History UI, Duplicate semantics, row-click editing, context-menu actions, old-event migration, and deletion-to-Trash behavior. Weather, Astronomy, ntfy scheduling, blinker state, and existing event lifecycle tests must remain green.
