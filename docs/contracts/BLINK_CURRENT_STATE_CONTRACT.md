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

Files one-file Acceptance passed physically. CREATE and DONE need final clean
tree verification and representative physical Acceptance under canonical names.

## Sync and release gates

After every Mac Shortcut edit: harmless real GUI edit + Save on Mac, wait for
iCloud, compare the complete iPhone Edit tree/build marker, then run or push.
Name synchronization alone is insufficient. Codex {"detail":"Bad Request"}
messages were connection/tool failures, not Shortcuts/file errors.

Acceptance requires direct CREATE, Share CREATE, DONE, one/multiple-file Files,
and one event with both independent actions. Production cutover must explicitly
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
