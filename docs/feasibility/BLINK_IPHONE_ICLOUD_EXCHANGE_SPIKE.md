# Blink ↔ iPhone private iCloud exchange — feasibility / robustness spike

**Status:** feasibility only; no production feature implemented.
**Date:** 2026-09-10
**Project:** `/Users/vitaliiprotsiuk/Desktop/Blink`

## Safety boundary

This spike does not modify `watcher.py`, `agenda.json`, production SwiftUI
behavior, ntfy configuration, or any user folders outside the dedicated test
area. It does not create public iCloud links, access Photos/Documents, or use
HTTP/ntfy for file exchange. The production source of truth remains the Mac's
local Blink JSON and attachment folders.

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

The test area is intentionally outside the Blink repository:

```text
iCloud Drive/Shortcuts/Blink_Feasibility/
  ToMac/
  ToPhone/
```

The actual macOS filesystem root is recorded in the test results below; no
symbolic links are used.

## Part 1 — Mac iCloud filesystem

| Check | Result |
|---|---|
| macOS version | recorded by the spike command below |
| iCloud Drive filesystem path | recorded by the spike command below |
| `Shortcuts` availability | created only as the dedicated test area |
| ordinary filesystem access | create/read/rename/delete/subdirectory/Unicode/space tests |
| atomic temp → rename | tested inside `ToMac` |
| `shortcuts` CLI | present; run/list/view/sign only; no create/import subcommand |

The exact command output and pass/fail matrix are appended to this report after
the bounded test run.

## Part 2 — mailbox package format

The tested package shape is deliberately flat and uses a final marker:

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

The future Mac reader must ignore incomplete packages until `.ready` exists,
validate the JSON and all listed files, process a package once, and move or mark
it only after successful processing. No per-event dynamic directories are
needed.

## Part 3 — Shortcut design under test

One future Shortcut (`Blink Test`) has two input modes:

1. Share Sheet: accept at most one File/PDF/Image, then ask Title, Description,
   Event Date/Time, Priority, and Blink Date/Time. Write JSON, then attachment,
   then `.ready`.
2. No Input: ask the same fields without an attachment and write JSON, then
   `.ready`.

The Shortcut must use a fixed private iCloud destination without asking the
destination on every run. The spike cannot validate this iPhone-only behavior;
the exact manual checklist is below.

## Part 4 — required manual iPhone validation

The owner must test on a real iPhone:

1. `Blink Test` appears in Files' Share Sheet.
2. A PDF is accepted.
3. An explicitly shared photo/image is accepted.
4. Multiple Share Sheet inputs are rejected or reduced to one with a clear rule.
5. Direct Home Screen/Shortcuts launch works with no attachment.
6. All five event fields are collected.
7. The Shortcut saves to the fixed private iCloud folder without destination
   selection each time. If iOS forces a picker, record this as an architecture
   blocker; do not add a workaround before review.
8. The Mac sees the JSON/attachment/ready package.

## Part 5 — Mac → iPhone viewing package

The future `Blink Files` Shortcut should read only `ToPhone`, select files by
`occurrence_id`, ignore `.manifest.json` and `.ready`, and open one file directly
or present a list when there are two or more. Quick Look/standard preview is
enough. No public links, HTTP, or ntfy are involved.

## Findings and recommendation

The flat package plus final `.ready` marker is feasible with ordinary filesystem
operations and avoids complicated directory-sync semantics. The main unknown is
not Mac storage; it is whether iOS Shortcuts can save to a fixed private iCloud
subfolder without presenting a destination picker. Production Blink must remain
unchanged until the owner completes that iPhone test and accepts the result.

## Reproducibility evidence

The bounded filesystem test creates only `AI_TEST_*` files under the dedicated
`Blink_Feasibility` area and removes only those files. The mailbox directories
remain available for the owner's manual Shortcut test. No production runtime
files are part of this spike.

