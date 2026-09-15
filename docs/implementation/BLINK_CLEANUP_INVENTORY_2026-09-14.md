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

## Mac Shortcuts recheck before cleanup

The Mac Shortcuts GUI recheck at the current checkpoint shows 26 entries. The
exact agent-created cleanup candidates are:

| Shortcut | Current decision | Why |
|---|---|---|
| `Blink Nested Invoke TEST 20260915` | DELETE after explicit GUI confirmation | concluded nested-invoke experiment; no accepted source |
| `Blink Files VIEW INVOKE TEST` | DELETE after explicit GUI confirmation | concluded helper experiment; no accepted source |
| `Blink Files Acceptance DYNAMIC 20260915` | DELETE after explicit GUI confirmation | superseded 47-action duplicate |
| `Blink Files Acceptance PACKAGEPATH 20260916` | DELETE after explicit GUI confirmation | superseded 47-action duplicate |
| `Blink Files Acceptance MULTI 20260915` | DELETE after explicit GUI confirmation | empty concluded experiment |
| `Blink Files Acceptance FIXED INVOKE 20260915` | DELETE after explicit GUI confirmation | empty concluded experiment |
| `Blink Files Runtime Diagnostic — DIRECT-NAME-ACCEPTANCE-20260913-A \| GUI-SAVED` | DELETE after explicit GUI confirmation | proof-only diagnostic |
| `Blink Test` | DELETE after explicit GUI confirmation | obsolete one-action test |
| `Blink JSON Serialization Test` | DELETE after explicit GUI confirmation | proof-only serialization test |
| `Blink Files Candidate — CHOOSER-ACCEPTANCE-20260913-A \| GUI-SAVED 1` | DELETE after explicit GUI confirmation | duplicate of accepted candidate |

Keep unchanged until final Production acceptance: `Blink Create Test`,
`Blink Create Stage2 WORK`, `Blink Create Test BACKUP`, `Blink DONE Test`,
`Blink DONE Test BACKUP Stage2`, `Blink Files Stage2 VIEW TEST`, `Blink Files
Stage2 WORK`, `Blink Files`, `Blink Files BACKUP Stage2`, the accepted Files
candidate(s), `RU Fix (Selected Text)`, and all four Apple starter shortcuts.

This table is an inventory, not deletion authorization. GUI deletion is a
separate action-time confirmation with the accepted source and at least one
flow fallback preserved.

## iCloud transport

| Root | Decision | Reason |
|---|---|---|
| Blink_Acceptance | KEEP until cutover | isolated acceptance transport |
| Blink_Production | RESERVED | must remain disabled until all gates pass |
| Blink_Feasibility | KEEP until final audit | historical fallback/evidence |
| ToPhoneView packages | DELETE only after bounded cleanup and acceptance | derived presentation data |
| canonical user attachments | KEEP | user data |

### Full iCloud transport-root audit — 2026-09-15

The private Shortcuts container currently contains these distinct transport
locations; they must not be conflated:

| Exact location | Observed role | Current disposition |
|---|---|---|
| `Blink_Acceptance/ToMac/` | current folder-based CREATE/DONE inbox; five stale DONE pairs plus the `Еуые` CREATE pair | KEEP; do not delete or process blindly |
| `Blink_Acceptance/ToMac.json` | legacy single-file CREATE artifact from the earlier path | KEEP as historical evidence until final audit |
| `Blink_Acceptance/Archive/Phase5-20260912211629/` | ten complete historical CREATE packages, each with `.ready` | KEEP as reversible acceptance evidence |
| `Blink_Acceptance/SerializationProof/` | serializer proofs; one intentionally has no `.ready` | KEEP as proof-only evidence |
| `Blink_Feasibility/ToMac/` | older bare-ID CREATE/DONE experiments, including successful packages and malformed zero-byte attachment case | KEEP as historical fallback/evidence; never current target |
| `Blink_Feasibility/ToMac/Blink_Acceptance/` | nested legacy DONE artifact | KEEP as historical evidence |
| `Blink_Feasibility/ToPhone/` | older Files/manual material | KEEP until final audit |
| `.Trash/Blink_Feasibility/{ToMac,ToPhone}/` | previously trashed feasibility material | do not restore or purge in this phase |

No `Blink_Production/ToMac` directory was found. The exact current Shortcuts
container reports `caught-up` with no pending item in `brctl status`; this
supports treating the current fresh-run failure as a Save/publication-boundary
investigation, not as proof that one of these historical roots is active.

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
