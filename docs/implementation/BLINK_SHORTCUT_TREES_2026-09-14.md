# Blink Shortcut trees and acceptance inventory

**Snapshot:** 2026-09-14  
**Authority:** current contract and roadmap. This file records actual tree
evidence separately from desired production contracts.

## Canonical targets

| User-facing target | Purpose | ntfy input | Status |
|---|---|---|---|
| Blink | CREATE from direct launch or Share | CREATE payload | clean final tree/physical acceptance still required |
| Blink DONE | apply a DONE command on Mac | blink-done-v1|<event-id> | controlled Acceptance exists; canonical production acceptance still required |
| Blink Files | open event attachments on iPhone | blink-files-v1|<package-id> | one-file Acceptance passed physically; multi-file open |

## Proven Files tree

The physically accepted Acceptance candidate is package-scoped:

    Get file from Shortcuts at path
      Blink_Acceptance/ToPhoneView/<package-id>
    Get Contents of Folder
    Choose from List
    Show Selected Item in Quick Look

The installed Mac candidate currently also has the standard Shortcuts
completion/output guard after Quick Look:

    Stop and output -> Quick Look
    If there’s nowhere to output -> Do Nothing

That guard is part of the currently installed candidate; it is not evidence
that a production tree has been cut over.

The chooser receives the folder contents, not the flat package root. It shows
only original safe basenames, for example Appointment Schedule (1).pdf.
Manifest, .ready, package IDs, technical prefixes, and unrelated packages are
never copied into the view folder.

## Live multi-file Acceptance checkpoint

On 2026-09-14 a new controlled package was generated from the personal event
`event-0f6edc58-50f4-48fb-9423-15ddb499d876` at reminder offset `10`:
`blink-files-v1-b7125ae665b167365d197f0bb7785b2c`. The flat package validated
with two files, and its derived view contains only `485 Notice.jpeg` and
`Appointment Scheduled (1).pdf`.

The notification was sent to the existing Acceptance subscription with the
target `Blink Files Stage2 WORK`. iPhone Mirroring displayed the notification
and accepted the tap, but opened the Shortcuts library without running the
shortcut/chooser. This is a Mirroring-vs-physical behavior difference, so
multi-file physical Acceptance remains OPEN and requires one physical tap.

## CREATE tree contract

    Receive Shortcut Input (direct launch or Share)
    Collect Title, Description, Date, Time, Importance
    Collect zero or more Reminders using integer-minute validation
    Collect one independent Blinker value using integer-minute validation
    Normalize local date/time with timezone
    Build CREATE_EVENT v2 flat payload
    Write package to selected ToMac root
    Write .ready last

The tree must reject more than one shared attachment. It must preserve Unicode,
multiline text, date/time, reminders, blinker, and importance. The exact action
names and complete iPhone body must be recorded after the clean candidate is
built; no unverified physical result is claimed here.

## DONE tree contract

    Receive Shortcut Input as Text
    Parse blink-done-v1|<event-id>
    Build one DONE payload with actual command time
    Write to selected ToMac root
    Write .ready last
    Finish

The phone does not edit agenda state. The Mac importer applies DONE, preserves
the original event start, records done_at, moves the event to History, and
silently ignores replays/no-ops.

## Files transport contract

Flat package (integrity layer):

    <package-id>.manifest.json
    <package-id>__01__<safe-original-name>
    <package-id>__02__<safe-original-name>
    <package-id>.ready

View package (iPhone presentation layer):

    ToPhoneView/<package-id>/
      <safe-original-name-1>
      <safe-original-name-2>

The Mac sorts source attachments deterministically before assigning ordinals,
validates safe basenames and duplicates, builds the view atomically, and cleans
it up idempotently.

## ntfy action contract

For an eligible personal event with attachments, ntfy exposes two independent
actions in this order:

    Done; Files

Done targets Blink DONE with EventID. Files targets Blink Files with PackageID.
Production names must not contain Candidate, Test, WORK, Stage2, Runtime, or
Acceptance.

## Synchronization gate

Every changed tree requires:

1. Mac Shortcuts GUI harmless edit and Save.
2. Wait for iCloud.
3. Open Edit on iPhone.
4. Compare the complete action body and build marker, not only the name.
5. Run/push only after equality is confirmed.

The add/remove Stop Shortcut experiment is historical evidence only.

## Acceptance matrix

| Test | Required evidence |
|---|---|
| CREATE direct | one event reaches Mac with expected fields |
| CREATE Share | one shared attachment accepted; second rejected |
| DONE | EventID applied once; duplicate is silent |
| Files one | original name and Quick Look — PASS |
| Files multiple | two or more isolated names and Quick Look — OPEN |
| Combined event | Done and Files buttons independently work — OPEN |
| Production | canonical names/paths and smoke test — OPEN |

## Historical objects

Candidate, Test, BACKUP, Stage2 WORK, Runtime Diagnostic, and Feasibility
shortcuts are not production targets. Keep the working fallback until the
canonical production replacement passes. Cleanup requires a separate inventory
with KEEP / DELETE / WHY.

The five visible `.done.json` + `.ready` pairs in
`Blink_Acceptance/ToMac` are explicitly stale Acceptance artifacts and must not
be applied or deleted before the Acceptance importer/cleanup audit:

    20260913023352-385630113
    20260913213223-646956164
    20260913213317-748777692
    20260913213646-153651294
    20260913214022-944321537

## Mac library snapshot

The Shortcuts library currently contains 17 entries. Blink-related entries
observed on 2026-09-14 are:

| Name | Classification |
|---|---|
| Blink Files Candidate — CHOOSER-ACCEPTANCE-20260913-A \| GUI-SAVED | accepted one-file candidate; preserve until cutover |
| Blink JSON Serialization Test | test |
| Blink Create Test | test/candidate |
| Blink Create Stage2 WORK | work candidate |
| Blink Create Test BACKUP | fallback backup |
| Blink DONE Test | test/candidate |
| Blink DONE Test BACKUP Stage2 | fallback backup |
| Blink Files | historical/canonical fallback; preserve |
| Blink Files Stage2 WORK | work candidate |
| Blink Files BACKUP Stage2 | fallback backup |
| Blink Files Runtime Diagnostic — DIRECT-NAME-ACCEPTANCE-20260913-A \| GUI-SAVED | historical diagnostic |
| Blink Test | test |
| RU Fix (Selected Text) | unrelated utility |

The four `Начальные команды` entries are unrelated Apple starter shortcuts.
No entry is deleted or renamed until the Acceptance matrix passes and a final
KEEP/DELETE/WHY inventory is approved by the Production gate.
