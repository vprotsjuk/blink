# CREATE Logic Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fast, pure-Python simulator for the logical CREATE contract so validation and serialization cases can be checked without occupying Shortcuts or iPhone Mirroring.

**Architecture:** The simulator is an isolated pure function. It receives normalized test inputs plus raw user-facing numeric strings, validates them using the accepted CREATE contract, and returns either a structured rejection or the payload and transport filenames that the Shortcut is expected to produce. It does not write iCloud files, run the watcher, or replace Apple-specific acceptance tests.

**Tech Stack:** Python standard library (`dataclasses`, `datetime`, `json`, `re`, `unittest`); existing repository test runner.

## Global Constraints

- Preserve Title required/nonblank behavior and lossless Description text.
- Accept only non-negative integer Reminder and Blinker values; never round or coerce malformed input.
- Preserve explicit timezone offsets and the `yyyyMMddHHmmss-<9-digit-random>` transport ID contract.
- Accept direct launch with no attachment and at most one supported attachment.
- Do not modify Shortcut objects, watcher behavior, scheduling, or production architecture.
- Keep the simulator as a test oracle, not as a second Blink implementation.

---

### Task 1: Define the simulator behavior matrix

**Files:**
- Create: `test_create_shortcut_simulator.py`

- [x] Write tests for valid direct input, Unicode/multiline text, reminders, blinker values, attachments, transport naming, and all invalid cases.
- [x] Run `python3 -m unittest -q test_create_shortcut_simulator.py` and confirm the expected import/implementation failure.

### Task 2: Implement pure CREATE simulation

**Files:**
- Create: `app/create_shortcut_simulator.py`
- Test: `test_create_shortcut_simulator.py`

- [x] Implement strict validation and deterministic result objects.
- [x] Implement v1 payload construction without sanitizing normal text.
- [x] Implement output filenames and attachment metadata without filesystem writes.
- [x] Run the focused test file, then the full unittest suite.

### Task 3: Record the deferred same-ID snapshot question

**Files:**
- Modify: `docs/implementation/BLINK_REMAINING_ROADMAP.md`
- Modify: `docs/contracts/BLINK_CURRENT_STATE_CONTRACT.md`

- [x] Record that future push notifications for an unchanged Event ID should be evaluated against current event state, while stale queued snapshots remain an open architectural question.
- [x] Explicitly defer queue/scheduler changes until a dedicated investigation.

### Task 4: Verify and hand off

**Files:**
- Modify: `docs/superpowers/plans/2026-09-15-create-logic-simulator.md`

- [x] Run focused tests, full unittest suite, `py_compile`, and `git diff --check`.
- [x] Confirm no Shortcut or iCloud file was changed by this block.
- [x] Record remaining Apple-specific checks for the existing CREATE acceptance plan.
