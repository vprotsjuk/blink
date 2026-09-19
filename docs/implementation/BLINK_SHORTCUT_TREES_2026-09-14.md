# Blink Shortcut trees and acceptance inventory

**Snapshot:** 2026-09-14  
**Authority:** current contract and roadmap. This file records actual tree
evidence separately from desired production contracts.

## Correction — 2026-09-16

The latest canonical `Blink Files` body is the 47-action flat-root tree
saved on Mac:

```text
Receive (Apps and 18 more; no input -> Continue)
Get text from Shortcut Input
Comment (build marker)
Match ^blink-files-v1\|blink-files-v1-[0-9a-f]{32}$ in Text
If Text has no value -> Stop this shortcut
Otherwise -> End If
Split Text by |
Get Item at Index 2 from Split Text
Set PackageID
Get file from Shortcuts at path Blink_Acceptance/ToPhone
Get contents of File
Set AllFiles to Folder Contents
Filter ready and manifest markers
Filter attachment prefix PackageID__
Count and fail closed when empty
Choose from Attachments
Show Selected Item in Quick Look
```

The preserved fallback physically opens both JPEG and PDF. The canonical body
has now been replaced in place with the verified flat-root body, with marker
`FILES-CANONICAL-FLAT-20260916 | GUI-SAVED`; its source is confirmed as
`Shortcuts`, not the `PackageID` token. The iPhone body still requires the
usual lock/sync verification before physical canonical acceptance. The former
dynamic-path body remains comparison/rollback evidence only; this result is
not evidence that iOS universally forbids Magic Variables in path fields.

## Canonical targets

| User-facing target | Purpose | ntfy input | Status |
|---|---|---|---|
| Blink | CREATE from direct launch or Share | CREATE payload | Gate A/B implemented; direct, one-image, and two-image iPhone paths verified; final representative text/Files acceptance remains |
| Blink DONE | apply a DONE command on Mac | blink-done-v1|<event-id> | controlled Acceptance exists; canonical production acceptance still required |
| Blink Files | open event attachments on iPhone | blink-files-v1|<package-id> | canonical flat-root filtering tree saved on Mac; iPhone sync + JPEG/PDF acceptance |

## Proven Files tree

The physically accepted Acceptance candidate is package-scoped:

    Get file from Shortcuts at path
      Blink_Acceptance/ToPhoneView/<package-id>
    Get Contents of Folder
    Choose from List
    Show Selected Item in Quick Look

The current Mac candidate has the input fail-closed guard before the package
lookup and then ends directly at Quick Look. The obsolete `.ready`, manifest,
technical-prefix, count, and duplicate chooser branches were removed from the
candidate; they remain only in preserved fallback/evidence shortcuts.

The chooser receives the folder contents, not the flat package root. It shows
only original safe basenames, for example Appointment Schedule (1).pdf.
Manifest, .ready, package IDs, technical prefixes, and unrelated packages are
never copied into the view folder.

On 2026-09-15 the canonical `Blink Files` Shortcut was repaired in place. The
former canonical body had only four actions and read the historical
`Blink_Feasibility/ToPhone` folder; that was the concrete reason a valid
package action opened the stale single file `745 Windsor...`. The first repair
used a 14-action dynamic path, but iPhone execution completed without a
chooser, indicating that nested `ToPhoneView` was not a reliable iPhone
boundary. The canonical body was therefore replaced with the existing
flat-root package-filtering tree, retaining its ready/manifest/prefix checks
and chooser branches. The Mac editor marker is now
`FILES-CANONICAL-FLAT-20260916 | GUI-SAVED`. The canonical body now has 47
actions, including the flat-root package filters and fail-closed count branch.
iPhone body synchronization and the final two-file physical run remain open.

On 2026-09-15 the iPhone editor exposed the concrete runtime defect in this
tree: the `Get file` action's source token was `PackageID`, while its path was
`Blink_Acceptance/ToPhone`. That is not the intended Shortcuts/iCloud source;
the shortcut therefore reached its fail-closed `AttachmentCount = 0` stop and
showed only a completion checkmark. The canonical Mac tree was corrected so
the action now reads `Get file from Shortcuts at path
Blink_Acceptance/ToPhone`, and the complete corrected body was verified in the
iPhone editor. No filters, validation, package naming, or Quick Look actions
were changed by this repair. A fresh physical two-file run is still required.

## Live multi-file Acceptance checkpoint

On 2026-09-14 a new controlled package was generated from the personal event
`event-0f6edc58-50f4-48fb-9423-15ddb499d876` at reminder offset `10`:
`blink-files-v1-b7125ae665b167365d197f0bb7785b2c`. The flat package validated
with two files, and its derived view contains only `485 Notice.jpeg` and
`Appointment Scheduled (1).pdf`.

On 2026-09-15 the one-file path was physically exercised from a live ntfy
notification: the `Files` action opened Shortcuts, showed the single file in
the chooser, and opening that filename displayed the file successfully. This
closes one-file Acceptance.

The same controlled two-file package was independently verified on Mac and in
the Acceptance iCloud container. Its manifest and ready marker are valid, and
its package-scoped view contains exactly `485 Notice.jpeg` and `Appointment
Scheduled (1).pdf`. A fresh ntfy notification was accepted with HTTP 200 and
displayed the `Files` action on iPhone. The multi-file action still requires
one physical tap while the phone is unlocked/in use; Mirroring lost control
when the owner used the phone. JPEG+PDF chooser/Quick Look therefore remains
open and is not declared accepted.

The notification was sent to the existing Acceptance subscription with the
target `Blink Files Stage2 WORK`. iPhone Mirroring displayed the notification
and accepted the tap, but opened the Shortcuts library without running the
shortcut/chooser. A subsequent physical tap reproduced the boundary
definitively: Shortcuts opened `Blink Files Stage2 WORK`, it finished with a
checkmark, and no chooser or Quick Look appeared. Thus the failure was inside
the old running tree after launch, not the ntfy URL or package staging.

The original 47-action tree remains preserved and was restored to its original
flat `Blink_Acceptance/ToPhone` path. An isolated Mac-only experiment,
`Blink Files Stage2 VIEW TEST`, was created from a duplicate. It now has 14
actions: the dynamic path `Blink_Acceptance/ToPhoneView/<PackageID>/`,
`Get Contents of Folder`, one chooser, and Quick Look, with only the PackageID
input guard retained. Its build marker is
`FILES-FINAL-DYNAMIC-20260914 | GUI-SAVED`. Earlier helper and duplicate invoke
experiments are not production targets. End-to-end iPhone/live-banner
acceptance is still pending, so this candidate is not yet cut over to the
canonical `Blink Files` name.

## CREATE tree contract

    Receive Shortcut Input (direct launch or Share)
    Collect Title, Description, Date, Time, Importance
    Collect zero or more Reminders using integer-minute validation
    Collect one independent Blinker value using integer-minute validation
    Normalize local date/time with timezone
    Build CREATE_EVENT v1 flat payload
    Write package to selected ToMac root
    Write .ready last

The production tree must reject more than one shared attachment. It must preserve Unicode,
multiline text, date/time, reminders, blinker, and importance. The exact Mac
candidate additions are recorded below; the complete iPhone body and physical
Share/banner result remain separate acceptance evidence.

### Accepted CREATE source — exact inspected action groups

On 2026-09-14 the Mac Shortcuts GUI was inspected from top to bottom for the
untouched `Blink Create Test` source (93 actions in the current library
snapshot). The observed order and responsibility map is:

1. **Input/attachment branch:** receive `Images and 2 more` from Share Sheet;
   continue when there is no input; when `Shortcut Input` has a value, get its
   first item, set `Attachment`, read `Name` into `OriginalFilename`, read
   `File Extension` into `OriginalExtension`, and set `HasAttachment` to text
   `true`. The otherwise branch sets `Attachment`, `OriginalFilename`, and
   `OriginalExtension` to empty Text and `HasAttachment` to text `false`.
2. **Title:** ask for Text with prompt `Title`; set `Title`; `Match \\S` in
   `Title`; stop when the match has no value.
3. **Description:** ask for optional Text with prompt `Description (optional)`;
   set `Description` directly to `Ask for Input`. No sanitizing or replacement
   action is present.
4. **Start:** ask for Date and Time with prompt `Event start date and time`;
   set `EventDateTime` directly to `Ask for Input`.
5. **Importance:** choose menu `Attention level` with exactly `green`,
   `yellow`, and `red`; set `AttentionLevel` from `Menu Result`.
6. **Reminders:** ask for Text with the comma-separated reminder prompt; set
   `ReminderOffsetsText`; split by comma; repeat each item; match
   `^\\s*\\d+\\s*$`; stop on failed match; get numbers; accept only numbers
   `>= 0`; add them to `ReminderOffsets`; stop if the final list has no value.
7. **Blinker:** ask for Number with prompt `Blinker lead time in minutes
   before start (default 0)`; set `BlinkerMinutesBefore`; convert it with
   `Get text from BlinkerMinutesBefore`; match the full text against `^\d+$`,
   stopping when the match has no value; then retain the original independent
   `>= 0` check. This rejects fractions and malformed values without coercion.
8. **Transport/time values:** format `Current Date`; generate a random number
   from `100000000` through `999999999`; combine into `TransferID`; format
   `EventDateTime` into `EventDateTimeISO`; format current date into
   `CreatedAtISO`.
9. **Attachment serialization:** if `HasAttachment` is text `true`, construct
   `AttachmentJSON` with basename from `TransferID` plus the attachment
   extension and `original_filename` from `OriginalFilename`; otherwise set
   `AttachmentJSON` to empty Text.
10. **Payload and writes:** build the visible JSON Text template containing
    `type: CREATE_EVENT`, `transfer_id`, `title`, `description`, `start`,
    `reminder_intent.offsets_minutes`, `attention_level`,
    `blinker_intent.minutes_before`, and `created_at`; set the file name to
    `TransferID.event.json`; save to `Shortcuts`; when attached, save the
    attachment under `TransferID.attachment.OriginalExtension`; save `READY`
    as `TransferID.ready`; stop the Shortcut.

The visible payload template in this accepted source currently says
`"version": 1`. The importer contract accepts v1/v2, so this is recorded as
actual source evidence and is not silently reclassified as v2. No dedicated
build-marker Comment was visible in the inspected source; the five visible
Comments are prompts/section separators for Title, Description, Date/Time,
Reminders, and Blinker. The source remains untouched and is the rollback
reference for work on `Blink Create Stage2 WORK`.

This inspection confirms two boundaries in the untouched source rather than
silently changing the rollback reference: it visibly uses `First Item` without
a separate multi-item Share rejection, and its Blinker path visibly checks only
`>= 0`. The active candidate addresses the first boundary below; the source
remains unchanged and the second boundary is still open.

### CREATE Stage2 WORK audit checkpoint

The active `Blink Create Stage2 WORK` candidate was inspected before editing.
It retained the same visible input, field collection, reminder, Blinker,
serialization, attachment, and `.ready` write path as the accepted source, but
had 94 actions rather than 93. After its reachable `Stop this shortcut`, it
contained an additional unreachable `Dictionary` action with eight items,
including visible diagnostic-looking values `version=2`, `type=CREATE_EVENT`,
`reminder_offsets`, `blinker_minutes_before`, `transfer_id`, and `title`.
That block was removed from the candidate only. After Mac GUI save-touch, the
candidate re-opened in the library as 93 actions and its reachable tail again
matches the accepted source, including the `version: 1` JSON Text template and
the `.ready` write. `Blink Create Test` remained untouched at 93 actions.

### CREATE Gate A — Share Sheet more-than-one rejection

Gate A was applied only to `Blink Create Stage2 WORK`, one behavioral change at
a time. The candidate now begins its input handling with:

1. `Count Items in Shortcut Input`.
2. `If Count is greater than 1`.
3. `Show Alert` — `Blink accepts at most one attachment.`.
4. `Stop this shortcut`.
5. `Otherwise`, followed by the pre-existing input path and its
   `Get First Item` behavior for the single-item case.

The Mac editor was saved and the candidate was re-opened from the library as
99 actions at that checkpoint. The visible order confirms the rejection actions are inside the
new true branch, before the original single-attachment branch; the accepted
source remains 93 actions and untouched. A focused macOS `shortcuts run` smoke
with two real file inputs returned `Running was cancelled`, which is the
expected stop-path result, before Title/serialization could run. No CREATE
payload was produced by that rejection path. This proves the candidate's Gate
A behavior at the Shortcut/runtime level; physical iPhone Share Sheet evidence
is recorded below.

Gate B was then applied only to this candidate as the next isolated change.

### CREATE Gate B — Blinker integer rejection

The candidate now uses native numeric validation immediately after the Blinker
input assignment. The untouched source was not changed. The saved candidate
contains 104 actions and the new sequence is:

1. `Round BlinkerMinutesBefore to Integer`.
2. `If Rounded Number is BlinkerMinutesBefore`.
3. `Otherwise` -> `Stop this shortcut`.

The pre-existing non-negative gate remains in the surrounding Blinker path, so
the combined behavior is integer equality plus `>= 0` without Number -> Text ->
regex conversion.

This is the implemented Gate B shape: it must reject fractions without
locale-sensitive Number -> Text -> regex conversion and preserve valid `0` and
positive integers. No accepted Reminder, Date/Time, serialization, or
`.ready` behavior may be removed.

Physical iPhone evidence after Mac save/sync:

- `Test B0` with Blinker `0` created
  `20260915151902-696741911.event.json` and `.ready`; the payload contains
  `reminder_intent.offsets_minutes_before=[0]`, explicit `-07:00`, and
  `blinker_intent.minutes_before=0`.
- `Test B17` with Blinker `17` created
  `20260915151925-946819941.event.json` and `.ready`; the payload contains
  `blinker_intent.minutes_before=17`.
- `Test B15` with `1.5` and `Test Bneg` with `-1` returned to the Shortcuts
  library without creating a new `.event.json` or `.ready` pair.

This closes the Gate B runtime check; representative CREATE and physical
Share Sheet multi-item acceptance remain open.

One-image Share Sheet acceptance then exposed the expected iOS privacy gate:
`Allow “Blink Create Stage2 WORK” to save 1 photo to a file?`. After choosing
`Always Allow`, the run completed and produced the fresh pair
`20260915160605-559478233.event.json` plus `.ready`, alongside
`20260915160605-559478233.attachment.jpeg`. The JSON preserved the selected
image's `original_filename` (`IMG_3618`) and the independent Blinker `0`.

### CREATE validation contract — preserve during cleanup

The physically accepted `Blink Create Test` is the source tree for this
contract. Files cleanup did not change it. Validation is product behavior, not
temporary Shortcut complexity:

- **Title:** required; empty and whitespace-only values stop the Shortcut.
  The `Match \S` check must not strip valid Unicode, emoji, punctuation, or
  other non-whitespace characters.
- **Description:** optional text is passed through unchanged, including
  multiline paragraphs, Unicode, emoji, quotes, backslashes, punctuation, and
  newlines.
- **Reminders:** one or more comma-separated, non-negative integer minutes;
  presets remain `1440, 720, 300, 60, 30, 10, 5, 0`; Custom accepts integers
  only. Negative, fractional, alphabetic, and mixed-symbol values stop the
  Shortcut and must never be rounded or coerced to zero.
- **Blinker:** exactly one independent, non-negative integer-minute value with
  the same preset/Custom semantics as the Mac editor. Invalid text, letters,
  negatives, and fractions must stop the Shortcut; it must not silently become
  another value. The untouched source uses `Ask for Number` plus `>= 0`; the
  active candidate uses native Round-to-Integer equality plus native `>= 0`.
  Physical
  iPhone/UI evidence remains an acceptance gate before CREATE production
  cutover.
- **Attachments:** direct launch with no attachment remains valid. Share Sheet
  accepts the supported file/image/PDF types and at most one item; a folder,
  empty direct input, or a second item must not be treated as a valid single
  attachment. The current source's `First Item` branch is preserved after the
  candidate's explicit Count > 1 rejection; physical iPhone Share evidence is
  still required before production cutover.
- **Date/time:** keep the explicit UTC-offset/timezone representation; do not
  replace it with naive date serialization.
- **Transport ID:** format is exactly `yyyyMMddHHmmss-<9-digit-random>`, with
  random range `100000000..999999999`.

### CREATE behavior matrix

`Before` is the accepted `Blink Create Test` tree plus the Mac importer tests.
`After` is the current 104-action `Blink Create Stage2 WORK` candidate after
Gates A+B. Physical iPhone evidence covers valid Blinker `0`/`17`, rejection
of `1.5`/`-1`, two-image rejection, and one-image acceptance.

### iPhone sync checkpoint — 2026-09-15

### CREATE transport recovery — 2026-09-15 02:11

The known-good transport was physically restored through the untouched
`Blink Create Test` oracle. With Mirroring connected, a fresh direct run using
Title `Transport Recovery Test`, empty Description, explicit-offset start
`2026-09-23T02:06:00-07:00`, green Attention, Reminder `0`, and Blinker `17`
created both files in the exact Acceptance mailbox:
`20260915021144-935344778.event.json` and
`20260915021144-935344778.ready`. The JSON preserves the title, offset,
Reminder `[0]`, Blinker `17`, and a 9-digit random suffix. The `.ready` and
`.event.json` have the same materialization second. This proves the current
failure was not an iCloud backlog and that the proven Save/publication path is
available again.

The same physical direct flow was then run against `Blink Create Stage2 WORK`
with a valid title and Reminder `0`. The Shortcut returned to the library, but
no fresh candidate pair appeared in `Blink_Acceptance/ToMac`. This is now a
candidate-only differential failure; Gate A/B and iCloud are no longer valid
general explanations. The candidate remains frozen while its reachable
Gate-B-to-save path is compared against the untouched oracle.

### Current transport regression retest — 2026-09-19 11:51–11:52

After a clean iPhone Shortcuts restart, `Blink Create Stage2 WORK` completed a
valid direct run (title, empty description, default date/time, green attention,
Reminder `0`, Blinker `0`) and returned to the library without a fresh
`.event.json` or `.ready`. The untouched `Blink Create Test` oracle was then
run with the same input shape and also produced no fresh pair. The Mac
Acceptance mailbox and all local `ToMac` folders were checked by modification
time. `brctl status iCloud~is~workflow~my~workflows` reported the Shortcuts
container caught-up/full-sync with no pending materialization. The 2026-09-15
oracle success remains historical evidence, but the current failure is now a
shared physical Save/write boundary regression, not a candidate-only Gate A/B
failure. Do not change CREATE logic until this boundary is restored or an
Apple-side permission/path cause is proven.

### iCloud upload-loop evidence — 2026-09-19 12:04–12:06

The owner materialized the `Blink_Acceptance/ToMac` folder on Mac and a fresh
candidate run was repeated. The folder still contained only the historical
2026-09-15 payloads; no new `.event.json` or `.ready` appeared. Finder then
reported `Uploading 2 items` with progress repeatedly approaching completion
and restarting. CloudDocs logs showed the corresponding cycle: one item
finished uploading, two edited items were received from cloud, and another
item was sent back to cloud. This proves an active iCloud/CloudDocs
upload-conflict loop around the Shortcuts container. It is now the leading
transport blocker; do not alter CREATE action logic while this loop persists.

### Latest candidate transport retest — 2026-09-15

After Mirroring was reconnected, the current Mac editor run of `Blink Create
Stage2 WORK` reached the end of the reachable body (the visible tail contained
the `READY` text and `Stop this shortcut`) and was stopped cleanly. The exact
Acceptance `ToMac` mailbox still contained only the earlier oracle pair
`20260915021144-935344778`; no new candidate `.event.json` or `.ready` was
materialized. This is additional evidence for the candidate-only failure, but
not iPhone physical acceptance: the Mac run is a separate execution boundary.
No Shortcut object was deleted or replaced. The recovery rule is now explicit:
if one more stable differential comparison does not expose a concrete
reachable defect, restore this candidate from untouched `Blink Create Test`
and reapply only the Acceptance path, Gate A, and Gate B deltas.

### In-place candidate baseline restoration — 2026-09-15

The recovery rule was executed without creating a Shortcut object: the
existing `Blink Create Stage2 WORK` action body was replaced in-place from the
untouched oracle copy. The Mac library now reports `93 actions` for both
`Blink Create Test` and `Blink Create Stage2 WORK`, and the candidate's visible
body matches the oracle, including the original `First Item` attachment branch
and original Blinker path. Gate A and Gate B are intentionally not present in
this restored baseline; they are to be reapplied as two isolated, recoverable
changes with GUI save-touch and acceptance after each.

### Three-role simulator parity — 2026-09-15

The simulator is intentionally limited to the three product roles, with
historical Shortcut names represented only as profiles. The known-good fresh
CREATE payload `20260915021144-935344778.event.json` was fed back through the
CREATE simulator; `accepted=True` and the produced payload matched the real
JSON exactly, including title, explicit offset, `created_at`, reminders,
Blinker, and transport ID. A real historical DONE package was likewise
replayed through the DONE simulator and matched its JSON and filenames. The
existing Acceptance `ToPhoneView` package containing `485 Notice.jpeg` and
`Appointment Scheduled (1).pdf` was replayed through the Files simulator and
produced the same two visible files and selected-file path.

These are parity checks of logical/transport output only. They do not promote
the simulator over physical Apple acceptance: Share Sheet delivery, iCloud
materialization, ntfy deep links, and Quick Look remain real-device gates.

Historical checkpoint, superseded by the in-place restoration from the
untouched oracle on 2026-09-15: the candidate was opened in iPhone Mirroring
under the same name and the live editor visibly showed Gate A in a previous
100-action body. That proved sync of that prior body, not product Acceptance.
The restored current candidate is 99 actions with Gate A only; Gate B has not
been reapplied.

In the superseded pre-restoration 100-action body, Gate B was physically
exercised through the live CREATE flow: after valid
Title, empty optional Description, default Date/Time, green Importance, and
valid Reminder `30`, the Blinker field received `1.5`. Pressing `Done` ended
the Shortcut and returned to the Shortcuts library without continuing CREATE.
No new file appeared in the Acceptance `ToMac` mailbox, and no `.ready` was
created. This remains historical evidence for the old candidate body and is
not evidence that native Gate B is present in the current 99-action candidate.

A subsequent non-fractional run was initially inconclusive while iCloud state
was being inspected. The mailbox contains an older
`20260914222838-949257520.event.json` plus its `.ready`, preserving Unicode
Title `Еуые`, explicit `-07:00` start offset, Reminder `[0]`, Blinker `17`,
and the required 9-digit transport suffix. The user later identified that
payload as an older run, not the later `Test 17` run; the later run produced no
new file in `ToMac`. Therefore this payload is retained as historical evidence
only, not as physical acceptance of the current candidate. A fresh
valid run must be correlated by timestamp and title before acceptance.

After the Mac save-touch at approximately 23:00, a fresh controlled iPhone
run at approximately 23:05 used Title `17`, empty Description, green
Attention, Reminder `0`, and Blinker `0`. The Shortcut returned to the library,
but `ToMac` still contained no new `.event.json`/`.ready` pair. This confirms
that the valid direct path remains unresolved despite the Mac tree being saved
at the then-current 100-action body; do not advance to attachment or Files
acceptance yet. The candidate was subsequently restored, so Gate B must be
reapplied and reverified before that gate can be considered closed.

### Differential CREATE checkpoint — 2026-09-15 12:10–12:12

The current candidate was launched on iPhone with valid Blinker `0` and
completed back to the Shortcuts library, but produced no new
`.event.json`/`.ready` pair. Untouched `Blink Create Test` was then run with
the same direct-launch shape, Reminder `0`, and Blinker `0`; it also returned
to the library without a new mailbox pair. The failure is therefore not
currently attributable to the new native Gate B condition. CREATE
transport/write-path or iCloud mailbox routing remains the active differential
investigation; no candidate bypass or source edit is authorized.

The Mac Shortcuts Save action was independently opened on the untouched source
and resolved to the real `Blink_Acceptance/ToMac` folder, not a similarly named
local folder. Finder then showed that folder with an iCloud transfer in
progress (`Uploading 2 items`) while still listing only historical entries;
the local filesystem likewise contained no files from either fresh run. This
narrows the failure to iCloud materialization/transfer or the final Save
publication boundary, rather than Gate B logic. No source Shortcut was edited
during this inspection.

CloudDocs evidence was then narrowed to the exact private Shortcuts container:
`brctl status iCloud~is~workflow~my~workflows` reports `caught-up` and
`has-synced-down`, with no pending item listed. Earlier `bird`/`cloudd` upload
activity and one retry after `BRCloudDocsErrorDomain Code=140`
(`un-acked in-flight diffs`) remain historical clues, but they do not explain
the absent fresh files after the container returned to caught-up. The
authoritative status is therefore: `CREATE transport failure under
investigation; current evidence favors the final Shortcut Save/publication
boundary over an iCloud sync backlog`.

| Case | Expected | Before | After |
|---|---|---|---|
| empty Title | rejected | rejected | unchanged |
| whitespace-only Title | rejected | rejected | unchanged |
| normal Unicode Title | preserved | accepted/preserved | unchanged |
| multiline Description | preserved | accepted/preserved | unchanged |
| Reminder `17` | accepted | accepted | unchanged |
| Reminder `0` | accepted | accepted | unchanged |
| Reminder `-1` | rejected | rejected | unchanged |
| Reminder `17.5` | rejected | rejected | unchanged |
| Reminder `abc` | rejected | rejected | unchanged |
| Reminder mixed symbols/text | rejected | rejected | unchanged |
| Blinker valid integer | accepted | accepted by integer contract/parser | iPhone accepted for 0 and 17; fresh pairs verified |
| Blinker letters | rejected | rejected by transport/parser; phone UI gate | Ask for Number/regex rejection; no coercion |
| Blinker decimal | rejected | transport rejects; phone UI gate | iPhone 1.5 returned without fresh pair |
| direct launch, no attachment | accepted | physically accepted | unchanged |
| Share one PDF | accepted | physically accepted / parser green | unchanged |
| Share one image | accepted | parser green; physical pair verified | fresh event + attachment + ready pair verified |
| Share more than one item | rejected clearly | source used `First Item`; no explicit rejection | macOS and iPhone Photos paths show alert → Stop; no payload |
| special characters/newlines | survive serialization | parser green | unchanged |
| explicit-offset Date/Time | preserved | parser green | unchanged |
| native transport ID | exact 14 digits + 9 random digits | tree/parser green | unchanged |

The matrix is intentionally not reduced to an action-count claim. A future
CREATE cleanup must prove every protected behavior before deleting or merging
its corresponding validation block.

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
| Files multiple | both JPEG and PDF opened through preserved fallback; canonical dynamic path — OPEN |
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

The original snapshot contained 20 entries. The current Mac recheck contains
26 entries because several experimental duplicates were created during the
subsequent investigation. The original list remains historical; the current
execution inventory is recorded below.

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
| Blink Files Stage2 VIEW TEST | isolated dynamic-view experiment; preserve for rollback/evidence |
| Blink Files VIEW INVOKE TEST | isolated local-input helper; test only |
| Blink Files BACKUP Stage2 | fallback backup |
| Blink Files Runtime Diagnostic — DIRECT-NAME-ACCEPTANCE-20260913-A \| GUI-SAVED | historical diagnostic |
| Blink Test | test |
| RU Fix (Selected Text) | unrelated utility |

The four `Начальные команды` entries are unrelated Apple starter shortcuts.
No entry is deleted or renamed until the Acceptance matrix passes and a final
KEEP/DELETE/WHY inventory is approved by the Production gate.

## Current execution inventory

This is the working inventory after the latest Mac Shortcuts recheck. “Delete
now” means disposable agent-created experiment only; it is not permission to
delete an accepted fallback or any transport file. GUI deletion still needs a
separate action-time confirmation.

| Shortcut | Keep now | Delete now | Delete after cutover | Reason |
|---|---:|---:|---:|---|
| Blink Create Test | yes |  |  | physically accepted CREATE source |
| Blink Create Stage2 WORK | yes |  | yes | current CREATE work candidate |
| Blink Create Test BACKUP | yes |  | yes | CREATE rollback fallback |
| Blink DONE Test | yes |  |  | physically accepted DONE source |
| Blink DONE Test BACKUP Stage2 | yes |  | yes | DONE rollback fallback |
| Blink Files Candidate — CHOOSER-ACCEPTANCE-20260913-A \| GUI-SAVED | yes |  | yes | accepted one-file fallback |
| Blink Files Candidate — CHOOSER-ACCEPTANCE-20260913-A \| GUI-SAVED 2 | yes |  | yes | direct two-file chooser proof |
| Blink Files Stage2 VIEW TEST | yes |  | yes | one active dynamic-path candidate |
| Blink Files Stage2 WORK | yes |  | yes | rollback/evidence for old failure |
| Blink Files | yes |  | yes | historical fallback |
| Blink Files BACKUP Stage2 | yes |  | yes | Files rollback fallback |
| RU Fix (Selected Text) and Apple starters | yes |  |  | unrelated user/system shortcuts |
| Blink Nested Invoke TEST 20260915 |  | yes |  | nested UI experiment concluded |
| Blink Files VIEW INVOKE TEST |  | yes |  | helper experiment concluded |
| Blink Files Acceptance DYNAMIC 20260915 |  | yes |  | duplicate old flat 47-action model |
| Blink Files Acceptance PACKAGEPATH 20260916 |  | yes |  | duplicate old flat 47-action model |
| Blink Files Acceptance MULTI 20260915 |  | yes |  | empty/suspect experimental duplicate |
| Blink Files Acceptance FIXED INVOKE 20260915 |  | yes |  | empty/suspect experimental duplicate |
| Blink Files Runtime Diagnostic — DIRECT-NAME-ACCEPTANCE-20260913-A \| GUI-SAVED |  | yes |  | historical diagnostic |
| Blink Test |  | yes |  | obsolete test |
| Blink JSON Serialization Test |  | yes |  | obsolete test |
| Blink Files Candidate — CHOOSER-ACCEPTANCE-20260913-A \| GUI-SAVED 1 |  | yes |  | duplicate accepted candidate |

The current Files implementation chunk is to simplify the existing VIEW TEST
candidate in place. No new Shortcut is required. The old 47-action Stage2
candidate remains only until the simplified dynamic candidate passes the
physical acceptance matrix; it is not a design to extend.

## Explicit candidate ToMac retest — 2026-09-19 12:15–12:18

The active candidate was minimally edited in Mac Shortcuts only: all three
reachable `Save` actions (event JSON, optional attachment, and final `.ready`)
were explicitly bound to the verified folder `Blink_Acceptance/ToMac`. The Mac
picker exposed the exact private iCloud URL ending in
`Documents/Blink_Acceptance/ToMac/`; `Blink Create Test` was not edited. A GUI
save-touch caused CloudDocs to upload and apply changed Shortcut records, after
which the candidate was run again on the reconnected iPhone with valid direct
no-attachment input (`Reminder 0`, `Blinker 0`). No fresh `.event.json` or
`.ready` appeared. The path-selection error is therefore not sufficient to
explain the current failure. The authoritative status remains a shared CREATE
Save/publication boundary under investigation; the earlier upload-loop is
evidence, but not by itself a proven current root cause after reconnection.
