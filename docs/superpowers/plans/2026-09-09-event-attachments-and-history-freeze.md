# Event Attachments and History Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Blink-local event attachments, multiline event text, safe screenshot paste, immutable History, and click/context-menu event interaction while preserving the existing SwiftUI -> JSON -> watcher -> ntfy architecture.

**Architecture:** Keep `agenda.json` as event metadata and add an ignored `event_data/` runtime directory inside the Blink root for draft and permanent attachment files. SwiftUI owns file selection, pasteboard access, draft lifecycle, and row UX; `agenda_store.py` owns metadata validation/migration; `notification_format.py` owns the compact `📎` push projection; `watcher.py` only consumes the manifest and never opens attachment files.

**Tech Stack:** SwiftUI/macOS 14, Swift Package Manager, Python 3, local JSON, ntfy, existing unittest and Swift smoke runner.

## Global Constraints

- Keep all Blink-owned runtime files under `/Users/vitaliiprotsiuk/Desktop/Blink`.
- Do not add SQLite, cloud storage, a second scheduler, a second sender, or a new service.
- Do not put attachment bytes, absolute paths, private runtime state, or the app bundle in public GitHub.
- History records are immutable; only `Duplicate as new event` or Delete is allowed.
- Existing recurring occurrence IDs remain unique; `series_id` owns shared recurring attachments.
- Preserve multiline local text; truncate only the ntfy projection using UTF-8 byte accounting.
- Use atomic JSON writes and recoverable filesystem moves.
- Do not change Weather or Astronomy behavior.

## File map

- Create: `app/attachment_store.py` — pure Python manifest/path rules, safe owner IDs, migration helpers, and testable draft/final directory operations used by Python-side validation.
- Modify: `app/agenda_store.py` — event attachment metadata normalization, History immutability helpers, duplicate-event construction, and recurring-series owner resolution.
- Modify: `watcher.py` — preserve/validate attachment manifest and expose only `has_attachments` to notification formatting.
- Modify: `app/notification_format.py` — add one paperclip marker to personal push projections and byte-safe multiline projections.
- Modify: `test_agenda_store.py`, `test_watcher.py`, `test_notification_format.py` — Python contract coverage.
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift` — attachment metadata, draft/final filesystem bridge, Save/duplicate/history rules, and multiline serialization.
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift` — TextEditor fields, attachment control, row click/hover behavior, and context menus.
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift` — deterministic Swift smoke coverage with temporary Blink roots.
- Modify: `.gitignore` — ignore `event_data/` and any local attachment/runtime outputs.
- Modify: `README.md`, `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`, `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`, `docs/HANDOFF.md` — update the normative storage, lifecycle, UX, and verification contracts.

---

### Task 1: Freeze current state and add the storage contract

**Files:**
- Create: `docs/superpowers/specs/2026-09-09-event-attachments-and-history-freeze-design.md`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- Modify: `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
- Modify: `docs/HANDOFF.md`

- [ ] Step 1: Record the approved design and the `event_data/attachments` + `event_data/drafts` layout.
- [ ] Step 2: Add `event_data/` to the public-repository ignore list without changing existing user runtime files.
- [ ] Step 3: Document frozen History, Duplicate semantics, recurring `series_id`, multiline text, local-only attachments, and paperclip-only pushes.
- [ ] Step 4: Review the docs for contradictions with the current event lifecycle and recurrence rules.
- [ ] Step 5: Commit only these documentation/ignore changes with `docs: specify event attachments and frozen history`.

### Task 2: Add Python attachment metadata and ownership rules

**Files:**
- Create: `app/attachment_store.py`
- Modify: `app/agenda_store.py`
- Test: `test_agenda_store.py`

**Interfaces:**
- `attachment_store.owner_id_for_event(event: dict[str, Any]) -> str`
- `attachment_store.attachments_root(blink_root: Path) -> Path`
- `attachment_store.draft_root(blink_root: Path) -> Path`
- `attachment_store.attachment_manifest(raw: Any, event: dict[str, Any]) -> dict[str, Any]`
- `agenda_store.duplicate_event(event: dict[str, Any], new_id: str, new_start: str | None = None) -> dict[str, Any]`

- [ ] Step 1: Write failing tests for non-recurring owner IDs, recurring `series_id` owners, malformed/absent manifests, and duplicate events that preserve content but receive a new ID and clean lifecycle state.
- [ ] Step 2: Run `.venv/bin/python -m unittest test_agenda_store -q` and confirm the new tests fail.
- [ ] Step 3: Implement pure path/manifest helpers; reject path traversal and never store absolute paths in event metadata.
- [ ] Step 4: Add duplicate construction without changing the source record; preserve recurrence only when explicitly requested and keep new events unfinished/enabled.
- [ ] Step 5: Run the targeted tests and `python -m py_compile app/attachment_store.py app/agenda_store.py`.
- [ ] Step 6: Commit `feat: define local attachment metadata and duplicate events`.

### Task 3: Preserve metadata through watcher and format the push projection

**Files:**
- Modify: `watcher.py`
- Modify: `app/notification_format.py`
- Test: `test_watcher.py`
- Test: `test_notification_format.py`

- [ ] Step 1: Add failing tests proving old events without manifests remain valid, malformed manifests do not crash the watcher, and personal notifications add exactly one `📎` when files exist.
- [ ] Step 2: Add tests for multiline title/description projection: local values remain untouched and the push projection is bounded by UTF-8 bytes without splitting invalid sequences.
- [ ] Step 3: Implement normalized `attachments`/`has_attachments` fields in watcher validation while keeping the watcher blind to attachment bytes.
- [ ] Step 4: Implement a single shared personal push projection for compact title and byte-safe body; leave Weather/Astronomy formatters unchanged.
- [ ] Step 5: Run `.venv/bin/python -m unittest test_watcher test_notification_format -q` and the full Python suite.
- [ ] Step 6: Commit `feat: add attachment marker and safe text projection to pushes`.

### Task 4: Implement Swift draft and permanent attachment storage

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

**Interfaces:**
- `AttachmentManifest` — Codable/Equatable metadata with `ownerID`, `count`, and `hasFiles`.
- `AttachmentWorkspace(root: URL)` — creates drafts, copies selected URLs, converts pasteboard images to JPEG, finalizes a draft, opens a folder, and moves a deleted owner folder to Trash.
- `EventStore.save(_ event: EditableEvent, attachmentWorkspace: AttachmentWorkspace) throws` — persists metadata only after the draft finalization succeeds.

- [ ] Step 1: Add failing Swift smoke cases for draft creation, multi-file copy, JPEG screenshot naming, save finalization, cancel cleanup, and old agenda records without attachment fields.
- [ ] Step 2: Implement `event_data/` path resolution relative to the existing Blink root; do not introduce Application Support or a second data root.
- [ ] Step 3: Implement draft markers and stale-draft cleanup limited to Blink-created draft directories.
- [ ] Step 4: Add atomic finalization and rollback/error reporting so a failed Save does not create an event claiming files it does not own.
- [ ] Step 5: Add immutable History rules: History rows cannot open Edit; Duplicate creates a fresh ID, fresh owner folder, and leaves the source unchanged; Delete confirms and sends attachments to Trash.
- [ ] Step 6: Run `cd app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner` and `swift build -c release`.
- [ ] Step 7: Commit `feat: add Blink-local attachment workspace and frozen history`.

### Task 5: Update event editor, row interaction, and context menu

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

- [ ] Step 1: Add failing Swift checks for multiline title/description round-trip, click-to-edit in Today/Upcoming, frozen History rows, hover treatment, and context-action availability.
- [ ] Step 2: Replace single-line Title/Description fields with multiline editors while preserving required-title validation and stable modal scrolling.
- [ ] Step 3: Add the attachment button/Finder multi-select and show the staged file count in the editor.
- [ ] Step 4: Add saved-row paperclip indicator, `Open Attachments Folder`, `Add Files`, and `Paste Screenshot` actions.
- [ ] Step 5: Make the row content a click target that opens Edit only for Today/Upcoming; keep buttons and context menus independent.
- [ ] Step 6: Add context menu actions with tab-specific gating: History has Duplicate/Delete/attachment actions, never Edit or On/Off.
- [ ] Step 7: Run the Swift smoke runner and release build; manually inspect all three tabs at normal and compact window sizes.
- [ ] Step 8: Commit `feat: add multiline editor and event context actions`.

### Task 6: Full regression, runtime restart, and handoff reconciliation

**Files:**
- Modify: `docs/HANDOFF.md` if verification details change.
- Modify: `BLINK_STATUS_FOR_CHATGPT.md` if runtime status changes.

- [ ] Step 1: Run `.venv/bin/python -m unittest -q` and record the exact count.
- [ ] Step 2: Run `.venv/bin/python -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py`.
- [ ] Step 3: Run `plutil -lint Blink.app/Contents/Info.plist launchd/*.plist`.
- [ ] Step 4: Build and install the Swift release executable inside `Blink.app/Contents/MacOS/Blink`; restart Blink and the watcher only after the build succeeds.
- [ ] Step 5: Run `./status_watcher.command` and verify a fresh heartbeat, then exercise a test event with files, a pasted screenshot, a multiline description, a History duplicate, and a push containing `📎`.
- [ ] Step 6: Verify `git status` contains no private runtime files, attachment bytes, draft bytes, or build artifacts.
- [ ] Step 7: Re-read the design and plan checklists line by line; mark every requirement complete or document a blocker before claiming completion.
- [ ] Step 8: Commit only the intended source/docs changes with `chore: verify event attachments and history freeze`.

## Final cross-check before completion

- [ ] Historical event cannot be edited from click, button, or context menu.
- [ ] Duplicate creates a new ID and folder; source history remains unchanged.
- [ ] Recurring occurrences retain safe unique IDs while sharing `series_id` attachment ownership.
- [ ] Cancel/Escape does not leave a draft folder; a failed Save does not lose staged files.
- [ ] Multiline local text round-trips; push text is compact and byte-safe.
- [ ] Only a paperclip marker enters personal pushes; no local path or file bytes are sent.
- [ ] Weather, Astronomy, ntfy scheduling, lamp, and existing lifecycle behavior remain unchanged.
- [ ] All Blink runtime files remain under the Blink root and public GitHub remains clean.
