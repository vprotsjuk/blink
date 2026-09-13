# Blink — complete program description and unresolved iPhone Quick Look problem

**Document purpose:** standalone context for an independent GPT/ChatGPT thread.
The new thread should understand the Blink program, its safety boundaries, the
current iPhone file-viewing design, and the exact unresolved problem without
reading another document first.

**Snapshot:** 2026-09-13  
**Project root:** /Users/vitaliiprotsiuk/Desktop/Blink  
**Owner language:** Russian; technical discussion may be English.  
**Current Git commit:** 69a4a42 docs: record Files acquisition repair and retest result
**Current branch:** main  
**Production mailbox:** disabled  
**New ntfy notification for this investigation:** one Files-only retest sent to WORK; physical tap completed, still no preview

---

## 1. What Blink is

Blink is a local-first macOS reminder and daily-information application. It
stores personal events and settings as local JSON, keeps event attachments in
Blink-owned local folders, calculates Weather and Astronomy on the Mac, sends
notifications through ntfy, and controls a USB blinker/lamp through the
existing watcher process.

The application is single-user and local-first. The Mac is the source of truth.
The iPhone is a notification and manual input/viewing endpoint, not a second
event database.

The central runtime chain is:

~~~text
SwiftUI GUI
    -> local JSON and Blink-owned attachment folders
        -> watcher.py
            -> ntfy notifications -> iPhone/Mac
            -> USB blinker/lamp
~~~

This boundary is mandatory:

- SwiftUI is the editor/viewer. It reads and writes local contracts but does
  not send production ntfy notifications.
- watcher.py is the only production scheduler, sender, queue reconciler, and
  hardware-blinker coordinator.
- ntfy is transport and notification presentation, never the database or
  source of truth.
- agenda.json and Blink-local attachment folders are canonical.
- There is no SQLite database, cloud backend, public URL, Calendar
  integration, second sender, second scheduler, or phone-to-Mac round trip for
  attachment viewing.
- Weather, Astronomy, Location, Personal Events, Attention, and iPhone
  transport are separate blocks connected by explicit contracts.

## 2. Repository and important runtime files

The relevant checkout is:

~~~text
/Users/vitaliiprotsiuk/Desktop/Blink/
~~~

Important source files:

~~~text
watcher.py                         production scheduler/sender/blinker
app/agenda_store.py                event persistence, lifecycle, recurrence, locking
app/event_timing.py                timezone-aware timing
app/attachment_store.py            transactional attachment ownership
app/notification_format.py         canonical ntfy body/header/action formatting
app/ntfy_schedule.py               rolling 24-hour queue and signatures
app/mailbox_importer.py            opt-in/test mailbox parser and transactions
app/BlinkSwiftUI/                  native macOS GUI and Swift tests
astronomy/generate_astronomy.py    Skyfield/local-ephemeris schedule generation
~~~

Canonical local data:

~~~text
agenda.json
location.json
config.json
watcher_state.json
watcher_runtime.json
ntfy_schedule_state.json
event_data/attachments/<event-id>/
event_data/drafts/<draft-id>/
weather/weather_config.json
weather/weather_cache.json
weather/weather_state.json
astronomy/astronomy_config.json
astronomy/astronomy_schedule.json
astronomy/ephemeris/de440s.bsp
~~~

agenda.json, local settings/state, event_data/, app bundles, build products,
backups, and virtual environments are ignored where appropriate. Real user
PDFs, images, DWG files, and spreadsheets must not enter Git.

The latest documented verification before the retest override was:

- Python default suite: 219 passing;
- focused source/regression suite: 111 passing;
- Swift test runner: pass;
- Swift release build: pass;
- Python compile checks: pass;
- plist lint: pass;
- git diff --check: pass;
- ./status_watcher.command: healthy watcher with fresh heartbeat.

The owner has decided to keep timing unchanged: reminders retain existing
presets, integer-minute Custom minutes, and multiple offsets; Blinker retains
existing presets, integer minutes, and one offset with no Custom value. No new
timing model, fractional minutes, seconds, or universal timing control is part
of this task.

The default Python command is:

~~~bash
.venv/bin/python -m unittest -q
~~~

This checkout has root-level test_*.py modules and no importable tests/ package,
so unittest discover -s tests is not the correct command here.

## 3. Personal event contract and lifecycle

Every event has at least:

- id;
- title;
- start with an explicit UTC offset;
- reminders_minutes_before;
- enabled.

Optional fields include multiline description, importance/attention level,
independent blinker_minutes_before, recurrence metadata, tags, and local
attachment metadata. Arbitrary Unicode, quotes, backslashes, and newlines in
user-entered title/description must survive persistence.

The lifecycle is:

~~~text
Upcoming -> Active -> Done -> History
~~~

Rules:

- done=true is authoritative even when the scheduled start is in the future.
- Done preserves the original start, records actual done_at, clears
  Attention/blinker eligibility, and is idempotent.
- A past unfinished enabled event remains Active until Done.
- Off changes notification eligibility only; it is not Done and does not
  delete the event.
- Disabled past events remain inspectable in frozen History.
- History cannot be edited in place. It can be duplicated as a new event or
  deleted.
- A recurring successor receives a new event ID and starts with no
  attachments.
- Snooze, Quiet Hours, and Templates are retired and must not be reintroduced.
- Reminder offsets are non-negative integer minutes and may contain arbitrary
  values and multiple entries. Blinker timing is independent; a new event
  defaults to blinker_minutes_before = 0 (At event).

The GUI keeps a last-good in-memory event snapshot. A valid empty agenda.json
means Loaded (0); an unreadable or malformed file means Error/Stale, not an
empty event list. Today, Upcoming, History, and Search continue showing the
last-good snapshot while Health reports the error.

## 4. Attachments and ownership

Attachment bytes are canonical only in Blink-owned folders:

~~~text
event_data/attachments/<event-id>/   saved files for one occurrence
event_data/drafts/<draft-id>/        temporary editor staging
~~~

The JSON stores metadata only: owner ID, count, and has_files. It never stores
absolute paths or file bytes. series_id is recurrence metadata only, never an
attachment owner.

Attachment behavior:

- Every event occurrence owns its own event-ID folder.
- New-event editor Add Files, Paste, and drag/drop stage into a draft until
  Save.
- Cancel/Escape removes only the Blink-created draft.
- Failed Save keeps the draft recoverable.
- Today/Upcoming row Add Files and Paste are immediate transactions on the
  already-saved event; they do not open the editor and do not require Save.
- All files in a batch are validated first. If one fails, the whole operation
  rolls back and existing files/metadata remain unchanged.
- Finder file URLs have priority over image clipboard data.
- If there are no file URLs, image clipboard data becomes a timestamped JPEG.
- Directories and recursive folder copies are rejected.
- Drag-and-drop is accepted only inside the editor attachment panel, not on
  event rows.
- Search includes local attachment filenames and extensions, but not file
  contents.
- History is frozen. It may reveal an existing attachment folder but must not
  create a new one.

Personal ntfy notifications show only a paperclip marker when attachments are
present. They never send local paths, filenames, or file bytes.

## 5. GUI behavior

The native SwiftUI app includes these surfaces:

- Today: active events for the local current day, including overdue unfinished
  events;
- Upcoming: future enabled events sorted by effective local start;
- History: completed, disabled-retained, and past records with frozen rows;
- Astronomy: calculated Sun/Moon settings and today's summary;
- Weather: independent weather settings, cache, and summary;
- Location: city/custom coordinates plus explicit IANA timezone;
- Health: diagnostics only, never a second control plane;
- Search: event title, description, and local attachment-name search.

Today has a round blue + button to the left of the heading. Rows expose
priority, title, description, attachment count, folder access, Done, On/Off,
Edit, and Delete as allowed by lifecycle. History exposes duplication and
deletion but not Edit or On/Off.

The editor uses 24-hour time, multiline Title/Description, reminders, an
independent Blinker picker, attachment staging, and Save/Cancel. Save buttons
change to Saved and become disabled until another change occurs. Dirty modal
state is guarded against accidental navigation or backdrop dismissal.

Selected Day is a temporary view created by double-clicking a non-today date in
the editor calendar. It uses the shared event snapshot, includes all events on
that local date, sorts by local start and event ID, scopes Search to that day,
and does not persist across relaunch.

## 6. Weather, Astronomy, Location, Attention

Weather uses Open-Meteo and the active coherent latitude/longitude/IANA
timezone tuple. It fetches fresh data before a due direct briefing and keeps a
normalized local cache.

Astronomy uses Skyfield, local de440s.bsp, NumPy, and topocentric local
coordinates. It generates a rolling schedule and supports Sun events, Moon
events, illumination, phase direction, rise/set, and day/night duration. The
watcher owns the notification formatter; SwiftUI mirrors the approved icon
language and does not calculate a second astronomy model.

Personal and Astronomy reminders use the rolling 24-hour remote queue.
Weather is separate direct delivery and is never added to that queue. Weather
and Astronomy can share a briefing time, but remain independent blocks.

The app's visual Attention and the hardware blinker are separate. Attention
clears when an event is Done. The watcher owns the real USB blinker state.

## 7. ntfy notification contract

ntfy headers carry Title, Priority, and Tags. The visible body is human-readable
and must not contain raw JSON, internal scheduling keys, absolute paths, or
transport objects.

Personal event titles use the attention icon 🟢, 🟡, or 🔴; if local attachments
exist, exactly one 📎 marker is added. ntfy priority is an independent urgency
value.

The queue signature includes the visible has_files bit. Therefore:

- false -> true and true -> false rebuild a queued notification so the
  paperclip is correct;
- changing only the attachment count does not duplicate an otherwise unchanged
  delivery.

The same canonical action builder is used by direct and queued paths.

Remote DONE input is:

~~~text
blink-done-v1|<event_id>
~~~

After a newly applied remote DONE, Mac may send exactly one short confirmation
without an action button and without clear=true. Replays, no-ops, stale,
malformed, pending, and failed commands are silent. Production DONE action
delivery is disabled by default.

## 8. Private iCloud / Apple Shortcuts transport

The verified private Apple Shortcuts container is:

~~~text
~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents
~~~

Relevant roots:

~~~text
Blink_Feasibility/ToMac       historical/manual feasibility only
Blink_Feasibility/ToPhone    historical/manual feasibility only
Blink_Acceptance/ToMac       controlled acceptance only; mailbox OFF
Blink_Acceptance/ToPhone     controlled Files package inbox
Blink_Production/ToMac       must remain unused
~~~

The mailbox is transport only. agenda.json remains the Mac source of truth.
The Mac importer is opt-in/test-only in the current state. It must never
consume, delete, or move historical feasibility files while diagnosing Quick
Look.

Incoming CREATE/DONE packages use flat files and write .ready last. The Mac
reader validates complete packages, handles iCloud dataless/pending-sync
files, applies canonical business logic, is idempotent, and deletes transport
files only after successful application. Production mailbox processing is
currently disabled.

### DONE package

~~~text
<command-id>.done.json
<command-id>.ready
~~~

The accepted test Shortcut Blink DONE Test validates the exact escaped
literal-pipe input, writes into Blink_Acceptance/ToMac, and ends without
creating a privacy/output popup.

### CREATE package

The accepted Blink Create Test supports direct launch and Share Sheet input
with no attachment or one image/PDF/file attachment. The flat/v2 transport
supports explicit-offset dates, arbitrary non-negative reminder/blinker
minutes, empty Description, and phone-side validation of required Title.

The native Shortcut has no Generate UUID action, so transport identity uses:

~~~text
<yyyyMMddHHmmss>-<9-digit-random>
~~~

UUIDv4 remains accepted for backward compatibility. The transport ID is never
an event ID or event start time.

## 9. Mac -> iPhone Files package contract

Stage 2 Mac-side implementation is behind two explicit opt-in controls:

~~~text
BLINK_NTFY_FILES_ACTION_ENABLED=1
BLINK_TO_PHONE_ROOT=<explicit approved root>
BLINK_NTFY_FILES_SHORTCUT_NAME=<controlled test override only>
~~~

The package is a deterministic, flat, event-specific snapshot generated from
the canonical event-ID attachment folder. The package ID has the form:

~~~text
blink-files-v1-<sha256-prefix>
~~~

The package contains:

~~~text
<package-id>.manifest.json
<package-id>__01__<safe-basename>
<package-id>__02__<safe-basename>
...
<package-id>.ready
~~~

.ready is written last. The manifest contains package ID, source event/reminder
identity, ordered filenames, sizes, and SHA-256 values. It contains no
absolute paths.

While a reminder is queued or delayed, reconciliation refreshes the same
package if canonical attachments change. Once the reminder is due and the
snapshot is delivered, it remains immutable until bounded cleanup.

The ntfy action input is:

~~~text
blink-files-v1|<package-id>
~~~

The URL must use percent encoding, including %20 for spaces and %7C for the
pipe. It must not use + for spaces and must not include clear=true:

~~~text
shortcuts://run-shortcut?name=Blink%20Files&input=text&text=blink-files-v1%7C<package-id>
~~~

When both actions are enabled for an unfinished personal event, the canonical
Mac payload is two independent ntfy actions separated by a semicolon:

~~~text
view, Done, shortcuts://run-shortcut?name=Blink%20DONE&input=text&text=blink-done-v1%7C<event-id>; view, Files, shortcuts://run-shortcut?name=Blink%20Files&input=text&text=blink-files-v1%7C<package-id>
~~~

The comma-separated fields are the ntfy short action format; the semicolon is
the action separator. `Done` and `Files` must remain independently usable.
The source builder's canonical default name is `Blink Files`; the isolated WORK
Shortcut is a separate acceptance candidate, so any physical retest must
verify that its action URL names the intended Shortcut before sending or
reusing a notification.

The source now supports this override only when explicitly set; production
behavior remains `Blink Files` when it is unset.

Only the matching package may be shown. The Shortcut must ignore unrelated
files, .manifest.json, and .ready as displayable attachments.

## 10. Shortcuts and backups

### Blink Files

This is the old proven Shortcut. It must remain unchanged while diagnosing the
WORK candidate.

Its old proven path was visibly:

~~~text
Get File / folder from Shortcuts/Blink_Feasibility/ToPhone
-> Get Contents of File (applied to the folder in the old UI)
-> Choose from Folder Contents
-> Show Selected Item in Quick Look
~~~

### Blink Files BACKUP Stage2

This is an intentional backup and must remain unchanged.

### Blink Files Stage2 WORK

This is the only Shortcut under investigation. Its current tree is:

~~~text
Receive Shortcut Input (no input: Continue)
Get Text from Shortcut Input
Match Text:
  ^blink-files-v1\|blink-files-v1-[0-9a-f]{32}$
If Matches does not have any value
  Stop This Shortcut
Otherwise
Split Shortcut Input by literal |
Get Item at Index 2
Set Variable PackageID

Get file from Shortcuts at path Blink_Acceptance/ToPhone
Get Contents of File
Set Variable AllFiles
Text [PackageID].ready
Set Variable ReadyName
Filter AllFiles where Name is ReadyName
Count ready matches
If ready count is not 1 -> Stop This Shortcut

Text [PackageID].manifest.json
Set Variable ManifestName
Filter AllFiles where Name is ManifestName
Count manifest matches
If manifest count is not 1 -> Stop This Shortcut

Text [PackageID]__
Set Variable AttachmentPrefix
Filter AllFiles where Name begins with AttachmentPrefix
Set Variable Attachments to Files
Count Items in Attachments
Set Variable AttachmentCount to Count
If AttachmentCount is 0 -> Stop This Shortcut
Otherwise
  If AttachmentCount is 1
    Choose from Attachments (Select Multiple OFF)
    Show Selected Item in Quick Look
  Otherwise
    Choose from Attachments (Select Multiple OFF)
    Show Selected Item in Quick Look
  End If
End If
~~~

The candidate has the expected validation and isolation checks: exact escaped
pipe regex, .ready existence, manifest existence, exact package attachment
prefix, and fail-closed count handling.

The final actions must be Quick Look actions, not Open Item, unless an
independent test proves that another action is required and safe.

## 11. Exact unresolved problem

The first controlled Files acceptance package was generated for the real
eligible event:

~~~text
event-0f6edc58-50f4-48fb-9423-15ddb499d876
~~~

It contained a canonical PDF attachment and used package ID:

~~~text
blink-files-v1-f5363e8bb0beeba1de7c2cf98215e8c9
~~~

The hardened candidate was targeted by an ntfy action. ntfy accepted the
request with HTTP 200. The action had no clear=true.

Observed iPhone behavior:

1. Tapping the ntfy Files action opened the Shortcuts library/editor context
   rather than visibly presenting the PDF.
2. The Shortcut later showed a completion checkmark.
3. No PDF Quick Look preview appeared after completion.
4. The same PDF is visible and opens manually in the iPhone Files app.
5. The package is present in Blink_Acceptance/ToPhone.
6. A later iPhone screenshot confirmed that the full WORK candidate and the
   escaped-pipe regex were present on the phone.
7. The Mac-generated action URL and package/input contract were verified.
8. One Files-only retest was sent explicitly to `Blink Files Stage2 WORK`
   using the same validated one-file package. The owner tapped the action;
   the Shortcut completed with a checkmark, but no chooser or PDF preview
   appeared. This is not acceptance.
9. Immediately before that push, Mac-side evaluation of the actual package
   produced `AllFiles = 3`, `.ready = 1`, manifest = 1, and `Attachments = 1`.
   The WORK plist contains 46 actions and its successful branch ends in
   `Choose from Attachments` → `Show Selected Item in Quick Look`. The
   pre-repair WORK copy had 42 actions. The owner subsequently confirmed by
   iPhone editor screenshot that the repaired `Get file` → `Get Contents of
   File` → `AllFiles` prefix is present on the phone. The stale-version
   hypothesis is therefore removed. The remaining diagnostic boundary is
   the iPhone runtime output after `AllFiles` and the final Quick Look
   presentation. No further push should be sent before that boundary is
   diagnosed.

Therefore package availability and basic iCloud synchronization are proven.
The unresolved area is the binding/presentation between the filtered Shortcut
output and the Quick Look action, or an iOS Shortcuts presentation behavior.

Important caution: the old Shortcut visibly called an action Get Contents of
File while it was applied to the ToPhone folder. The current macOS Shortcut
editor may expose the corresponding operation under a different name. Adding
another contents action after Attachments without verifying input/output
types may convert file references into raw file contents and break Quick Look.

The current candidate was then repaired at the acquisition boundary. Its
verified Mac action prefix is now:

- `Get file from Shortcuts at path Blink_Acceptance/ToPhone`;
- `Get Contents of File` applied to that folder;
- `Set Variable AllFiles` from `Folder Contents`.

The existing validation and final branches remain unchanged. Before this
acquisition repair, the candidate was adjusted only in its final branches:

- one file: chooser -> Show Selected Item in Quick Look;
- multiple files: chooser -> Show Selected Item in Quick Look.

The SQLite action blob and macOS editor confirm that both chooser inputs are
the filtered `Attachments` File items/references. The repaired tree was
tested by one new phone notification after the repair, but the result was
again only a checkmark with no chooser or preview. The iPhone editor now
confirms the repaired acquisition prefix; actual runtime values after
`AllFiles` still need independent verification.

## 12. Exact questions for independent GPT diagnosis

Please independently diagnose the issue from the facts above. Do not assume
that earlier reports are correct; distinguish observed facts from hypotheses.

Answer these questions:

1. What is the actual type/output of Get Contents of
   Shortcuts/Blink_Acceptance/ToPhone?
2. What is the actual type/output of AllFiles?
3. What is the actual type/output of Attachments after the name-prefix
   filter?
4. What is the actual type/output of the chooser's Selected Item after
   Attachments contains one File item?
5. Is Show Selected Item in Quick Look semantically correct after that chooser?
6. Does the one-file branch need a folder-contents action, a list conversion,
   Quick Look, or another action before presentation?
7. Could the filter be returning file objects, file references, a list of
   files, or raw bytes, and how can that be proved in the Shortcut editor?
8. Is the no-preview result caused by a wrong binding, the iPhone run context,
   or an iOS Quick Look presentation limitation?
9. What is the smallest safe edit and what exact physical retest proves it?

The prepared diagnostic candidate uses a chooser even for the one-file case,
followed by Show Selected Item in Quick Look, because that resembles the old
proven path. This is only a hypothesis, not an accepted fix until the PDF is
visibly presented on the physical iPhone.

Do not recommend or use Open Item merely because it opens the file. Open Item is
not currently accepted as the intended design and may create a different
presentation path than Quick Look.

## 13. Safety and non-negotiable restrictions

While investigating this issue:

- do not modify Blink Files;
- do not modify Blink Files BACKUP Stage2;
- do not modify unrelated Shortcuts;
- do not enable BLINK_MAILBOX_ENABLED;
- do not configure or use Blink_Production/ToMac;
- do not add clear=true;
- do not send another ntfy notification unless the owner explicitly authorizes
  a controlled retest;
- do not start Stage 3 Today Morning Briefing, Stage 5/6 work, USB hardware
  work, or Home Screen icon work;
- do not delete acceptance, WORK, test, or backup artifacts before the Files
  acceptance is resolved and documented;
- do not introduce a second sender, scheduler, database, public URL, or
  phone-to-Mac acknowledgement loop.

The production mailbox must remain disabled throughout the diagnosis.

## 14. Current roadmap position

Completed:

- Mac core persistence, lifecycle, recurrence, attachments, Weather,
  Astronomy, Location, queue, and Attention;
- Phase 1 shared agenda locking;
- Phase 2A/2B mailbox parser and canonical transactions;
- Phase 3 opt-in watcher mailbox worker;
- Phase 4A/4B DONE action support and real iPhone acceptance;
- Phase 5 CREATE transport and real iPhone acceptance;
- Phase 6 controlled CREATE/DONE acceptance;
- Phase 7 fast external agenda refresh;
- Stage 0 documentation reconciliation;
- Stage 1 Early Done, remote confirmation, Dock/Attention acceptance;
- Stage 2A/2B Mac attachment snapshot and Shortcut hardening design.

Current:

- Stage 2C: iPhone Shortcut implementation and Quick Look diagnosis.

Remaining after this diagnosis:

- Stage 2D: physical one-file and multi-file Files acceptance;
- Stage 2E: Stage 2 closeout and production decision;
- optional Today Morning Briefing;
- final one-icon Blink phone setup and Share -> Blink flow;
- cleanup of obsolete test/WORK/proof artifacts after accepted replacements;
- later USB RGB adapter and numeric mailbox/package/worker limits.

## 15. Required output from the GPT consultation

Return an evidence-based diagnosis with:

1. the most likely root cause and competing hypotheses;
2. the actual Shortcut type flow that must be inspected;
3. the exact minimal edit, or a clear statement that no edit is yet proven;
4. a physical iPhone retest procedure for one file and multiple files;
5. what result counts as acceptance;
6. confirmation that the proposed procedure preserves package isolation,
   production mailbox-off state, and the no-Open Item rule.

Do not declare the issue fixed until the PDF is visibly presented on the
physical iPhone.
