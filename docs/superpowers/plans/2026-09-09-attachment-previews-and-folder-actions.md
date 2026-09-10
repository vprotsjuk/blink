# Attachment Previews and Folder Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make event attachment actions reflect what is currently possible, always expose an empty attachment folder for editable events, and show clear previews of staged and saved files without changing Blink’s scheduler/watcher architecture.

**Architecture:** Keep attachment bytes under Blink’s existing `event_data/` directory. SwiftUI will derive the context menu from the current tab, event state, and pasteboard image availability; `AttachmentWorkspace` will create an empty owner folder on demand and enumerate safe regular files for previews. `BlinkStore.loadEvents()` will reconcile attachment counts from the owner folder during its existing 30-second UI reload, so files placed through Finder become visible without adding a watcher or database.

**Tech Stack:** SwiftUI/AppKit, Swift Package Manager, existing `AttachmentWorkspace`, local JSON manifest, current Swift smoke runner.

## Global Constraints

- Keep all Blink-owned runtime files under `/Users/vitaliiprotsiuk/Desktop/Blink`.
- Do not add cloud storage, a second scheduler, a second sender, or a new file-watching service. Keep JSON plus the attachment folders canonical; if a future scale test proves a database useful, SQLite may be added only as a rebuildable search index.
- Active/Upcoming events may open an empty attachment folder; frozen History may only open an existing attachment folder.
- `Paste Screenshot` appears only when the macOS pasteboard contains usable image data.
- Images get thumbnails; non-image files get type icons. Do not parse Excel/PDF contents.
- Search matches attachment filenames (and file extensions) in addition to title, description, date, and status.
- Cancel/Escape removes only the current draft folder; saved event folders remain local and outside Git.
- Preserve frozen History and recurring-series attachment ownership rules.

---

### Task 1: Lock the behavior in failing tests

**Files:**
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`

- [x] **Step 1: Add a failing source contract for dynamic context actions.**

  Assert that `EventRowView` gates `Paste Screenshot` on an image-availability helper, shows `Open Attachments Folder` for every non-History row, and gates it by existing attachments for History.

- [x] **Step 2: Add a failing source contract for editor previews.**

  Assert that the editor contains an attachment preview/list view, image thumbnail handling, non-image fallback icon handling, and a staged-file remove action.

- [x] **Step 3: Run the targeted runner and confirm the new assertions fail.**

  Run: `cd /Users/vitaliiprotsiuk/Desktop/Blink/app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner`

  Expected: the new folder-action/preview contracts fail before implementation.

- [x] **Step 4: Update the normative contract text.**

  Record that active events can open/create an empty folder, History can only reveal an existing folder, the menu omits unavailable paste actions, and previews are thumbnails/icons with no file-content parsing.

### Task 2: Add safe folder enumeration and metadata reconciliation

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AttachmentStore.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/Models.swift`
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

- [x] **Step 1: Add failing tests for empty-folder creation and regular-file enumeration.**

  Verify `ensureAttachmentFolder(ownerID:)` creates a folder under `event_data/attachments`, ignores hidden entries/directories, and returns only regular files for previews.

- [x] **Step 2: Implement `ensureAttachmentFolder(ownerID:)` and `files(ownerID:)`.**

  Reuse `safeComponent`, create only the requested owner directory, and filter with `isRegularFileKey` plus `.skipsHiddenFiles`.

- [x] **Step 3: Reconcile manifests during `BlinkStore.loadEvents()`.**

  For each decoded event, read the owner folder manifest and update only `attachments.owner_id`, `count`, and `has_files` when the on-disk count differs. Keep the existing JSON atomic-write behavior and leave all unrelated fields untouched.

- [x] **Step 4: Run targeted Swift tests and compilation.**

  Run: `cd /Users/vitaliiprotsiuk/Desktop/Blink/app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner`

  Expected: empty-folder and manifest-reconciliation tests pass.

### Task 3: Implement dynamic menus and attachment previews

**Files:**
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/ContentView.swift`
- Modify: `app/BlinkSwiftUI/Sources/BlinkSwiftUICore/AttachmentStore.swift`
- Modify: `app/BlinkSwiftUI/Tests/BlinkSwiftUITestRunner/main.swift`

- [x] **Step 1: Add a pasteboard image-availability helper.**

  Use the same TIFF/PNG/JPEG/HEIC decoding path as `clipboardJPEGData()`. The helper must return false for text, file URLs, Excel/PDF URLs, and folders.

- [x] **Step 2: Gate context-menu actions.**

  In Today/Upcoming, always show `Open Attachments Folder`; show `Paste Screenshot` only when the helper returns true. In History, never show add/paste actions and show folder access only when `event.hasAttachments` is true.

- [x] **Step 3: Ensure the folder before opening it.**

  `openAttachmentsFolder(for:)` calls `ensureAttachmentFolder(ownerID:)` for editable events, then opens the URL with `NSWorkspace`. Existing History folders are opened read-only; no new History folder is created.

- [x] **Step 4: Add the editor attachment list.**

  Show saved owner files plus current draft files in a compact scrollable list. Render image thumbnails with `NSImage`; render non-images with a generic/type file icon. Display filename and size, and provide `Remove` only for files in the current draft.

- [x] **Step 5: Refresh previews after attach/paste and preserve draft cleanup.**

  Reuse the existing draft workspace. After each attach/paste, refresh the list and count. Save finalizes the draft; Cancel/Escape discards it. A failed operation leaves the draft and visible list unchanged.

- [x] **Step 6: Extend event search to attachment filenames.**

  Read the owner folder’s regular-file names through `AttachmentWorkspace.files(ownerID:)` during the existing filtered-view pass. Match the normalized filename and extension without reading file contents or introducing SQL. The same helper remains the future seam for an optional rebuildable SQLite index.

- [x] **Step 7: Run the Swift smoke runner and perform visual QA.**

  Run: `cd /Users/vitaliiprotsiuk/Desktop/Blink/app/BlinkSwiftUI && swift run BlinkSwiftUITestRunner`

  Manually inspect Today, Upcoming, and History; open an empty active-event folder, place a file in Finder, wait for the normal reload, and confirm the paperclip/count and preview appear.

### Task 4: Release gate, restart, and plan reconciliation

**Files:**
- Modify: `docs/HANDOFF.md` if verification details change.
- Modify: `BLINK_STATUS_FOR_CHATGPT.md` if runtime status changes.

- [x] **Step 1: Run the full Swift and Python checks.**

  Run the Swift runner, `swift build -c release`, `.venv/bin/python -m unittest -q`, `python3 -m py_compile watcher.py app/*.py astronomy/generate_astronomy.py`, and `git diff --check`.

- [x] **Step 2: Install the release executable and restart Blink.**

  Copy the release product to `Blink.app/Contents/MacOS/Blink`, restart the launchd app, and verify `./status_watcher.command` reports a fresh heartbeat.

- [x] **Step 3: Verify repository hygiene.**

  Confirm `git status` contains only intended source/docs/plan changes and no `event_data/`, drafts, attachments, or build products.

- [x] **Step 4: Re-read this plan line by line and mark every checkbox complete.**

  Reconcile the final report against the plan so no behavior, test, documentation, or restart step is omitted.
