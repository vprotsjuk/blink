# Blink — current state contract

**Snapshot:** 2026-09-14
**Authority:** this file and ROADMAP. Historical reports explain how a problem
was found but never override this contract.

## Ownership

```text
SwiftUI GUI -> local JSON and attachment folders -> watcher.py -> ntfy -> iPhone
```

- Mac agenda.json and Mac-owned attachment folders are the source of truth.
- watcher.py is the only push sender and long-running delivery process.
- iPhone Shortcuts are transport adapters; they do not mutate canonical state.
- Do not add a second sender, scheduler, cloud backend, SQLite source of truth,
  or parallel watcher.

## Event and timing contract

Required event fields: id, title, start, reminders_minutes_before, enabled.
start contains an explicit UTC offset. description is optional and preserves
newlines. Attachments belong to event_data/attachments/<event-id>/; event JSON
stores metadata, not bytes or absolute paths.

Lifecycle: Upcoming -> Active -> Done -> History. Done preserves the original
start, clears attention, and is idempotent. Disabling changes delivery
eligibility only. History is frozen and can only be duplicated or deleted.

Reminders are non-negative integer minutes and may contain multiple values.
Presets are 1440, 720, 300, 60, 30, 10, 5, 0; 0 means At time. Custom values
reject fractions, negatives, and invalid text. [30, 0] is a creation default
only; clearing all reminders must never silently restore it.

Blinker is independent from reminders and uses one non-negative integer minute
offset. If the Mac UI exposes a custom blinker, the phone mirrors it.
The active CREATE candidate uses native numeric validation: it rounds the
number to Integer and requires equality with the original value, combined with
a native `>= 0` check. Thus fractions, letters, signs, and mixed symbols cannot
be silently coerced into a valid minute value, and the validation is not
locale-sensitive.

Lead-time availability constrains new and duplicated events. When editing an
existing non-frozen event, the intended contract is that the Mac editor keeps
old reminder/blinker values editable even after their lead time has elapsed, so
the user can correct them and save the same event ID. This is not currently
product-accepted: live evidence shows a stale `1 day before` Blinker can leave
`Start blinking` disabled and block replacement with a future `60 min before`.
Final acceptance must use that exact live UI scenario after Shortcut
convergence. History remains frozen and cannot be edited.

## Transport contract

CREATE accepts v1/v2 and at most one incoming attachment. Native Shortcut
transport IDs are <yyyyMMddHHmmss>-<9-digit-random>, with random range
100000000..999999999. It is not an EventID or event time.

DONE input: `blink-done-v1|<event-id>`. It writes the canonical DONE
package and writes .ready last. Replays/no-ops are silent.

FILES input: `blink-files-v1|<package-id>`. Mac stages a flat integrity
package and atomic package-scoped ToPhoneView/<package-id>/ containing only
safe original basenames. Source ordering is deterministic (__01__, __02__).
Manifest, .ready, transport prefixes, metadata, and unrelated packages are
excluded.

ntfy actions are separate and ordered `Done; Files`. Done carries
EventID and targets Blink DONE. Files carries PackageID and targets Blink Files.
URLs are percent-encoded; clear=true is not used.

## Shortcut trees

See docs/implementation/BLINK_SHORTCUT_TREES_2026-09-14.md for evidence.

```text
Blink
  direct launch or Share input
  -> validate/normalize fields
  -> build one CREATE_EVENT package
  -> write Acceptance/ToMac, later Production/ToMac
  -> write .ready last

Blink DONE
  receive blink-done-v1|<event-id>
  -> write DONE package to ToMac
  -> write .ready last

Blink Files
  receive blink-files-v1|<package-id>
  -> get package-scoped ToPhoneView folder
  -> Get Contents of Folder
  -> Choose from List
  -> Show Selected Item in Quick Look
```

The active CREATE candidate must reject Share input with more than one item
before `First Item` is selected. Its current Gate A implementation is
`Count Items in Shortcut Input` → `If Count > 1` → clear alert → `Stop this
shortcut`; the single-item and direct-launch paths remain unchanged. The
Blinker contract is still independently gated: its Shortcut input must reject
fractions, letters, negatives, and malformed text rather than coercing them.

Files one-file Acceptance passed physically. CREATE Gate A (Share `>1`) and
Gate B (integer Blinker) are implemented and programmatically verified. Gate
B's fractional rejection has now also been physically exercised on iPhone
(`1.5` stopped with no new payload or `.ready`), but full CREATE product
Acceptance still requires the representative direct, single-attachment,
multi-item, and text-preservation cases. DONE needs final clean-tree verification and
representative physical Acceptance under its canonical name. The Mac editor
Blinker regression remains an independent CURRENT gate.

The known-good CREATE transport was physically re-established on 2026-09-15:
untouched `Blink Create Test` produced fresh
`20260915021144-935344778.event.json` plus `.ready` in the exact
`Blink_Acceptance/ToMac` mailbox. The payload preserved explicit `-07:00`
time, Reminder `[0]`, Blinker `17`, and the required 9-digit suffix. This
proves the transport and iCloud materialization path are currently available;
the remaining no-payload result is candidate-only and must be debugged against
that oracle.

## Fast CREATE logic oracle

`app/create_shortcut_simulator.py` and
`test_create_shortcut_simulator.py` model the pure logical portion of the
CREATE Shortcut: validation, variables, branches, v1 JSON, transport names,
and output ordering. They intentionally do not model Apple-specific behavior
such as Share Sheet delivery, iCloud sync, Mirroring, Quick Look, or ntfy.
Those boundaries still require the real Shortcut and physical acceptance.

These simulators are the primary development/test harness for the three
Shortcut roles, but are never runtime dependencies. The required sequence is:
simulator/profile verification → minimal physical Shortcut edit →
Apple-specific acceptance. The gray Mac `Start blinking` state remains a real
open UI bug and is not cleared by passing model/unit tests.

The simulator boundary is exactly the three product Shortcuts, not the current
development inventory:

| Product role | Physical oracle/profile | Simulator boundary |
|---|---|---|
| `Blink` | `Blink Create Test`; candidate `Blink Create Stage2 WORK` | input/attachment branch, prompts, validation, variables, JSON, filenames, `.ready` order |
| `Blink DONE` | `Blink DONE Test` | `blink-done-v1|<event-id>` validation, command JSON, filenames, `.ready` order; no event lookup/update |
| `Blink Files` | accepted `Blink Files` / candidate `Blink Files Stage2 VIEW TEST` | PackageID validation, `ToPhoneView/<PackageID>`, folder contents, chooser, Quick Look selection |

Test/Stage2/WORK/Candidate/BACKUP/Invoke/Diagnostic names are comparison
profiles or historical evidence only. They do not create additional product
models. Trace entries in the simulator name the corresponding physical
Shortcut action groups; Apple-only delivery and presentation remain physical
gates.

## Open question — same-ID notification freshness (must resolve before Production)

An event edited without changing its Event ID should conceptually keep that ID.
The required behavior after an edit is intentionally unresolved: if the Mac
was asleep, already queued ntfy messages from the old snapshot may perhaps
continue alongside new pushes for the same Event ID, or future delivery may be
required to resolve only the current canonical state. This must be investigated
and explicitly decided before Production cutover. Until then, do not change
the scheduler or queue; record evidence and define a regression matrix first.

The historical `20260914222838-949257520` payload (Unicode title `Еуые`,
Blinker `17`) is not evidence for the later user-labelled `Test 17` run; no
new payload was found for that run. A fresh valid CREATE run must be correlated
to a newly written `.event.json` and `.ready` pair before the direct path is
marked physically accepted.

## Sync and release gates

After every Mac Shortcut edit: harmless real GUI edit + Save on Mac, wait for
iCloud, compare the complete iPhone Edit tree/build marker, then run or push.
Name synchronization alone is insufficient. Codex {"detail":"Bad Request"}
messages were connection/tool failures, not Shortcuts/file errors.

Acceptance requires direct CREATE, Share CREATE, DONE, one/multiple-file Files,
and one event with both independent actions. The final physical sequence is
CREATE accepted → DONE accepted → Files accepted → Combined accepted → gray
Mac `Start blinking` fixed/live-verified → same-ID freshness investigated and
decided → Production cutover. Production cutover must explicitly
migrate ToMac/ToPhone/ToPhoneView, replace candidate names with Blink, Blink
DONE, Blink Files, perform GUI touch and iPhone tree verification, smoke test,
then enable production controls.

## Future and cleanup

Today Morning Briefing remains a core feature: optional persistent toggle,
every applicable Today event, importance, title, optional description, local
date/time, dedupe, empty-day/wake/timezone rules, Weather/Astronomy coexistence,
using the existing watcher sender only.

One Home Screen icon Blink is the final UX. Removing the intermediate Shortcuts
screen is optional and deferred. The RGB lamp is the last stage and must use a
separate fail-safe adapter, not a second sender or scheduler.

Before cleanup inventory Shortcuts, iCloud, and project/runtime as
KEEP / DELETE / WHY. Delete only agent-created or explicitly approved obsolete
artifacts after replacement acceptance; never delete user data, source, tests,
runtime state, authoritative docs, or the only fallback.
