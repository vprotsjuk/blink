# Active Attention UI Design

## Goal

Make unfinished enabled events visually unmistakable after their start time,
without changing their lifecycle, notification scheduling, JSON schema, or
attention outputs.

## Approved UX

- A personal event in `snapshot.active` continues to demand attention until
  `Done`.
- Only the date/title/description portion of its app row pulses. The colored
  priority circle remains solid so the severity is legible throughout.
- The `Today` tab title pulses whenever `snapshot.active` is non-empty, even
  while another tab is selected.
- State toggle text is `On` for enabled and `Off` for disabled. It remains a
  toggle, never a completion action.
- Disabled rows dim their text/date content while retaining a fully saturated
  priority circle and usable controls.

## Boundaries

- This is a SwiftUI presentation change in `ContentView.swift`.
- `EventSnapshot.active` remains the sole lifecycle authority.
- No watcher, Python sender, ntfy payload, persisted event fields, or
  attention-manager behavior is changed.

## Verification

- Swift UI source-contract tests prove the controls and pulse wiring exist.
- Existing lifecycle tests continue to prove `Done`, `On/Off`, History, and
  attention classification behavior.
- The installed app is closed and relaunched from `Blink.app` after the
  release build is copied into the bundle.
