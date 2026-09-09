# Blink Astronomy And Native GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Blink from a JSON-only ntfy reminder watcher into a small native Mac utility that manages personal events and astronomy reminders without replacing the existing watcher sender.

**Architecture:** Keep `watcher.py` as the only scheduled push sender. Add independent personal and astronomy data sources, normalize both into the existing reminder pipeline, and keep astronomy generation separate from notification settings. Add a minimal SwiftUI app that edits JSON/config files and never sends ntfy pushes directly.

**Tech Stack:** Python standard library for watcher/data contracts, optional Skyfield/JPL ephemeris for precise astronomy generation after dependency approval, SwiftUI for native macOS GUI.

## Global Constraints

- Do not rewrite Blink from scratch.
- `watcher.py` remains the only scheduled push sender.
- SwiftUI must never send ntfy directly.
- Personal events remain backward compatible with the existing `agenda.json` event schema.
- Astronomy data generation is independent of notification enable/disable settings.
- Sunset plus moon-status-at-sunset should be one combined evening astronomy push when both are enabled.
- Personal reminders are never combined.
- Duplicate prevention must use reminder identity, not timestamp.
- `late_delivery_grace_minutes` must be 180.
- History v1 is for personal events, not five years of daily astronomy.
- Do not introduce SQLite for v1.

---

### Task 1: Multi-Source Watcher Contracts

**Files:**
- Modify: `/Users/vitaliiprotsiuk/Desktop/Blink/test_watcher.py`
- Modify: `/Users/vitaliiprotsiuk/Desktop/Blink/watcher.py`
- Modify: `/Users/vitaliiprotsiuk/Desktop/Blink/config.example.json`
- Modify: `/Users/vitaliiprotsiuk/Desktop/Blink/config.json`

**Interfaces:**
- Produces: `load_notification_events(config, agenda_path=None, astronomy_path=None, astronomy_config_path=None) -> list[dict]`
- Produces: `load_astronomy_events(path=None, settings_path=None) -> list[dict] | None`
- Produces: existing `process_due_reminders(...)` continues to accept normalized events.

- [ ] Write failing tests for two personal events at the same timestamp, personal plus astronomy at the same timestamp, duplicate prevention by identity, disabled personal, disabled astronomy, enabled astronomy, late grace 180, and malformed astronomy file isolation.
- [ ] Run `python3 -m unittest discover -s . -p 'test_*.py'` and confirm the new tests fail for missing multi-source support.
- [ ] Implement minimal normalized astronomy loader and update watcher main loop to process personal plus astronomy sources together.
- [ ] Set grace defaults to 180 in config files.
- [ ] Re-run tests until green.

### Task 2: Astronomy Data Schema And Generator Scaffold

**Files:**
- Create: `/Users/vitaliiprotsiuk/Desktop/Blink/astronomy/astronomy_config.json`
- Create: `/Users/vitaliiprotsiuk/Desktop/Blink/astronomy/astronomy_schedule.json`
- Create: `/Users/vitaliiprotsiuk/Desktop/Blink/astronomy/generate_astronomy.py`
- Create: `/Users/vitaliiprotsiuk/Desktop/Blink/astronomy/README.md`
- Modify: `/Users/vitaliiprotsiuk/Desktop/Blink/test_watcher.py`

**Interfaces:**
- Produces daily records with full supported facts independent of notification toggles.
- Watcher consumes `notifications` derived from daily records plus current settings.

- [ ] Write failing sanity tests for timezone-aware Sunnyvale config, full-data generation independent of toggles, sunset combined moon status notification, moonrise/moonset missing-day handling, and clear dependency status when Skyfield is unavailable.
- [ ] Implement a small schema and generator scaffold that refuses precise generation without approved/installed astronomy dependency.
- [ ] Keep sample schedule small and explicit for tests; do not fake five-year precision.
- [ ] Re-run tests.

### Task 3: Safe Agenda Store For GUI

**Files:**
- Create: `/Users/vitaliiprotsiuk/Desktop/Blink/app/agenda_store.py`
- Create: `/Users/vitaliiprotsiuk/Desktop/Blink/test_agenda_store.py`

**Interfaces:**
- Produces: `load_agenda_document(path) -> dict`
- Produces: `save_agenda_document_atomic(path, document) -> None`
- Produces: `upsert_event(document, event) -> dict`

- [ ] Write failing tests for preserving unknown fields, atomic save, timezone-aware start, edit start preserving event id, disable, delete with explicit call, and history/upcoming split.
- [ ] Implement minimal Python data-store layer that SwiftUI can mirror or call later.
- [ ] Re-run tests.

### Task 4: Minimal SwiftUI App Scaffold

**Files:**
- Create: `/Users/vitaliiprotsiuk/Desktop/Blink/app/BlinkApp/`

**Interfaces:**
- SwiftUI reads/writes JSON files only.
- No ntfy code exists in SwiftUI.

- [ ] Create native macOS SwiftUI skeleton for Today, Upcoming, History, Astronomy settings, and New/Edit Event.
- [ ] Implement JSON file read/write boundary carefully or prepare a Python-bridge-free Swift Codable store.
- [ ] Add manual run instructions if Xcode CLI build is unavailable.
- [ ] Verify no GUI code posts to ntfy.

### Task 5: Documentation And Verification

**Files:**
- Modify: `/Users/vitaliiprotsiuk/Desktop/Blink/README.md`
- Create or modify astronomy/app READMEs.

- [ ] Document architecture and user workflow.
- [ ] Run full tests after each substantial layer.
- [ ] Run Python compile checks.
- [ ] Verify backup exists.
- [ ] Report exact remaining risks, especially astronomy precision/dependencies and SwiftUI build status.
