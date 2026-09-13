# Blink Stage 2 ToPhone Attachment Viewing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement event-specific iPhone attachment viewing through deterministic, safe ToPhone snapshots and a canonical ntfy Files action.

**Architecture:** Add a pure package/action identity layer and an atomic `app/to_phone_store.py` that snapshots canonical event attachments into a flat ToPhone package. Integrate snapshot preparation with direct sends and remote queue reconciliation; queued packages remain mutable until due, then become immutable in a local ledger and expire through bounded cleanup. Extend the existing notification formatter so direct and queued payloads use the same percent-encoded `Blink Files` action.

**Tech Stack:** Python 3, `pathlib`, `hashlib`, `json`, `urllib.parse.quote/urlencode`, existing `watcher.py` and `app/ntfy_schedule.py`, pytest, macOS private Shortcuts iCloud filesystem.

## Global Constraints

- `event_data/attachments/<owner-id>/` remains the source of truth.
- ToPhone is transient transport only; no phone-to-Mac round trip and no public links.
- Production mailbox remains disabled; files staging is opt-in via `BLINK_NTFY_FILES_ACTION_ENABLED=1` and explicit `BLINK_TO_PHONE_ROOT`.
- DONE, CREATE, Weather, Astronomy, SwiftUI, and unrelated Shortcuts contracts remain unchanged.
- Package IDs are deterministic `blink-files-v1-<sha256-prefix>` values from `(event_id, effective_start, offset)`.
- Package publication is atomic and `.ready` is written last; invalid/foreign/path-traversal files fail closed.
- Queue reconciliation refreshes queued snapshots; delivered snapshots are immutable until bounded TTL cleanup.
- No `clear=true`, no extra Home Screen icon, and no Stage 3 work.
- Use the existing Python test suite and preserve all prior passing tests.

---

### Task 1: Add failing package-store and identity tests

**Files:**
- Create: `test_to_phone_store.py`
- Modify: `test_notification_format.py`
- Modify: `test_ntfy_schedule.py`

**Interfaces:**
- `app.to_phone_store.package_id(event, offset_minutes) -> str`
- `app.to_phone_store.prepare_snapshot(root, event, offset_minutes, *, now, delivered=False) -> SnapshotResult`
- `app.to_phone_store.mark_delivered(root, package_id, delivered_at) -> None`
- `app.to_phone_store.cleanup(root, now, ttl_seconds) -> list[str]`
- `app.notification_format.build_files_action(package_id, *, shortcut_name="Blink Files") -> str`

- [ ] **Step 1: Write failing tests** for deterministic safe IDs, manifest/attachment/ready shape, traversal rejection, duplicate names, source exclusions, no-file result, idempotent regeneration, delivered immutability, cleanup TTL, and `%20` Files URL encoding.

- [ ] **Step 2: Run the focused tests**

```bash
pytest -q test_to_phone_store.py test_notification_format.py test_ntfy_schedule.py
```

Expected: new tests fail because the package store and Files action do not yet exist.

### Task 2: Implement the atomic ToPhone package store

**Files:**
- Create: `app/to_phone_store.py`

**Interfaces:**
- `SnapshotResult`: dataclass with `package_id: str`, `ready: bool`, `has_files: bool`, `manifest: dict[str, Any] | None`, `source_hash: str | None`.
- `package_id(event, offset_minutes) -> str` hashes `event_id|effective_start.isoformat()|offset_minutes`.
- `prepare_snapshot(root, event, offset_minutes, *, now, delivered=False) -> SnapshotResult` writes manifest and ordinal files through temp names and writes `<package_id>.ready` last.
- `mark_delivered(root, package_id, delivered_at) -> None` records immutable state in `<root.parent>/to_phone_state.json` using atomic JSON replacement.
- `cleanup(root, now, ttl_seconds) -> list[str]` removes only packages recorded as delivered/orphaned past TTL and never current queued package IDs.
- `validate_package(root, package_id) -> dict[str, Any] | None` enforces exact stem ownership, safe package regex, manifest schema, file hashes, and ready marker.

- [ ] **Step 1: Implement strict validation helpers** for package IDs, basenames, regular non-hidden source files, and exact package stems.
- [ ] **Step 2: Implement source manifest hashing** over sorted visible regular files, preserving original display names and deterministic ordinals.
- [ ] **Step 3: Implement atomic regeneration** with `root.mkdir`, per-file temporary copies, flushed manifest, `os.replace`, and final ready marker; preserve the last complete package on failure.
- [ ] **Step 4: Implement local delivered ledger and bounded cleanup** with atomic writes and no arbitrary-folder scanning.
- [ ] **Step 5: Run package-store tests**

```bash
pytest -q test_to_phone_store.py
```

Expected: PASS.

### Task 3: Add the canonical Files action and payload eligibility

**Files:**
- Modify: `app/notification_format.py`
- Modify: `test_notification_format.py`

**Interfaces:**
- `FILES_ACTION_VERSION = "blink-files-v1"`.
- `files_action_enabled(config: dict[str, Any] | None = None) -> bool` reads `BLINK_NTFY_FILES_ACTION_ENABLED` and defaults false.
- `build_files_action(package_id: str, *, shortcut_name: str = "Blink Files") -> str` returns `view, Files, shortcuts://run-shortcut?...` using `urlencode(..., quote_via=quote)` and input `blink-files-v1|<package_id>`.
- `build_event_payload(config, event, offset_minutes, *, files_package_id: str | None = None) -> dict[str, Any]` adds Files only when enabled, personal, unfinished, and package ID is supplied; existing DONE logic remains intact.

- [ ] **Step 1: Extend failing tests** for no-file/source exclusions, encoded spaces and pipe, clear absence, and DONE+Files coexistence.
- [ ] **Step 2: Implement the pure Files builder** and optional payload parameter without changing existing call behavior.
- [ ] **Step 3: Run notification tests**

```bash
pytest -q test_notification_format.py
```

Expected: PASS.

### Task 4: Integrate snapshots into direct notification sends

**Files:**
- Modify: `watcher.py` near `send_ntfy_notification`
- Modify: `test_watcher.py`

**Interfaces:**
- `_to_phone_root() -> Path | None` resolves only an explicit `BLINK_TO_PHONE_ROOT` when Files staging is enabled.
- `_prepare_files_package(event, offset_minutes, *, delivered=False) -> str | None` returns the deterministic package ID after successful preparation, or `None` when ineligible/unavailable.
- `send_ntfy_notification(event, config, offset_minutes, ...)` prepares a current package before building the payload, sends the canonical action, and marks the package delivered only after accepted ntfy response.

- [ ] **Step 1: Add failing watcher tests** for one eligible direct send, no-file/source exclusion, package creation before request, direct/queued action equality, and failed-send retryability.
- [ ] **Step 2: Implement opt-in root resolution and direct-send preparation** while leaving mailbox flags untouched.
- [ ] **Step 3: Mark accepted direct sends immutable and run watcher tests**

```bash
pytest -q test_watcher.py
```

Expected: PASS.

### Task 5: Integrate snapshots and stale-queue reconciliation

**Files:**
- Modify: `app/ntfy_schedule.py`
- Modify: `watcher.py` remote reconciliation/scheduled send paths
- Modify: `test_ntfy_schedule.py`

**Interfaces:**
- `build_desired_queue(..., files_package_for: Callable[[dict[str, Any], int], str | None] | None = None)` passes a deterministic package ID to `build_event_payload` for eligible personal reminders.
- `reconcile(...)` keeps existing queue identity/dedupe semantics and exposes matured sequence IDs for watcher-side `mark_delivered` synchronization without changing ntfy API behavior.
- Queued reconciliation calls snapshot preparation every cycle; attachment mutations replace the same package atomically, while removal of the last file removes the Files action and changes payload hash.

- [ ] **Step 1: Add failing tests** for queued package creation, mutation refresh before due, same action/hash identity, payload hash change when Files disappears, matured immutability, duplicate queue dedupe, and Weather/Astronomy exclusion.
- [ ] **Step 2: Implement callback-based package preparation and matured delivery synchronization**.
- [ ] **Step 3: Run schedule tests**

```bash
pytest -q test_ntfy_schedule.py
```

Expected: PASS.

### Task 6: Document and evolve the Blink Files Shortcut contract

**Files:**
- Modify: `docs/implementation/BLINK_MAILBOX_IMPLEMENTATION_REPORT.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`
- Modify: `docs/HANDOFF.md`
- Modify: `CODEX_NEXT_THREAD_PROMPT.md`
- Modify: `docs/implementation/BLINK_REMAINING_ROADMAP.md`

**Interfaces:**
- Document `BLINK_TO_PHONE_ROOT`, `BLINK_NTFY_FILES_ACTION_ENABLED`, package filenames, manifest fields, input `blink-files-v1|<package-id>`, one-file/multi-file behavior, queued/delivered snapshot policy, TTL cleanup, and the manual `Blink Files` Shortcut update/acceptance checkpoint.
- Preserve DONE input, `clear=true` OPEN, production mailbox OFF, and Stage 3 as not started.

- [ ] **Step 1: Update each document only where current Stage 2 behavior/contracts belong.**
- [ ] **Step 2: Verify no stale statement claims Stage 2 is complete before physical iPhone acceptance.**

### Task 7: Full verification and controlled acceptance preparation

**Files:**
- Modify: `docs/implementation/BLINK_MAILBOX_IMPLEMENTATION_REPORT.md` with verification results only.

- [ ] **Step 1: Run the complete Python suite and focused suites**

```bash
pytest -q
pytest -q test_attachment_store.py test_mailbox_importer.py test_notification_format.py test_ntfy_schedule.py test_watcher.py test_to_phone_store.py
```

- [ ] **Step 2: Run compile, diff, and watcher health checks**

```bash
python3 -m compileall -q app watcher.py *.py
git diff --check
./status_watcher.command
```

- [ ] **Step 3: Create and verify only the clean acceptance ToPhone folder** under the private Shortcuts container; do not touch feasibility or production ToMac.
- [ ] **Step 4: Record exact package/action and stop for the single unavoidable physical iPhone `Files` tap.** Stage 2 remains CURRENT until the owner confirms the tap.

### Task 8: Commit the coherent Stage 2 Mac-side block

- [ ] **Step 1: Review `git diff`, status, tests, and roadmap markers.**
- [ ] **Step 2: Commit**

```bash
git add app/to_phone_store.py app/notification_format.py app/ntfy_schedule.py watcher.py test_*.py docs CODEX_NEXT_THREAD_PROMPT.md
git commit -m "feat: add event-specific ToPhone attachment snapshots"
```

- [ ] **Step 3: Report commit, exact roadmap `[DONE] / [CURRENT] / [REMAINING]`, tests, mailbox status, and any required iPhone tap.**
