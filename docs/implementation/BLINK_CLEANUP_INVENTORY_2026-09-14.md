# Blink cleanup inventory — prepared, not executed

**Date:** 2026-09-14  
**Gate:** do not delete until canonical Blink, Blink DONE, and Blink Files
pass final physical Acceptance and Production smoke tests.

## Shortcuts

| Item | Decision | Reason |
|---|---|---|
| Blink | KEEP / create canonical | final Home Screen CREATE target |
| Blink DONE | KEEP / create canonical | internal Done action |
| Blink Files | KEEP / create canonical | internal Files action |
| Blink Files Candidate — CHOOSER-ACCEPTANCE... | KEEP temporarily | only physically accepted one-file fallback |
| Blink Files | KEEP temporarily | historical working fallback |
| Blink Create Test / Stage2 WORK | KEEP temporarily | Acceptance source until clean CREATE passes |
| Blink DONE Test / BACKUP Stage2 | KEEP temporarily | Acceptance evidence and recovery |
| Blink Files Stage2 WORK / BACKUP Stage2 | KEEP temporarily | recovery/evidence |
| Blink Files Runtime Diagnostic | DELETE after cutover | proof-only diagnostic |
| Blink JSON Serialization Test / Blink Test | DELETE after cutover | proof-only tests |
| RU Fix and Начальные команды | KEEP | unrelated user utilities |

No deletion or rename is authorized at this stage.

## iCloud transport

| Root | Decision | Reason |
|---|---|---|
| Blink_Acceptance | KEEP until cutover | isolated acceptance transport |
| Blink_Production | RESERVED | must remain disabled until all gates pass |
| Blink_Feasibility | KEEP until final audit | historical fallback/evidence |
| ToPhoneView packages | DELETE only after bounded cleanup and acceptance | derived presentation data |
| canonical user attachments | KEEP | user data |

The current `Blink_Acceptance/ToMac` inventory contains these stale Acceptance
DONE pairs. KEEP temporarily, never apply, and classify before any importer or
cleanup operation:

    20260913023352-385630113.done.json + .ready
    20260913213223-646956164.done.json + .ready
    20260913213317-748777692.done.json + .ready
    20260913213646-153651294.done.json + .ready
    20260913214022-944321537.done.json + .ready

## Project

| Area | Decision | Reason |
|---|---|---|
| app/, astronomy/, tests, launchd | KEEP | source/runtime/tests |
| current contract, roadmap, plan, tree inventory | KEEP | authoritative documentation |
| historical reports | KEEP, mark historical | audit trail |
| temporary diagnostics | DELETE only if agent-created and after replacement | safe cleanup candidate |
| runtime event data | KEEP | canonical user data |

## Required final audit

Before cleanup, repeat the inventory and record exact names, paths, and why.
Delete only agent-created or explicitly approved obsolete artifacts. Preserve
the only working fallback until the production replacement is physically
accepted.
