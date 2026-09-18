# Blink — Product Requirements and Direction

**Authority:** this is the compact product-level requirements list for every
future agent. It complements the technical state contract and roadmap. If a
technical shortcut conflicts with the product intent below, stop and resolve
the conflict before implementing it.

## Product north star

Blink must not merely remind the user what to do. It must preserve why the
event exists, return the relevant source context at the right moment, and keep
important work visible until the user marks it `Done`.

An event may therefore own its source QR code, barcode, PDF, photo, ticket,
instruction, or other accepted file. An event without a source file remains a
valid simple event.

## Non-negotiable product architecture

```text
Mac source of truth
  → watcher scheduler/sender/blinker
  → ntfy notification transport
  → iPhone notification and Shortcuts actions
  → iCloud bounded command/file transport
```

- The Mac owns events, lifecycle, timing, and attachment ownership.
- ntfy and iCloud are transport layers, not competing databases.
- There is one scheduler and one sender.
- iPhone Shortcuts are adapters: capture, Done, and Files viewing.
- Do not add a second backend, scheduler, sender, event store, or helper
  Shortcut merely to bypass a difficult acceptance boundary.

## Three final Shortcut roles

### `Blink` / CREATE

One user-facing creation Shortcut, launched directly or from the iPhone Share
Sheet. It accepts zero or one attachment, asks for the event fields, preserves
lossless text, validates all numeric inputs as non-negative integers, and writes
one validated CREATE package to the Mac mailbox with `.ready` last.

Share Sheet behavior is deliberately **one file maximum**. A second item must
be rejected clearly. This does not limit the number of files that an already
created event may have in its attachment package.

### `Blink DONE`

An internal notification action receiving `blink-done-v1|<event-id>`. It writes
a bounded DONE command. The Mac applies it idempotently and remains the owner
of lifecycle transitions.

### `Blink Files`

An internal notification action receiving `blink-files-v1|<package-id>`. It
reads the matching iCloud Shortcuts package, filters only its files, presents a
chooser for multiple files, and opens the selected file in Quick Look. It is
read-only with respect to canonical event state.

## Required user journeys

- Share an Amazon return QR and later receive the reminder with that QR ready.
- Create from a manager's PDF and later open the same PDF from the reminder.
- Create from a ticket, parking QR, medical instruction, barcode, or school
  document and recover it without searching the original message.
- Create ordinary no-attachment tasks such as watering plants or calling Mom.
- Use several reminders plus an independent Blinker lead time.
- Keep important work active until explicit `Done`.
- Optionally receive a useful daily briefing, practical weather guidance, and
  astronomy context without turning Blink into an unrelated dashboard.

## Future context capture and browsing

The context layer should grow beyond a single shared file without changing the
event/source-of-truth model:

- **Selected text capture:** create an event from text selected on the Mac. The
  selected text is preserved as a text document attachment owned by the event,
  so the original context is still available at reminder time.
- **Phone event-folder browsing:** from the iPhone, allow the user to browse
  event folders using their real human-readable names and see the attachments
  belonging to each event. Browsing must remain read-only and must not bypass
  the Mac source of truth.
- **Broader document support:** support a substantially wider set of document
  and media types than the initial image/PDF/Word-oriented set. New types must
  preserve their original bytes and display/open behavior where iOS and macOS
  support it; unsupported types must fail clearly rather than being silently
  converted or discarded.

These requirements are future product work. They do not authorize a second
cloud file database, uncontrolled recursive iCloud browser, or replacement of
the existing one-file CREATE Share Sheet contract.

## Development rules

- Simulators are the primary development/test harness for CREATE, DONE, and
  Files, but never runtime dependencies.
- Model the exact semantic blocks present in physical Shortcuts.
- Use: Apple instructions → complete physical tree/oracle → simulator/profile
  → focused/full tests → minimal reversible Shortcut edit → GUI save/sync →
  iPhone tree verification → Apple-specific acceptance.
- Do not judge a Shortcut only by action count; accepted validation and
  lossless user behavior are part of the product contract.
- Keep `Blink Create Test` untouched as source/oracle until Production is
  accepted.
- Do not delete whole Shortcut objects before final physical acceptance and
  Production smoke; preserve the accepted source and a rollback path.
- After each major accepted block, commit and push a coherent Git checkpoint.

## Agreed delivery order

```text
CREATE accepted
  → DONE accepted
  → Files accepted
  → Combined acceptance
  → restore/accept Mac Start blinking
  → investigate Same-ID stale/future push semantics
  → Production cutover
  → Production smoke
  → one-icon Blink phone UX
  → final four-area cleanup
  → Today Morning Briefing
  → WiZ lamp adapter
  → bounded transport hardening
```

The Same-ID question is intentionally an investigation/open decision before
Production, not an automatic implementation mandate. Do not change queue
semantics until the behavior is understood and the product decision is made.

## Explicit open items to preserve

These observations must not be lost or silently reclassified:

1. **Mac editor Blinker control:** the Blinker control disappeared from the
   editor. Restore it later without changing Shortcut or transport contracts.
2. **Mac menu-bar indicators:** two yellow Blink circles appear near the clock;
   one can remain lit while Blink is off. Identify ownership and lifecycle
   later before changing UI/process behavior.
3. **Same-ID notification freshness:** after an event edit, determine whether
   old queued pushes may coexist with new current-state pushes or whether the
   queue must resolve only the latest state. Decide before Production.
4. **Files physical boundary:** canonical `Blink Files` must be physically
   proven with a fresh multi-file JPEG+PDF notification; old delivered actions
   are immutable evidence and must not be confused with new generation.
5. **Mac contextual capture:** add future Finder right-click creation from a
   supported file and creation from a supported clipboard object. Both must
   enter the existing one-attachment CREATE flow, not create a second event
   architecture.
6. **Today list spacing:** investigate why a large empty vertical gap can
   appear between event rows/cards when only a small number of events is
   present. The final layout should use space proportionally to actual content
   while preserving intentional grouping such as Active and Today's Events.
7. **Weather current temperature:** add a `Now` temperature value below or
   alongside the daily maximum/minimum, matching the existing `Now` humidity
   presentation. It must represent the temperature at the briefing/data
   timestamp, not another daily high/low value.
8. **Astronomy checkbox filtering:** investigate and fix the apparent case
   where most Astronomy event checkboxes are disabled but the delivered
   astronomy briefing still contains the full set of events. Disabled
   categories must not appear in the generated briefing or scheduled
   notifications.
9. **Briefing schedule/deduplication:** investigate the observed behavior where
   an Astronomy briefing configured for 06:53 arrived at 07:07 after the Mac
   became available, followed later by an unexpected Weather briefing at 09:39.
   Verify wake/startup catch-up, configured times, enable flags, queue
   ownership, and per-day deduplication. A catch-up briefing must not create an
   unrelated second briefing later in the day.

## Final library state

After Production cutover and successful smoke, the user's Shortcut library
should retain exactly `Blink`, `Blink DONE`, and `Blink Files` as Blink's
product objects, plus unrelated/system Shortcuts. Historical source, rollback,
and evidence belong in Git, contracts, and exports rather than permanent
laboratory objects.
