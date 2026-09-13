# Blink — Complete handoff for the next Codex thread

**Snapshot:** 2026-09-13  
**Project root:** `/Users/vitaliiprotsiuk/Desktop/Blink`  
**Owner language:** Russian. Technical collaboration may be English.

## Mission for the next thread

First reconstruct Blink from the repository and this handoff. Then ask a new
ChatGPT thread for an independent diagnosis of the unresolved iPhone Quick
Look problem. Do not assume earlier reports are correct; inspect the actual
Shortcut trees and running code.

Exact task to send to the new ChatGPT thread:

> Blink Files Stage2 WORK completes on iPhone with a checkmark, but tapping
> the ntfy `Files` action does not display the PDF. The PDF opens manually in
> Files, and the package is present in `Blink_Acceptance/ToPhone`. Compare the
> proven old `Blink Files` Shortcut with `Blink Files Stage2 WORK`, determine
> whether the final one-file action must be `Show Item from List in Quick Look`,
> ordinary `Quick Look`, or another action, and verify the type/output of
> `AllFiles`, `Attachments`, and `Get First Item`. Give a safe, exact edit plan
> that preserves package isolation and does not use `Open Item` unless proven
> necessary. Do not change production mailbox settings or send a new push.

## Authority and safety

Read and reconcile these files against the actual checkout:

1. `BLINK_FULL_DESCRIPTION_FOR_CHATGPT.md`
2. `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
3. `docs/HANDOFF.md`
4. `docs/feasibility/BLINK_IPHONE_ICLOUD_EXCHANGE_SPIKE.md`
5. `docs/implementation/BLINK_REMAINING_ROADMAP.md`
6. this file

Then run:

```bash
cd "/Users/vitaliiprotsiuk/Desktop/Blink"
git status --short
git log -20 --oneline --decorate
```

Never modify `Blink Files` or `Blink Files BACKUP Stage2` while diagnosing the
WORK candidate. Do not enable `BLINK_MAILBOX_ENABLED`, configure
`Blink_Production/ToMac`, add `clear=true`, start Stage 3/5/6, or send another
ntfy notification until the owner explicitly authorizes it.

## Product and architecture

Blink is a local macOS reminder and daily-information application:

```text
SwiftUI GUI -> local JSON + Blink-owned attachment folders -> watcher.py
             -> ntfy -> iPhone/Mac notifications
             -> USB blinker (future hardware adapter)
```

`agenda.json` and local attachment folders are the source of truth. SwiftUI is
the editor/viewer only. `watcher.py` is the single production scheduler,
sender, queue reconciler, and current blinker coordinator. ntfy is transport,
never a database. Do not add a second sender/scheduler, SQLite, cloud backend,
Calendar integration, public URLs, phone-to-Mac round trips, or unrelated
cross-block coupling.

## Repository and runtime

- `watcher.py`: production scheduler/sender/blinker process.
- `app/agenda_store.py`: event persistence, lifecycle, recurrence, locking.
- `app/event_timing.py`: timezone-aware timing.
- `app/attachment_store.py`: transactional local attachment ownership.
- `app/notification_format.py`: canonical ntfy projection/action builder.
- `app/ntfy_schedule.py`: rolling 24-hour queue and signatures.
- `app/mailbox_importer.py`: opt-in/test mailbox parser and transaction layer.
- `app/BlinkSwiftUI/`: native GUI and Swift contract tests.
- `event_data/attachments/<event-id>/`: canonical occurrence files.
- `event_data/drafts/<draft-id>/`: editor staging only.

The normal Python command is `.venv/bin/python -m unittest -q`; root-level
`test_*.py` modules are used and there is no importable `tests/` package.

## Event, attachment, notification, and mailbox contracts

Every event has `id`, `title`, `start` with explicit UTC offset,
`reminders_minutes_before`, and `enabled`; optional `description` preserves
arbitrary Unicode, quotes, backslashes, and newlines. Lifecycle is:

```text
Upcoming -> Active -> Done -> History
```

`done=true` is authoritative even for a future start. Done preserves `start`,
records `done_at`, clears attention/blinker eligibility, and is idempotent.
History is frozen; duplication creates a new event and attachment owner.
Recurring successors get a new ID and no files.

Attachments are local and transactional, owned by occurrence ID:

```text
event_data/attachments/<event-id>/
event_data/drafts/<draft-id>/
```

JSON stores metadata only, never absolute paths or bytes. Editor Add Files,
Paste, and drop are draft operations until Save; Today/Upcoming row Paste and
Add Files are immediate persisted operations. Finder file URLs take priority
over image clipboard data; unsupported text/directories are rejected.

Personal/Astronomy reminders use the rolling 24-hour queue; Weather is a
separate direct delivery. ntfy headers carry title/priority/tags; body is
human-readable, never raw JSON or local paths. Queue signatures include
`has_files`, so visible paperclip transitions rebuild pending payloads while
count-only changes do not duplicate delivery. Direct and queued paths use the
same canonical action builder.

Remote DONE input is exactly `blink-done-v1|<event_id>`. Production default
Shortcut name is `Blink DONE`; test override is
`BLINK_NTFY_DONE_SHORTCUT_NAME`. The original DONE notification is unchanged;
a newly applied remote DONE may emit one separate short confirmation without
an action button and without `clear=true`. Replays/no-ops/stale/malformed/
pending/failed commands are silent.

## iCloud transport and production gates

Verified private container:

```text
~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents
```

Relevant folders:

```text
Blink_Feasibility/ToMac       historical/manual feasibility only
Blink_Feasibility/ToPhone     historical/manual feasibility only
Blink_Acceptance/ToMac        controlled acceptance only; mailbox OFF
Blink_Acceptance/ToPhone      controlled Files package inbox
Blink_Production/ToMac        must remain unused
```

The mailbox importer and production mailbox remain disabled. Never consume,
delete, or move historical feasibility files during this task.

Files packages are flat and written with `.ready` last:

```text
<package-id>.manifest.json
<package-id>__01__<safe-basename>
<package-id>__02__<safe-basename>
<package-id>.ready
```

Package IDs are deterministic `blink-files-v1-<sha256-prefix>`. Queued
packages are regenerated from current canonical attachments; delivered
snapshots are immutable until bounded cleanup. Manifest contains exact package
ID, source event/reminder identity, ordered filenames, sizes, and SHA-256;
there are no absolute paths. Exact stem ownership and fail-closed validation
are mandatory.

Files input is `blink-files-v1|<package-id>`, encoded in the custom URL scheme
with `%20`, never `+`, and without `clear=true`:

```text
shortcuts://run-shortcut?name=Blink%20Files&input=text&text=blink-files-v1%7C<package-id>
```

Files action is opt-in only through `BLINK_NTFY_FILES_ACTION_ENABLED=1` and
explicit `BLINK_TO_PHONE_ROOT`.

## Actual Shortcuts

### `Blink DONE Test`

Manually verified on iPhone. It accepts `blink-done-v1|EVENT123`, validates the
escaped literal-pipe regex, splits on literal `|`, gets item 2, and sets
`EventID`. It writes `.done.json` and `.ready` into
`Blink_Acceptance/ToMac`; it no longer uses `Blink_Feasibility/ToMac`.

### `Blink Create Test`

The existing flat/v2 CREATE test was accepted with explicit-offset dates,
arbitrary integer reminder/blinker values, empty Description, and one image or
PDF attachment. Preserve `Blink Create Test BACKUP`.

### `Blink Files` and backup

`Blink Files` is the old proven Shortcut and must not be modified. Preserve
`Blink Files BACKUP Stage2` unchanged. Its proven final path was:

```text
Get File / folder from Shortcuts/Blink_Feasibility/ToPhone
→ Get Contents of File (the action was applied to the folder in the old UI)
→ Choose from Folder Contents
→ Show Selected Item in Quick Look
```

### `Blink Files Stage2 WORK` current tree

This is the only Shortcut under investigation:

```text
Receive Shortcut Input (no input: Continue)
Get Text from Shortcut Input
Match Text:
  ^blink-files-v1\|blink-files-v1-[0-9a-f]{32}$
If Matches does not have any value
  Stop This Shortcut
Otherwise
Split Shortcut Input by literal |
Get Item at Index 2
Set Variable PackageID

Get file from Shortcuts at path Blink_Acceptance/ToPhone
Get Contents of File
Set Variable AllFiles
Text [PackageID].ready
Set Variable ReadyName
Filter AllFiles where Name is ReadyName
Count ready matches
If ready count is not 1 → Stop This Shortcut

Text [PackageID].manifest.json
Set Variable ManifestName
Filter AllFiles where Name is ManifestName
Count manifest matches
If manifest count is not 1 → Stop This Shortcut

Text [PackageID]__
Set Variable AttachmentPrefix
Filter AllFiles where Name begins with AttachmentPrefix
Set Variable Attachments to Files
Count Items in Attachments
Set Variable AttachmentCount to Count
If AttachmentCount is 0 → Stop This Shortcut
Otherwise
  If AttachmentCount is 1
    Choose from Attachments (Select Multiple OFF)
    Show Selected Item in Quick Look
  Otherwise
    Choose from Attachments (Select Multiple OFF)
    Show Selected Item in Quick Look
  End If
End If
```

The regex, `.ready` check, manifest check, exact attachment prefix, and
fail-closed count branch are present. The one-file and multi-file branches now
use the same `Choose from Attachments` → `Show Selected Item in Quick Look`
pattern. The final actions remain Quick Look, not `Open Item`.

## Unresolved real-device problem

The first controlled Files ntfy push was accepted with HTTP 200 and a valid
package. On iPhone, tapping `Files` opened Shortcuts; the Shortcut completed
with a checkmark, but no PDF preview appeared. The same PDF opens manually in
the Files app, so iCloud/package availability is proven. The owner screenshots
also confirm that `Blink Files Stage2 WORK` exists and runs. The Mac WORK tree
was then repaired so its acquisition prefix matches the proven old pattern:
`Get file from Shortcuts at path Blink_Acceptance/ToPhone` followed by
`Get Contents of File`, with `AllFiles` bound to `Folder Contents`. One new
Files-only push was then sent explicitly to this WORK target. The owner
reported the same result: Shortcuts opens, WORK shows a checkmark, no chooser
appears, and no PDF remains visible.

The controlled Mac-side evidence immediately before that push was:
`AllFiles = 3` (manifest, `.ready`, and one PDF), `.ready matches = 1`,
`manifest matches = 1`, and `Attachments = 1`. The WORK plist has 46 actions,
and its successful-count path is `Choose from Attachments` → `Show Selected
Item in Quick Look`; no fail-closed branch should be selected for this
package. The pre-repair WORK copy had 42 actions. The owner's subsequent
iPhone editor screenshot now confirms the repaired acquisition prefix is
present on the phone, so the stale-version hypothesis is removed. The
unchanged canonical `Blink Files` control and the temporary `Blink Files
Acquisition Test` have now both displayed choosers and opened PDFs on the
current iPhone. The remaining unobserved boundary is therefore WORK-specific
runtime output after `AllFiles`: package parsing, dynamic filters, counts, and
the type passed to `Attachments`. No further push should be sent until that
boundary is diagnosed.

Do not add another contents action after `Attachments` unless the independent
review proves its input is the folder and its output is a file list. The old
Shortcut visibly called the action `Get Contents of File` while applying it to
the ToPhone folder; the current macOS action library may expose that operation
under a different name. Adding it to PDF attachments can convert file
references into raw contents and break Quick Look. Verify the actual input and
output types in the editor before changing anything.

The editor and SQLite action blob establish that `AllFiles` and the filtered
`Attachments` are File items/references, not raw bytes. The one-file branch was
therefore changed to the same chooser-plus-Quick-Look pattern already used by
the multi-file branch. The old and backup Shortcuts remain unchanged. This is
still a diagnostic candidate, not an accepted fix: do not declare success until
a physical iPhone run visibly shows the PDF.

## Cleanup and forbidden actions

Keep WORK, test Shortcuts, backups, and acceptance package files until Files
acceptance is resolved and documented. Later cleanup may remove obsolete test,
WORK, and proof artifacts only after accepted replacements exist; intentional
backups remain.

Forbidden now: production mailbox enablement, `Blink_Production/ToMac`, changes
to unrelated Shortcuts, new Home Screen icon, Today Briefing implementation,
USB hardware work, `clear=true`, and phone-to-Mac acknowledgement loops.

## Roadmap

- **[DONE]** Mac core, persistence, lifecycle, attachments, Weather,
  Astronomy, Location, queue, DONE/CREATE transport, Phase 4B/5/6 acceptance,
  Phase 7 refresh.
- **[DONE]** Stage 0 — documentation reconciliation.
- **[DONE]** Stage 1 — Early Done, remote DONE confirmation, Attention/Dock.
- **[DONE]** Stage 2A — Mac attachment snapshots and ToPhone infrastructure.
- **[DONE]** Stage 2B — Shortcut audit and hardening design.
- **[CURRENT]** Stage 2C — iPhone Shortcut implementation and Quick Look
  diagnosis.
- **[REMAINING]** Stage 2D — physical iPhone acceptance, one-file and
  multi-file behavior.
- **[REMAINING]** Stage 2E — Stage 2 closeout and production decision.
- **[REMAINING]** Today Morning Briefing.
- **[REMAINING]** Final phone setup: one `Blink` Home Screen icon and
  Share→Blink flow.
- **[REMAINING]** Cleanup of obsolete test/WORK/proof artifacts.
- **[LATER]** USB RGB adapter and numeric mailbox/package/worker limits.

## Required next-thread report

Return to the owner in Russian: actual Git status/commit; actual Shortcut trees
inspected; independent ChatGPT diagnosis; exact minimal edit or proof no edit
is needed; whether physical retest is required; updated documentation files;
tests/checks for code changes; and explicit confirmation that production
mailbox stayed disabled and no new notification was sent unless authorized.
