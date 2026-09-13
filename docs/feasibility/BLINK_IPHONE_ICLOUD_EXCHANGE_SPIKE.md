# Blink ↔ iPhone private iCloud exchange — feasibility / robustness spike

**Status:** manual feasibility plus Phase 4B/5 acceptance complete; no
production feature enabled.
**Date:** 2026-09-12
**Project:** `/Users/vitaliiprotsiuk/Desktop/Blink`

## Safety boundary

This spike does not modify `watcher.py`, `agenda.json`, production SwiftUI
behavior, ntfy configuration, or any user folders outside the approved
Shortcuts test/acceptance areas. It does not create public iCloud links, access
Photos/Documents, or use HTTP/ntfy for file exchange. The production source of
truth remains the Mac's local Blink JSON and attachment folders.

## Architecture under test

```text
iPhone Shortcut ⇄ private iCloud Drive mailbox ⇄ Mac-side Blink worker (future)
                         
ntfy remains only Mac → iPhone notification transport.
```

The mailbox is transport only, never a database or source of truth. `agenda.json`
is never synchronized and an iPhone command never edits it directly. Candidate
commands are `CREATE_EVENT` and `DONE`; Mac → iPhone files are temporary copies
for viewing.

## Test area

The exchange folders are pre-existing owner-maintained private iCloud folders
outside the Blink repository:

```text
iCloud Drive/Shortcuts/Blink_Feasibility/
  ToMac/
  ToPhone/

iCloud Drive/Shortcuts/Blink_Acceptance/
  ToMac/                         # active Phase 5 target; currently empty
  Archive/Phase5-20260912211629/ # preserved manual artifacts
```

The actual macOS filesystem root is the private Apple Shortcuts container:

`~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents`

Finder may display a breadcrumb resembling `iCloud Drive → Shortcuts`; this is
only the UI label for that private container. No symbolic links are used.

## Part 1 — Mac iCloud filesystem

| Check | Result |
|---|---|
| macOS version | `26.5.2` (build `25F84`) |
| private Shortcuts container | `~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents` |
| `Blink_Feasibility/{ToMac,ToPhone}` availability | pre-existing owner-maintained folders; not created by this spike |
| ordinary filesystem access | PASS: create/read/rename/delete/subdirectory/Unicode/space tests |
| atomic temp → rename | PASS inside `ToMac` |
| `shortcuts` CLI | `/usr/bin/shortcuts`; run/list/view/sign only; no create/import subcommand |

The test used only ordinary filesystem operations. The private container path is
readable and writable by the normal user process; no special Apple API was
required.
Bounded `AI_TEST_*` filesystem artifacts created by the spike were removed
after verification. The folders may contain owner files that predate the spike;
they are user-owned, are not fixtures, and must never be renamed, moved,
deleted, or interpreted as a mailbox package. The user-provided Finder
screenshots on 2026-09-11 confirm ordinary files already exist in both `ToMac`
and `ToPhone`.

## Part 2 — mailbox package format

The tested package shape is deliberately flat and uses a final marker. The
examples describe the proposed protocol only; they do not describe or authorize
treatment of pre-existing owner files in these folders. Two
`CREATE_EVENT` fixtures with different transfer IDs but the same
`original_filename` validated that display names do not have to be unique:

```text
ToMac/
  <transfer_id>.event.json
  <transfer_id>.attachment.<extension>   # optional
  <transfer_id>.ready                    # created last

ToPhone/
  <occurrence_id>.manifest.json
  <occurrence_id>__01__Permit.pdf
  <occurrence_id>__02__Estimate.pdf
  <occurrence_id>__03__Photo.jpg
  <occurrence_id>.ready                  # created last
```

The spike created and validated two incoming `CREATE_EVENT` packages, one
`DONE` command package, and one outgoing manifest;
the `.ready` marker for `AI_TEST-order` was written after its JSON and attachment
(mtime check passed). The `DONE` fixture uses the same flat
`<command_id>.done.json` + `<command_id>.ready` shape. The future Mac reader
must ignore incomplete packages until `.ready` exists,
validate the JSON and all listed files, process a package once, and move or mark
it only after successful processing. No per-event dynamic directories are
needed.

## Part 3 — Shortcut design and confirmed manual results

The manual phase used four test Shortcuts: `Blink Test` for file transport,
`Blink Files` for Mac → iPhone viewing, `Blink DONE Test` for the ntfy action,
and `Blink Create Test` for CREATE_EVENT. All use the fixed private Shortcuts
container and `Ask Where To Save = OFF`.

Confirmed PASS results on the real iPhone and Mac:

1. iPhone → Mac Share Sheet file transport to `ToMac` (PDF, image, and other
   files).
2. Mac → iPhone `ToPhone` retrieval and Quick Look.
3. External `shortcuts://run-shortcut` text input.
4. Real ntfy DONE button producing a matching `.done.json` and `.ready`.
5. CREATE_EVENT direct launch without attachment.
6. CREATE_EVENT from Share Sheet with one image attachment.
7. CREATE_EVENT from Share Sheet with one PDF attachment.
8. Repeated Viber PDF share after the source received `Always Allow`.
9. Direct-launch regression after attachment logic changes.

`Blink Create Test` accepts only `Images`, `PDFs`, and `Files` from the Share
Sheet. It supports direct launch with no input and at most one attachment.
It collects Title, Description, Event Date/Time, green/yellow/red Priority, and
Blink Date/Time.

During testing, the attachment branch incorrectly used `If Attachment has any
value`. Direct launch supplied an empty Text value, which created the zero-byte
artifact `918491446.attachment.`. The branch was corrected to `If HasAttachment
is true`; the follow-up direct-launch regression produced only `.event.json`
and `.ready`, with no attachment file.

The observed privacy behavior is intentionally recorded without inferring an
internal iOS permission model: Photos received `Always Allow`, Viber received
`Always Allow`, first access showed privacy prompts, and repeated Viber PDF
sharing did not show another prompt.

The original spike used a 9-digit Random Number while exploring the transport.
The accepted production-native transport identity is now
`<yyyyMMddHHmmss>-<9-digit-random>`; the complete combined value is the
`command_id`/`transfer_id`, never an event ID or event start time.

## Part 4 — confirmed package contracts

DONE package:

```text
ToMac/<command_id>.done.json
ToMac/<command_id>.ready                # written last
```

CREATE_EVENT without an attachment:

```text
ToMac/<transfer_id>.event.json
ToMac/<transfer_id>.ready                # written last
```

CREATE_EVENT with one attachment:

```text
ToMac/<transfer_id>.event.json
ToMac/<transfer_id>.attachment.<extension>
ToMac/<transfer_id>.ready                # written last
```

The order is always JSON, attachment if present, then `.ready` last. The test
DONE Shortcut ends with `Stop This Shortcut`, which removed the old output/
privacy popup. A future reader must still ignore packages without a matching
`.ready`, validate all contents, and apply a package only once.

## Part 5 — Mac → iPhone viewing package

The outgoing fixture used minimal test placeholders with the expected
`.pdf`/`.jpg` names; it was a package-shape test, not a claim that those files
contain user documents. Existing ordinary files visible in `ToPhone` are
owner-owned and outside the fixture/protocol. The future `Blink Files` Shortcut should read only `ToPhone`, select files by
`occurrence_id`, ignore `.manifest.json` and `.ready`, and open one file directly
or present a list when there are two or more. Quick Look/standard preview is
enough. No public links, HTTP, or ntfy are involved.

## Part 6 — Phase 5 actual CREATE acceptance

The owner migrated the existing `Blink Create Test`; the safety duplicate
`Blink Create Test BACKUP` was not modified. The active Shortcut writes to the
separate acceptance inbox
`~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/Blink_Acceptance/ToMac`.
Manual acceptance passed for CREATE without attachment, with one image, and
with one PDF. The observed successful examples were:

- `20260912192619-650719048.event.json` + `.ready`, with no attachment;
- `20260912194513-228316619.event.json` + matching `.attachment.jpeg` + `.ready`;
- `20260912194754-657491603.event.json` + matching `.attachment.pdf` + `.ready`.

The final JSON contract carried explicit-offset `start`/`created_at`,
`reminder_intent.offsets_minutes_before`, `attention_level`, and
`blinker_intent.minutes_before`, with no Mac-owned lifecycle fields. Manual
checks passed for arbitrary integer values including reminders `[3, 0]`, `17`,
and `240`, blinker `0`, `3`, and `240`, empty Description, and rejection of
empty Title/invalid reminder input. The Mac importer independently enforces
the required Title and integer-minute rules. A deliberately past event package
was created successfully; lifecycle handling is reserved for Phase 6.

After acceptance, 25 historical entries were moved reversibly with filenames
preserved to
`~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/Blink_Acceptance/Archive/Phase5-20260912211629`.
The active `Blink_Acceptance/ToMac` inbox is empty. Production mailbox
processing remains disabled and no production root is configured.

## Findings and recommendation

The flat package plus final `.ready` marker is feasible with ordinary filesystem
operations and avoids complicated directory-sync semantics. The real iPhone
tests confirmed the fixed private destination, Share Sheet inputs, cross-device
appearance, Quick Look, DONE, and CREATE_EVENT paths listed above. Production
Blink remains unchanged; these results authorize documentation of feasibility,
not production integration.

### Open design question: the originating ntfy DONE notification

After the user taps DONE, the iPhone creates the DONE package. A future Mac
importer will validate it and call the normal Blink Done path. It is not yet
decided what should happen to the original ntfy notification:

- clear it immediately after the button tap;
- keep it until Mac confirms successful package receipt and application; or
- use another acknowledgement UX.

`clear=true` is not an approved production solution. Decide this separately
before implementing the production DONE action.

## Next stage (Phase 6 controlled acceptance; production still disabled)

The existing Mac-side mailbox reader/importer may be enabled only for a
controlled run against the empty `Blink_Acceptance/ToMac` root. It requires
matching `.ready`, validates JSON and any declared attachment, is idempotent,
treats duplicate DONE and stale occurrences as NO-OPs, survives malformed
packages without blocking later packages, and removes transport files only
after successful application. Remote DONE calls the existing Blink Done
business logic; Remote CREATE_EVENT calls the existing event
creation/persistence path. The mailbox must never become the source of truth or
a second scheduler/sender. Production `Blink_Production/ToMac` remains unused.

Phase 6A CREATE without attachment and Phase 6B CREATE with a PDF were
completed against the acceptance root on 2026-09-12. The PDF package
`20260912214413-360011007` initially arrived with iCloud `dataless` bytes; the
reader now treats macOS `Errno 11 (Resource deadlock avoided)` during JSON or
attachment access as `PENDING_SYNC`, leaves the exact package untouched, and
retries after the bytes become local. Once downloaded, the package was
committed to a Mac-generated event-ID owner folder and removed only after the
agenda/attachment commit. The past-start PDF event was observed in Today/Active
with Attention still enabled, matching the current `requires_done` lifecycle.

The controlled real DONE request was accepted by ntfy, but the existing
`Blink DONE Test` Shortcut wrote its package
`20260912215237-901727503.done.json` + `.ready` to the historical
`Blink_Feasibility/ToMac`, not the acceptance inbox. Those feasibility files
remain untouched; the DONE importer was not pointed at that path. A future
DONE acceptance requires an owner-approved Shortcut target for
`Blink_Acceptance/ToMac`.

## Reproducibility evidence

The bounded filesystem test created only `AI_TEST_*` files under the dedicated
`Blink_Feasibility` area and removed only those files. Historical Phase 5 files
in the separately approved `Blink_Acceptance/ToMac` were later moved
reversibly, with names preserved, into its sibling archive; the feasibility
folders were not changed. No production runtime files are part of this spike.
