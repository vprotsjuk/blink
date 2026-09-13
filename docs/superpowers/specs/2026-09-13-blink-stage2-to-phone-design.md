# Blink Stage 2 — event-specific iPhone attachment viewing

**Date:** 2026-09-13  
**Status:** Approved; Mac-side implementation complete, physical iPhone acceptance pending

## Goal

Add a production-capable `Files` notification action for eligible personal
events that have attachments. The action opens only the attachments belonging
to the reminder that produced the notification. One file opens directly in
Quick Look; multiple files are presented to the existing `Blink Files`
Shortcut chooser. Weather, Astronomy, service, and system notifications never
gain this action.

## Boundaries

```text
Blink local event JSON + canonical attachment files
        -> watcher.py / ntfy
        -> private iCloud Shortcuts ToPhone transport
        -> iPhone Blink Files Shortcut / Quick Look
```

- `event_data/attachments/<owner-id>/` remains the source of truth.
- `ToPhone` is a transient, Mac-written transport cache only; it is never a
  database and never a source for event metadata.
- Attachment bytes never travel through ntfy and no public link is created.
- No phone-to-Mac round trip is introduced to refresh files.
- DONE, CREATE, Weather, Astronomy, mailbox import, SwiftUI, and Shortcuts
  unrelated to `Blink Files` retain their existing contracts.
- The production mailbox remains disabled. Files staging is opt-in for
  controlled acceptance through `BLINK_NTFY_FILES_ACTION_ENABLED=1` and an
  explicit `BLINK_TO_PHONE_ROOT`; neither setting is persisted in production by
  this stage.
- No extra Home Screen icon is added. The final single `Blink` icon remains a
  later production-cutover requirement.

## Snapshot-per-reminder architecture

Each reminder has one deterministic package identity derived from its stable
reminder key (`event_id`, effective occurrence start, and reminder offset), not
from attachment content or a wall-clock timestamp. The package ID is a safe
`blink-files-v1-<sha256-prefix>` value. Retries and queue reconciliation
therefore address the same package instead of creating unbounded duplicates.

Before a direct send or a queue scheduling attempt, the Mac computes the
current canonical attachment manifest and stages a complete package. The ntfy
payload is then built by the same canonical action builder for both direct and
queued paths and carries that package ID.

### Queued and delayed reminders

An item whose ntfy delivery time is still in the future is mutable. Every queue
reconciliation re-reads the canonical attachment manifest and safely
regenerates the same package ID when bytes, names, or membership changed. A
changed attachment set also changes the payload hash when the presence of the
Files action changes, so ordinary queue cancellation/rescheduling remains the
existing source of truth. If the package ID and action are unchanged, only the
package contents are replaced atomically; the queued notification still points
to the same package.

The package is never published partially: files and the manifest are written
through temporary names, flushed, renamed into place, and the final
`<package-id>.ready` marker is written last. A failed regeneration leaves the
previous complete package available and does not publish a new ready marker.

Once the local scheduler observes the reminder becoming due (or a direct ntfy
send is accepted), the package is recorded as delivered in a Blink-owned local
state ledger and becomes immutable. Later edits to the event's attachments do
not rewrite that delivered snapshot. A future reminder receives its own
identity and snapshot. This gives delayed pushes a current snapshot while they
are still queued and a stable snapshot after delivery without a phone-to-Mac
round trip.

## ToPhone package contract

The transport is flat to preserve the proven `Blink Files` feasibility shape:

```text
ToPhone/
  <package-id>.manifest.json
  <package-id>__01__<safe-basename>
  <package-id>__02__<safe-basename>
  <package-id>.ready                 # written last
```

The manifest is versioned JSON containing `version: 1`, `type: "ATTACHMENTS"`,
the exact `package_id`, the source `event_id`, the stable `reminder_key`, and
an ordered list of files with ordinal, transport filename, original display
name, byte size, and SHA-256. It contains no absolute paths and no event
contents beyond the attachment metadata required by the Shortcut.

Only regular, non-hidden files below the canonical event attachment owner are
eligible. Destination names use a strict basename policy; path separators,
NUL, traversal components, and arbitrary package stems are rejected. Duplicate
display names are retained through ordinals and deterministic safe destination
names. A missing/deleted event or an empty attachment set produces no Files
action and no ready package.

Package ownership is exact: every manifest, attachment, and ready marker must
use the complete package stem. The reader ignores incomplete packages, stale
foreign files, and packages whose manifest or file hashes do not validate.

## Lifecycle, retry, and cleanup

- `prepare_snapshot` is idempotent for a queued package: identical source
  content is a no-op; changed content replaces the package atomically.
- A package is considered complete only after `.ready` exists and all manifest
  entries validate.
- Failed copy, hash, iCloud placeholder, or rename operations are retryable and
  never delete the canonical source.
- Delivered and orphaned package state is kept in a Blink-owned local ledger;
  transport files are removed only after a bounded TTL and only when they are
  not current queued packages. Cleanup is restart-safe and never scans or
  deletes arbitrary owner files.
- The cleanup window is deliberately longer than normal iCloud propagation and
  Quick Look use; its exact constant is covered by tests and documented with
  the implementation.

## ntfy and Shortcut contract

For an eligible personal reminder with at least one current attachment, the
canonical payload contains exactly one action with label `Files` and a custom
URL scheme:

```text
shortcuts://run-shortcut?name=Blink%20Files&input=text&text=blink-files-v1%7C<package-id>
```

All query values are percent-encoded with a standards-compliant percent
encoder; spaces are `%20`, never `+`. The input contract is
`blink-files-v1|<package-id>`. No `clear=true` parameter is added. Direct and
queued notifications call the same action builder, and the queue payload hash
therefore includes the resulting action exactly as sent.

`Blink Files` keeps the proven private Shortcuts container and `Ask Where To
Save = OFF`. It accepts the `blink-files-v1|<package-id>` input, validates the
package stem, reads only matching manifest/attachment files from `ToPhone`,
and ignores all other files. With one manifest entry it opens that file
directly in Quick Look; with two or more it presents only that package's files
for selection and then opens the selected file. Missing, incomplete, or
invalid packages fail closed with no access to another event's files.

## Verification and acceptance

Automated coverage must include no-file/action exclusion, one-file direct open,
multi-file chooser, source exclusions, deterministic safe IDs, package and
manifest validation, duplicate names, traversal rejection, iCloud placeholder
retry, missing/deleted events, idempotent regeneration, cleanup TTL, queued
attachment mutation, delivered immutability, stale/missing package handling,
queue identity/dedupe, direct/queued canonical action equality, DONE
coexistence, and Weather/Astronomy exclusion. Existing Python and Swift tests
must remain green.

Before calling Stage 2 complete, create a clean acceptance `ToPhone` folder,
run one controlled real iPhone flow with a personal event that has attachments,
tap the `Files` action, and verify one-file and multi-file behavior without
touching `Blink_Production/ToMac` or enabling the production mailbox. Until
that physical acceptance passes, Stage 2 remains CURRENT and Stage 3 does not
start.
