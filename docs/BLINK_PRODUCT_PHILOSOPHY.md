# Blink — Product Philosophy

## The problem Blink exists to solve

Ordinary reminders remember the consequence but lose the reason. They can say
“return Amazon”, “call Sergey”, or “meeting at 3:00 PM”. Several days later,
the user has to investigate which Amazon order, why Sergey, what the meeting is
about, who sent the document, and whether the source was Slack, email, or
Messages.

Blink exists so the user does not have to reconstruct that history.

## The core promise

Blink preserves the whole chain:

```text
where this came from
  → what needs to be done
  → when it needs attention
  → what will be needed at that moment
```

The reminder is not the whole product. The reminder is the point at which Blink
returns the original context.

## Context is part of the event

When an event has a source document, QR code, barcode, ticket, instruction, or
photo, that source becomes part of the event itself. Sharing an Amazon return
QR code can create “Return Amazon” with that exact QR code. A manager's PDF,
concert ticket, parking reservation, medical instruction, pickup barcode, or
school-event rules can travel with the event and be opened when needed.

The source may be absent. “Water the plants”, “call Mom”, and “pick up the
car” are valid ordinary events. Blink does not require context; it preserves
context when context exists.

## Attention until Done

Blink separates “remind me” from “keep this in my field of attention”. An event
may have several reminders and an independent Blinker lead time. An important
meeting can be scheduled for 3:00 PM, reminded about a day and an hour ahead,
and enter active attention 20 minutes before it starts.

An important event is not considered finished merely because its start time
passed. It remains unfinished until the user explicitly marks it `Done`.

## The surrounding layers

Blink also helps answer “what matters today” with a short daily briefing,
practical weather guidance, and optional astronomy such as sunrise, sunset,
moonrise, and moon phases. These are supporting layers, not competing products
or alternate sources of truth. Future contextual sources may be added without
changing the event core.

## Architectural meaning

The philosophy creates concrete engineering rules:

1. An event and its useful source context belong together.
2. An attachment is owned by its event and returned with its notification.
3. Empty events remain first-class and simple.
4. The Mac is the single source of truth for events, lifecycle, timing, and
   attachment ownership.
5. The iPhone is a fast capture, notification, completion, and context-viewing
   surface.
6. ntfy and iCloud are transport layers, not competing databases.
7. Notifications are derived views of canonical state.
8. `Done` is an explicit, idempotent user decision.
9. Malformed input, foreign files, and ambiguous boundaries fail closed.
10. New features should help the user remember what matters and recover why it
    matters at the right time.

## What Blink is not

Blink is not merely a list of alarms, a loose file manager, a second cloud
database, or a notification stream without durable ownership. It is a
context-preserving attention system.

## North-star sentence

> Blink does not merely remind the user what to do. It remembers why the task
> exists, returns the context needed to do it, and keeps important work visible
> until the user marks it Done.

## Guidance for every future agent

Read this document before changing product behavior. Evaluate proposed changes
against the north star:

- Does the change preserve or restore the reason behind an event?
- Does it return the right context at the moment of action?
- Does it keep the Mac source of truth clear?
- Does it leave no-attachment events simple?
- Does it reduce the chance that important work is forgotten before `Done`?

If a change improves an isolated technical symptom but weakens these answers,
it is not automatically a Blink improvement.

## Future Mac capture entry points

The same context-preserving CREATE flow should eventually be available without
opening the main editor first:

- right-click a supported Finder file and choose the Blink create action;
- when the clipboard contains a supported object, create a Blink event from it
  through a context-menu or equivalent Mac command;
- both entry points reuse the existing one-optional-attachment CREATE contract,
  validation, event ownership, and Mac source of truth.

These are additional capture entry points, not a second event architecture.
