import BlinkSwiftUICore
import Foundation

struct TestFailure: Error, CustomStringConvertible {
    let description: String
}

func expect(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() {
        throw TestFailure(description: message)
    }
}

func temporaryRoot() throws -> URL {
    let root = FileManager.default.temporaryDirectory
        .appendingPathComponent("blink-swiftui-tests-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    return root
}

func readJSONObject(_ url: URL) throws -> [String: Any] {
    let data = try Data(contentsOf: url)
    guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw TestFailure(description: "Expected JSON object at \(url.path)")
    }
    return object
}

func testUpsertPreservesUnknownFields() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {
      "version": 1,
      "future_root": "keep",
      "events": [
        {
          "id": "dentist",
          "title": "Dentist",
          "start": "2026-09-12T15:00:00-07:00",
          "reminders_minutes_before": [30],
          "enabled": true,
          "future_event": "keep-event"
        }
      ]
    }
    """.write(to: agenda, atomically: true, encoding: .utf8)

    let store = BlinkStore(root: root)
    let event = EditableEvent(
        id: "dentist",
        title: "Dentist moved",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 9, day: 12).date!,
        hour: 16,
        minute: 0,
        description: "",
        reminderOffsets: [60, 30],
        enabled: true
    )
    try store.save(event)
    let object = try readJSONObject(agenda)
    let events = object["events"] as? [[String: Any]] ?? []
    try expect(object["future_root"] as? String == "keep", "Root unknown field was not preserved")
    try expect(events.first?["future_event"] as? String == "keep-event", "Event unknown field was not preserved")
    try expect(events.first?["title"] as? String == "Dentist moved", "Title was not updated")
    try expect(events.first?["start"] as? String == "2026-09-12T16:00:00-07:00", "Start ISO string is wrong")
}

func testBuildEventUsesLosAngelesDstOffset() throws {
    let summer = EditableEvent(
        id: "summer",
        title: "Summer",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 9, day: 12).date!,
        hour: 19,
        minute: 0,
        description: "",
        reminderOffsets: [0],
        enabled: true
    )
    let winter = EditableEvent(
        id: "winter",
        title: "Winter",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 12, day: 12).date!,
        hour: 19,
        minute: 0,
        description: "",
        reminderOffsets: [0],
        enabled: true
    )
    try expect(summer.toDictionary()["start"] as? String == "2026-09-12T19:00:00-07:00", "Summer offset is wrong")
    try expect(winter.toDictionary()["start"] as? String == "2026-12-12T19:00:00-08:00", "Winter offset is wrong")
}

func testDisableAndDeleteEvents() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[{"id":"call","title":"Call","start":"2026-09-12T19:00:00-07:00","reminders_minutes_before":[0],"enabled":true}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    try store.setEnabled(eventID: "call", enabled: false)
    var object = try readJSONObject(agenda)
    var events = object["events"] as? [[String: Any]] ?? []
    try expect(events.first?["enabled"] as? Bool == false, "Enabled flag was not changed")
    try store.delete(eventID: "call")
    object = try readJSONObject(agenda)
    events = object["events"] as? [[String: Any]] ?? []
    try expect(events.isEmpty, "Event was not deleted")
}

func testSaveCreatesMissingAgenda() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    let store = BlinkStore(root: root)
    let event = EditableEvent(
        id: "new",
        title: "New event",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 9, day: 12).date!,
        hour: 8,
        minute: 15,
        description: "Created by GUI",
        reminderOffsets: [0],
        enabled: true
    )
    try store.save(event)
    let object = try readJSONObject(agenda)
    let events = object["events"] as? [[String: Any]] ?? []
    try expect(object["version"] as? Int == 1, "Missing agenda did not get version")
    try expect(events.first?["id"] as? String == "new", "New event was not created")
}

func testLifecycleSectionsAndDonePersistence() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[
      {"id":"future","title":"Future","start":"2026-09-08T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":false,"attention_level":"green"},
      {"id":"active","title":"Active","start":"2026-09-05T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":false,"attention_level":"yellow"}
    ]}
    """.write(to: agenda, atomically: true, encoding: .utf8)

    let store = BlinkStore(root: root)
    let now = parseISODate("2026-09-07T12:00:00-07:00")!
    var snapshot = store.loadSnapshot(now: now)
    try expect(snapshot.upcoming.map(\.id) == ["future"], "Future event should be upcoming")
    try expect(snapshot.active.map(\.id) == ["active"], "Past unfinished event should be active")
    try expect(snapshot.history.isEmpty, "Unfinished active event should not be history")

    try store.complete(eventID: "active", now: parseISODate("2026-09-07T14:32:18-07:00")!)
    snapshot = store.loadSnapshot(now: parseISODate("2026-09-07T14:33:00-07:00")!)
    try expect(snapshot.active.isEmpty, "Done event should leave active")
    try expect(snapshot.history.map(\.id) == ["active"], "Done event should enter history")

    let reloaded = BlinkStore(root: root).loadSnapshot(now: parseISODate("2026-09-07T14:34:00-07:00")!)
    try expect(reloaded.history.map(\.id) == ["active"], "Done state should survive reload")
}

func testAttentionHighestPriorityAndExclusions() throws {
    let events = [
        BlinkEvent(id: "green", title: "Green", description: nil, start: "2026-09-07T10:00:00-07:00", reminders_minutes_before: [0], enabled: true, source: nil, requires_done: true, done: false, done_at: nil, attention_level: "green"),
        BlinkEvent(id: "yellow", title: "Yellow", description: nil, start: "2026-09-07T10:00:00-07:00", reminders_minutes_before: [0], enabled: true, source: nil, requires_done: true, done: false, done_at: nil, attention_level: "yellow"),
        BlinkEvent(id: "red", title: "Red", description: nil, start: "2026-09-07T10:00:00-07:00", reminders_minutes_before: [0], enabled: true, source: nil, requires_done: true, done: false, done_at: nil, attention_level: "red"),
        BlinkEvent(id: "disabled-red", title: "Disabled", description: nil, start: "2026-09-07T10:00:00-07:00", reminders_minutes_before: [0], enabled: false, source: nil, requires_done: true, done: false, done_at: nil, attention_level: "red"),
        BlinkEvent(id: "future-red", title: "Future", description: nil, start: "2026-09-08T10:00:00-07:00", reminders_minutes_before: [0], enabled: true, source: nil, requires_done: true, done: false, done_at: nil, attention_level: "red"),
        BlinkEvent(id: "astro-red", title: "Sunset", description: nil, start: "2026-09-07T10:00:00-07:00", reminders_minutes_before: [0], enabled: true, source: "astronomy", requires_done: true, done: false, done_at: nil, attention_level: "red")
    ]
    let now = parseISODate("2026-09-07T12:00:00-07:00")!
    let snapshot = EventSnapshot(events: events, now: now)
    try expect(snapshot.active.map(\.id) == ["green", "yellow", "red"], "Only active personal events should be active")
    try expect(snapshot.history.map(\.id) == ["disabled-red"], "Disabled past event should remain visible in history")
    try expect(snapshot.attentionState == .red, "Highest active attention should win")
    try expect(EventSnapshot(events: [events[0], events[1]], now: now).attentionState == .yellow, "Yellow should beat green")
    try expect(EventSnapshot(events: [events[0]], now: now).attentionState == .green, "One green active should be green")
    try expect(EventSnapshot(events: [events[3], events[4], events[5]], now: now).attentionState == .off, "Disabled/future/astronomy should not create attention")
}

func testLegacyPastEventsDoNotBecomeActive() throws {
    let legacy = BlinkEvent(id: "legacy", title: "Legacy", description: nil, start: "2026-09-01T10:00:00-07:00", reminders_minutes_before: [0], enabled: true, source: nil, requires_done: nil, done: nil, done_at: nil, attention_level: "red")
    let snapshot = EventSnapshot(events: [legacy], now: parseISODate("2026-09-07T12:00:00-07:00")!)
    try expect(snapshot.active.isEmpty, "Legacy past event must not become active")
    try expect(snapshot.history.map(\.id) == ["legacy"], "Legacy past event should remain history")
    try expect(snapshot.attentionState == .off, "Legacy past event should not blink Dock")
}

func testBlinkerOffsetStartsAttentionBeforeEventStart() throws {
    let event = BlinkEvent(
        id: "early",
        title: "Early",
        description: nil,
        start: "2026-09-07T15:00:00-07:00",
        reminders_minutes_before: [0],
        enabled: true,
        source: nil,
        requires_done: true,
        done: false,
        done_at: nil,
        attention_level: "yellow",
        blinker_minutes_before: 300
    )
    let beforeBlinker = EventSnapshot(events: [event], now: parseISODate("2026-09-07T09:59:00-07:00")!)
    let afterBlinker = EventSnapshot(events: [event], now: parseISODate("2026-09-07T10:00:00-07:00")!)
    try expect(beforeBlinker.active.isEmpty, "Event should not be active before blinker start")
    try expect(afterBlinker.active.isEmpty, "Event should remain upcoming until event start")
    try expect(afterBlinker.upcoming.map(\.id) == ["early"], "Event should remain upcoming before event start")
    try expect(afterBlinker.attentionState == .yellow, "Blinker offset should contribute attention color")
}

func testEventSearchMatchesTitleDescriptionDateAndStatus() throws {
    let active = BlinkEvent(
        id: "uscis",
        title: "USCIS",
        description: "Check case status",
        start: "2026-09-07T10:00:00-07:00",
        reminders_minutes_before: [0],
        enabled: true,
        source: nil,
        requires_done: true,
        done: false,
        done_at: nil,
        attention_level: "red",
        blinker_minutes_before: nil
    )
    let done = BlinkEvent(
        id: "filters",
        title: "Buy filters",
        description: "Garage HVAC",
        start: "2026-09-06T10:00:00-07:00",
        reminders_minutes_before: [0],
        enabled: true,
        source: nil,
        requires_done: true,
        done: true,
        done_at: "2026-09-06T12:00:00-07:00",
        attention_level: "green",
        blinker_minutes_before: nil
    )
    try expect(matchesEventSearch(active, query: "case"), "Search should match description")
    try expect(matchesEventSearch(done, query: "filters"), "Search should match title")
    try expect(matchesEventSearch(active, query: "Sep 7, 2026"), "Search should match visible date")
    try expect(matchesEventSearch(done, query: "done"), "Search should match status")
    try expect(matchesEventSearch(active, query: "receipt.pdf", attachmentNames: ["receipt.pdf"]), "Search should match attachment filename")
    try expect(!matchesEventSearch(active, query: "garage"), "Search should not match unrelated event")
}

func testNewEditableEventWritesDoneSchemaAndAttentionLevel() throws {
    let event = EditableEvent.blank()
    let object = event.toDictionary()
    try expect(object["requires_done"] as? Bool == true, "New GUI event should require Done")
    try expect(object["done"] as? Bool == false, "New GUI event should start unfinished")
    try expect(object.keys.contains("done_at"), "New GUI event should include done_at")
    try expect(object["attention_level"] as? String == "green", "New GUI event should default to green attention")
    try expect(object["blinker_minutes_before"] as? Int == 0, "New GUI event should default blinker to the last reminder row")
}

func testDoneAndAttentionWritesPreserveUnknownFields() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"future_root":"keep-root","events":[{"id":"event","title":"Event","start":"2026-09-07T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":false,"attention_level":"green","future_event":"keep-event"}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    try store.setAttentionLevel(eventID: "event", level: .red)
    try store.complete(eventID: "event", now: parseISODate("2026-09-07T14:32:18-07:00")!)
    let object = try readJSONObject(agenda)
    let events = object["events"] as? [[String: Any]] ?? []
    try expect(object["future_root"] as? String == "keep-root", "Root unknown field was not preserved")
    try expect(events.first?["future_event"] as? String == "keep-event", "Event unknown field was not preserved")
    try expect(events.first?["attention_level"] as? String == "red", "Attention was not updated")
    try expect(events.first?["done"] as? Bool == true, "Done flag was not written")
    try expect(events.first?["done_at"] as? String == "2026-09-07T14:32:18-07:00", "Done timestamp is wrong")
}

func testCompleteAfterDoneDaysRecurringAppendsNextEvent() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[{"id":"filter","title":"Change water filter","start":"2026-09-01T08:00:00-07:00","reminders_minutes_before":[1440,0],"enabled":true,"requires_done":true,"done":false,"attention_level":"yellow","recurrence":{"mode":"after_done_days","days":90}}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    try store.complete(eventID: "filter", now: parseISODate("2026-09-07T14:32:18-07:00")!)
    let object = try readJSONObject(agenda)
    let events = object["events"] as? [[String: Any]] ?? []
    let recurrence = events.last?["recurrence"] as? [String: Any]
    try expect(events.count == 2, "Recurring completion should append next event")
    try expect(events.first?["done"] as? Bool == true, "Original event should be done")
    try expect(events.last?["done"] as? Bool == false, "Next event should start undone")
    try expect(events.last?["start"] as? String == "2026-12-06T08:00:00-08:00", "Next after-done event start is wrong")
    try expect(recurrence?["mode"] as? String == "after_done_days", "Recurrence should be preserved")
}

func testCompleteWeeklyFixedRecurringAppendsNextWeekday() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[{"id":"monday","title":"Every Monday","start":"2026-09-07T08:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":false,"attention_level":"green","recurrence":{"mode":"weekly_fixed","weekday":1,"time":"08:00"}}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    try store.complete(eventID: "monday", now: parseISODate("2026-09-07T09:00:00-07:00")!)
    let object = try readJSONObject(agenda)
    let events = object["events"] as? [[String: Any]] ?? []
    try expect(events.count == 2, "Weekly completion should append next event")
    try expect(events.last?["start"] as? String == "2026-09-14T08:00:00-07:00", "Next weekly event start is wrong")
}

func testEditingDoneEventIsRejected() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[{"id":"event","title":"Done Event","start":"2026-09-07T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":true,"done_at":"2026-09-07T14:32:18-07:00","attention_level":"green"}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    let event = EditableEvent(
        id: "event",
        title: "Renamed",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 9, day: 7).date!,
        hour: 11,
        minute: 0,
        description: "",
        reminderOffsets: [0],
        enabled: true,
        attentionLevel: .yellow
    )
    var rejected = false
    do {
        try store.save(event)
    } catch {
        rejected = true
    }
    try expect(rejected, "Completed history event should be frozen")
}

func testEditingDoneEventToFutureIsRejected() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[{"id":"event","title":"Done Event","start":"2026-09-07T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":true,"done_at":"2026-09-07T14:32:18-07:00","attention_level":"green"}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    let event = EditableEvent(
        id: "event",
        title: "Done Event",
        date: parseISODate("2026-09-10T00:00:00-07:00")!,
        hour: 11,
        minute: 0,
        description: "",
        reminderOffsets: [0],
        enabled: true,
        attentionLevel: .green
    )
    var rejected = false
    do {
        try store.save(event)
    } catch {
        rejected = true
    }
    try expect(rejected, "Moving a history event to the future should be rejected")
}

func testLoadingStaleCompletedFutureEventRepairsAndMovesIt() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[{"id":"event","title":"Recovered","start":"2026-09-10T11:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":true,"done_at":"2026-09-08T09:09:40-07:00"}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    let snapshot = store.loadSnapshot(now: parseISODate("2026-09-08T09:00:00-07:00")!)
    try expect(snapshot.upcoming.map(\.id) == ["event"], "Stale completed future event should be repaired into upcoming")
    try expect(snapshot.history.isEmpty, "Repaired event should leave history")
    let object = try readJSONObject(agenda)
    let events = object["events"] as? [[String: Any]] ?? []
    try expect(events.first?["done"] as? Bool == false, "Stale completed future event was not persisted as unfinished")
}

func testAttentionOutputMappingAndTransitions() throws {
    let recorder = RecordingAttentionOutput()
    let manager = AttentionManager(outputs: [recorder])
    manager.setState(.red)
    manager.setState(.yellow)
    manager.setState(.green)
    manager.setState(.off)
    try expect(recorder.states == [.red, .yellow, .green, .off], "Attention output transitions are wrong")
}

func testLoadsAstronomyV2LocationAndWeatherReadOnlyFiles() throws {
    let root = try temporaryRoot()
    try FileManager.default.createDirectory(at: root.appendingPathComponent("astronomy"), withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: root.appendingPathComponent("weather"), withIntermediateDirectories: true)
    try """
    {
      "version": 2,
      "timezone": "America/Los_Angeles",
      "notifications": {
        "sun": {
          "enabled": true,
          "events": {
            "sunrise": {"enabled": true, "offsets_minutes_before": [30, 0]},
            "sunset": true
          }
        }
      }
    }
    """.write(to: root.appendingPathComponent("astronomy/astronomy_config.json"), atomically: true, encoding: .utf8)
    try """
    {"version":1,"display_name":"Sunnyvale, California, USA","latitude":37.3688,"longitude":-122.0363,"timezone":"America/Los_Angeles"}
    """.write(to: root.appendingPathComponent("location.json"), atomically: true, encoding: .utf8)
    try """
    {"version":1,"weather_enabled":true,"morning_briefing":{"enabled":true,"time":"06:30"}}
    """.write(to: root.appendingPathComponent("weather/weather_config.json"), atomically: true, encoding: .utf8)
    try """
    {"version":1,"status":"fresh","forecast_date":"2026-09-07","fetched_at":"2026-09-07T06:00:00-07:00","high_f":78,"low_f":59,"humidity_min_percent":40,"humidity_max_percent":70,"rain_probability_percent":0,"rain_window":null,"snow_expected":false,"wind_speed_mph":8,"wind_gust_mph":15,"wind_warning":false}
    """.write(to: root.appendingPathComponent("weather/weather_cache.json"), atomically: true, encoding: .utf8)

    let store = BlinkStore(root: root)
    let astronomy = store.loadAstronomyConfig()
    let astronomySchedule = store.loadAstronomySchedule()
    let location = store.loadLocation()
    let weatherConfig = store.loadWeatherConfig()
    let weatherCache = store.loadWeatherCache()

    try expect(astronomy?.notifications["sun"]?.events["sunrise"]?.enabled == true, "Astronomy v2 event setting did not decode")
    try expect(astronomy?.notifications["sun"]?.events["sunrise"]?.offsets_minutes_before == [30, 0], "Astronomy v2 offsets did not decode")
    try expect(astronomy?.notifications["sun"]?.events["sunset"]?.enabled == true, "Legacy astronomy bool did not decode")
    try expect(astronomySchedule?.generation_status == nil, "Missing optional astronomy schedule should decode as nil")
    try expect(location?.display_name == "Sunnyvale, California, USA", "Location did not decode")
    try expect(weatherConfig?.morning_briefing.time == "06:30", "Weather config did not decode")
    try expect(weatherCache?.high_f == 78, "Weather cache did not decode")
}

func testLoadsAstronomyScheduleStatus() throws {
    let root = try temporaryRoot()
    try FileManager.default.createDirectory(at: root.appendingPathComponent("astronomy"), withIntermediateDirectories: true)
    try """
    {"version":2,"generation_status":"pending_precise_ephemeris","generated_from":"2026-09-07","generated_through":"2028-09-07","daily_records":[]}
    """.write(to: root.appendingPathComponent("astronomy/astronomy_schedule.json"), atomically: true, encoding: .utf8)
    let schedule = BlinkStore(root: root).loadAstronomySchedule()
    try expect(schedule?.generation_status == "pending_precise_ephemeris", "Astronomy schedule status did not decode")
    try expect(schedule?.generated_through == "2028-09-07", "Astronomy schedule horizon did not decode")
}

func testEventDateTimeLabelIncludesDateAndTime() throws {
    let label = eventDateTimeLabel("2026-09-12T19:05:00-07:00")
    try expect(label.contains("Sep"), "Event label should include month")
    try expect(label.contains("12"), "Event label should include day")
    try expect(label.contains("2026"), "Event label should include year")
    try expect(label.contains("19:05"), "Event label should use 24-hour time")
}

func testReminderOffsetsRespectEventLeadTime() throws {
    let start = parseISODate("2026-09-07T13:30:00-07:00")!
    let now = parseISODate("2026-09-07T13:00:00-07:00")!
    try expect(isReminderOffsetAvailable(30, eventStart: start, now: now), "30 minute reminder should be available")
    try expect(isReminderOffsetAvailable(10, eventStart: start, now: now), "10 minute reminder should be available")
    try expect(isReminderOffsetAvailable(5, eventStart: start, now: now), "5 minute reminder should be available")
    try expect(isReminderOffsetAvailable(0, eventStart: start, now: now), "At-time reminder should be available")
    try expect(!isReminderOffsetAvailable(60, eventStart: start, now: now), "60 minute reminder should be unavailable")
    try expect(!isReminderOffsetAvailable(300, eventStart: start, now: now), "5 hour reminder should be unavailable")
}

func testEditableEventDropsUnavailableReminderOffsets() throws {
    let event = EditableEvent(
        id: "soon",
        title: "Soon",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 9, day: 7).date!,
        hour: 13,
        minute: 30,
        description: "",
        reminderOffsets: [1440, 60, 30, 10, 0],
        enabled: true
    )
    let now = parseISODate("2026-09-07T13:00:00-07:00")!
    let object = event.toDictionary(now: now)
    try expect(object["reminders_minutes_before"] as? [Int] == [30, 10, 0], "Unavailable reminders should be removed before saving")
}

func testLoadsReminderConfigWithFallback() throws {
    let root = try temporaryRoot()
    let fallback = BlinkStore(root: root).loadReminderConfig()
    try expect(fallback.presets.map(\.minutes_before) == [1440, 720, 300, 60, 30, 10, 5, 0], "Default reminder config is wrong")
    try """
    {"version":1,"presets":[{"minutes_before":90,"label":"90 min before"},{"minutes_before":0,"label":"At time"}]}
    """.write(to: root.appendingPathComponent("reminders.json"), atomically: true, encoding: .utf8)
    let loaded = BlinkStore(root: root).loadReminderConfig()
    try expect(loaded.presets.map(\.minutes_before) == [90, 0], "Reminder config did not load custom presets")
    try expect(loaded.presets.first?.label == "90 min before", "Reminder config did not load labels")
}

func testSaveWeatherConfigTogglePreservesMorningTime() throws {
    let root = try temporaryRoot()
    try FileManager.default.createDirectory(at: root.appendingPathComponent("weather"), withIntermediateDirectories: true)
    let url = root.appendingPathComponent("weather/weather_config.json")
    try """
    {"version":1,"weather_enabled":true,"morning_briefing":{"enabled":true,"time":"06:30"},"thresholds":{"rain_probability_percent":40},"future":"keep"}
    """.write(to: url, atomically: true, encoding: .utf8)

    let store = BlinkStore(root: root)
    try store.saveWeatherEnabled(false)
    let object = try readJSONObject(url)
    let morning = object["morning_briefing"] as? [String: Any]

    try expect(object["weather_enabled"] as? Bool == false, "Weather enabled flag was not saved")
    try expect(morning?["time"] as? String == "06:30", "Morning time was not preserved")
    try expect(object["future"] as? String == "keep", "Unknown weather config field was not preserved")
}

func testSaveWeatherSettingsPreservesUnknownFields() throws {
    let root = try temporaryRoot()
    try FileManager.default.createDirectory(at: root.appendingPathComponent("weather"), withIntermediateDirectories: true)
    let url = root.appendingPathComponent("weather/weather_config.json")
    try """
    {"version":1,"weather_enabled":true,"morning_briefing":{"enabled":true,"time":"06:30"},"thresholds":{"rain_probability_percent":40},"future":"keep"}
    """.write(to: url, atomically: true, encoding: .utf8)

    let store = BlinkStore(root: root)
    var config = WeatherConfig(
        weather_enabled: false,
        morning_briefing: WeatherConfig.MorningBriefing(enabled: true, time: "07:15"),
        include: WeatherConfig.Include(temperature: true, humidity: false, wind: true, rain: true, snow: false)
    )
    try store.saveWeatherSettings(config)
    let object = try readJSONObject(url)
    let morning = object["morning_briefing"] as? [String: Any]
    let include = object["include"] as? [String: Any]

    try expect(object["weather_enabled"] as? Bool == false, "Weather enabled flag was not saved")
    try expect(morning?["time"] as? String == "07:15", "Morning time was not saved")
    try expect(include?["humidity"] as? Bool == false, "Humidity include flag was not saved")
    try expect(include?["snow"] as? Bool == false, "Snow include flag was not saved")
    try expect(object["future"] as? String == "keep", "Unknown weather config field was not preserved")
    config.weather_enabled = true
    try expect(config.weather_enabled, "Weather config should remain mutable in the editor")
}

func testBriefingSavesRecordConfigurationChangeInstant() throws {
    let root = try temporaryRoot()
    try FileManager.default.createDirectory(at: root.appendingPathComponent("weather"), withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: root.appendingPathComponent("astronomy"), withIntermediateDirectories: true)
    try """
    {"version":1,"weather_enabled":true,"morning_briefing":{"enabled":true,"time":"06:30"}}
    """.write(to: root.appendingPathComponent("weather/weather_config.json"), atomically: true, encoding: .utf8)
    try """
    {"version":1,"last_weather_briefing_status":"delivered"}
    """.write(to: root.appendingPathComponent("weather/weather_state.json"), atomically: true, encoding: .utf8)
    try """
    {"version":2,"timezone":"America/Los_Angeles","notifications":{"sun":{"enabled":true,"events":{}}},"briefing":{"enabled":true,"time":"06:30","include_day_night":true,"include_weather":false}}
    """.write(to: root.appendingPathComponent("astronomy/astronomy_config.json"), atomically: true, encoding: .utf8)

    let store = BlinkStore(root: root)
    let weather = WeatherConfig(
        weather_enabled: true,
        morning_briefing: WeatherConfig.MorningBriefing(enabled: true, time: "06:00"),
        include: WeatherConfig.Include(temperature: true, humidity: true, wind: true, rain: true, snow: true)
    )
    try store.saveWeatherSettings(weather)
    let weatherState = try readJSONObject(root.appendingPathComponent("weather/weather_state.json"))
    try expect((weatherState["briefing_config_changed_at"] as? String)?.isEmpty == false, "Weather briefing save should record its change instant")

    var astronomy = try expectLoadedAstronomyConfig(store)
    astronomy.briefing = AstronomyConfig.Briefing(enabled: true, time: "06:00", include_day_night: true, include_weather: false)
    try store.saveAstronomySettings(astronomy)
    let astronomyObject = try readJSONObject(root.appendingPathComponent("astronomy/astronomy_config.json"))
    let briefing = astronomyObject["briefing"] as? [String: Any]
    try expect((briefing?["config_changed_at"] as? String)?.isEmpty == false, "Astronomy briefing save should record its change instant")
}

func expectLoadedAstronomyConfig(_ store: BlinkStore) throws -> AstronomyConfig {
    guard let config = store.loadAstronomyConfig() else {
        throw TestFailure(description: "Astronomy config did not load")
    }
    return config
}

func testSaveLocationInvalidatesDerivedCaches() throws {
    let root = try temporaryRoot()
    try FileManager.default.createDirectory(at: root.appendingPathComponent("weather"), withIntermediateDirectories: true)
    try FileManager.default.createDirectory(at: root.appendingPathComponent("astronomy"), withIntermediateDirectories: true)
    try """
    {"version":1,"display_name":"Sunnyvale, California, USA","latitude":37.3688,"longitude":-122.0363,"timezone":"America/Los_Angeles"}
    """.write(to: root.appendingPathComponent("location.json"), atomically: true, encoding: .utf8)
    try """
    {"version":1,"status":"fresh","forecast_date":"2026-09-07"}
    """.write(to: root.appendingPathComponent("weather/weather_cache.json"), atomically: true, encoding: .utf8)
    try """
    {"version":2,"generation_status":"fresh","daily_records":[{"date":"2026-09-07"}]}
    """.write(to: root.appendingPathComponent("astronomy/astronomy_schedule.json"), atomically: true, encoding: .utf8)
    try """
    {"version":2,"timezone":"America/Los_Angeles","location":{"display_name":"Sunnyvale","latitude":37.3688,"longitude":-122.0363}}
    """.write(to: root.appendingPathComponent("astronomy/astronomy_config.json"), atomically: true, encoding: .utf8)

    let store = BlinkStore(root: root)
    try store.saveLocation(BlinkLocation(display_name: "New York, USA", latitude: 40.7128, longitude: -74.0060, timezone: "America/New_York"))

    let location = store.loadLocation()
    let weatherCache = try readJSONObject(root.appendingPathComponent("weather/weather_cache.json"))
    let astronomy = try readJSONObject(root.appendingPathComponent("astronomy/astronomy_schedule.json"))
    let astronomyConfig = try readJSONObject(root.appendingPathComponent("astronomy/astronomy_config.json"))
    let astronomyLocation = astronomyConfig["location"] as? [String: Any]

    try expect(location?.display_name == "New York, USA", "Location was not saved")
    try expect(weatherCache["status"] as? String == "stale_location_changed", "Weather cache was not invalidated")
    try expect(astronomy["generation_status"] as? String == "needs_regeneration", "Astronomy schedule was not invalidated")
    try expect(astronomyConfig["timezone"] as? String == "America/New_York", "Astronomy timezone was not synchronized")
    try expect(astronomyLocation?["latitude"] as? Double == 40.7128, "Astronomy coordinates were not synchronized")
}

func testMenuBarSummaryShowsActiveAndNextEvents() throws {
    let events = [
        BlinkEvent(
            id: "call",
            title: "Call Robert",
            description: nil,
            start: "2026-09-07T15:00:00-07:00",
            reminders_minutes_before: [0],
            enabled: true,
            source: "personal",
            requires_done: true,
            done: false,
            done_at: nil,
            attention_level: "green"
        ),
        BlinkEvent(
            id: "uscis",
            title: "USCIS",
            description: nil,
            start: "2026-09-07T13:00:00-07:00",
            reminders_minutes_before: [0],
            enabled: true,
            source: "personal",
            requires_done: true,
            done: false,
            done_at: nil,
            attention_level: "red"
        ),
        BlinkEvent(
            id: "filters",
            title: "Buy filters",
            description: nil,
            start: "2026-09-08T09:00:00-07:00",
            reminders_minutes_before: [0],
            enabled: true,
            source: "personal",
            requires_done: true,
            done: false,
            done_at: nil,
            attention_level: "green"
        )
    ]
    let snapshot = EventSnapshot(events: events, now: parseISODate("2026-09-07T15:10:00-07:00")!)
    let summary = MenuBarSummary(snapshot: snapshot)

    try expect(summary.statusTitle == "● 2 Active", "Menu title should include active count")
    try expect(summary.activeItems.map(\.title) == ["USCIS", "Call Robert"], "Active items should be priority/time sorted")
    try expect(summary.nextItem?.title == "Buy filters", "Next item should be first upcoming event")
    try expect(summary.attentionState == .red, "Menu state should match snapshot attention")
}

func testEditableEventWritesRecurrenceContracts() throws {
    let monday = DateComponents(
        calendar: Calendar(identifier: .gregorian),
        timeZone: blinkTimeZone,
        year: 2026,
        month: 9,
        day: 7
    ).date!
    let weekly = EditableEvent(
        id: "weekly",
        title: "Weekly",
        date: monday,
        hour: 8,
        minute: 0,
        description: "",
        reminderOffsets: [0],
        enabled: true,
        recurrence: EventRecurrence(mode: "weekly_fixed")
    )
    let weeklyRecurrence = weekly.toDictionary()["recurrence"] as? [String: Any]
    try expect(weeklyRecurrence?["mode"] as? String == "weekly_fixed", "Weekly mode was not written")
    try expect(weeklyRecurrence?["weekday"] as? Int == 1, "Weekly recurrence should write ISO Monday")
    try expect(weeklyRecurrence?["time"] as? String == "08:00", "Weekly recurrence should use selected time")

    let afterDone = EditableEvent(
        id: "after-done",
        title: "After Done",
        date: monday,
        hour: 8,
        minute: 0,
        description: "",
        reminderOffsets: [0],
        enabled: true,
        recurrence: EventRecurrence(mode: "after_done_days", days: 90)
    )
    let afterDoneRecurrence = afterDone.toDictionary()["recurrence"] as? [String: Any]
    try expect(afterDoneRecurrence?["mode"] as? String == "after_done_days", "After Done mode was not written")
    try expect(afterDoneRecurrence?["days"] as? Int == 90, "After Done days were not written")
}

func testEditorBackdropAndTimeFieldUiContracts() throws {
    try expect(shouldDismissEventEditorOnBackdropTap(editorIsDirty: false), "Backdrop click should dismiss clean editor")
    try expect(shouldDismissEventEditorOnBackdropTap(editorIsDirty: true), "Backdrop click should dismiss dirty editor too")
    try expect(eventEditorTimeFieldWidth >= 104, "Time field should be wide enough for HH:mm")
    try expect(timeInputWidth >= 104, "Shared time input width should fit HH:mm")
    try expect(saveButtonOpacity(hasUnsavedChanges: true) == 1.0, "Dirty save button should be visible")
    try expect(saveButtonOpacity(hasUnsavedChanges: false) < 1.0, "Saved button should be dimmed")
    try expect(saveButtonTitle(defaultTitle: "Save Weather", saved: false) == "Save Weather", "Dirty save button should keep its action label")
    try expect(saveButtonTitle(defaultTitle: "Save Weather", saved: true) == "Saved", "Saved button should show completion feedback")
}

func testEventEditorLayoutContracts() throws {
    let contentView = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: contentView, encoding: .utf8)
    try expect(source.contains("TextEditor(text: $draft.title)"), "Title editor should support multiline text")
    try expect(source.contains("HStack(spacing: 18)"), "Reminder controls should use aligned columns")
    try expect(source.contains(".frame(width: 230, alignment: .leading)"), "Reminder columns should have a stable width")
    try expect(source.contains(".frame(maxWidth: 620, alignment: .leading)"), "Editor form should use a centered readable content width")
}

func testNewEventActionStaysInsideWindowContent() throws {
    let contentView = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: contentView, encoding: .utf8)
    try expect(source.contains("Image(systemName: \"plus\")"), "New Event should use the compact in-window plus action")
    try expect(source.contains("Text(\"Today\").font(.title.bold())"), "The Today title should remain next to the new event action")
    try expect(!source.contains(".safeAreaInset(edge: .top"), "New Event should not use an overflowing top inset")
    try expect(!source.contains("Button(\"New Event\")"), "The old wide New Event button should be removed")
    try expect(!source.contains("ToolbarItemGroup(placement: .automatic) {\n            TextField(\"Search\", text: $searchQuery)\n                .textFieldStyle(.roundedBorder)\n                .frame(width: 220)\n            Button(\"New Event\", action: onNewEvent)"), "New Event should not live in the overflowing automatic toolbar group")
}

func testNewEventPlusButtonAndTabHoverContracts() throws {
    let contentView = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: contentView, encoding: .utf8)
    try expect(source.contains("Image(systemName: \"plus\")"), "Today should expose a round plus button for creating events")
    try expect(source.contains(".clipShape(Circle())"), "The new event action should be circular")
    try expect(source.contains(".onHover { isHovered in"), "Every custom tab should react to mouse hover")
    try expect(source.contains("isHovered ? Color.primary.opacity(0.07)"), "Hovered tabs should have a subtle visual state")
}

func testImportancePickerUsesEventColor() throws {
    let contentView = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: contentView, encoding: .utf8)
    try expect(source.contains(".tint(color(for: draft.attentionLevel))"), "Importance picker should tint its selected segment with the event color")
}

func testActiveAttentionUiContracts() throws {
    let sourceURL = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: sourceURL, encoding: .utf8)

    try expect(source.contains("attentionPulseOn"), "ContentView should own a UI-only attention pulse state")
    try expect(source.contains("Button(event.enabled ? \"On\" : \"Off\")"), "Event state button should use On/Off labels")
    try expect(source.contains("activeEventIDs"), "Event rows should receive active event identity")
    try expect(source.contains("pulseVisible"), "Event rows should receive pulse visibility")
    try expect(source.contains("rowContentOpacity"), "Rows should dim disabled content separately from the priority dot")
    try expect(source.contains("BlinkTabButton"), "Blink should render its own tab title so priority color is not ignored by AppKit")
    try expect(source.contains("todayTabAttentionColor"), "Today tab should receive the highest active priority color")
}

func testLocationSearchAndCustomCoordinateContracts() throws {
    let url = try LocationGeocoder.searchURL(query: "San Francisco")
    let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
    try expect(components?.host == "geocoding-api.open-meteo.com", "Location search should use the Open-Meteo geocoder")
    try expect(components?.queryItems?.contains(where: { $0.name == "count" && $0.value == "10" }) == true, "Location search should request ranked suggestions")
    try expect(commonTimezones.count > 100, "Timezone picker should expose the complete system timezone list")
    try expect(commonTimezones.contains("Asia/Tokyo"), "Timezone picker should include global zones")
    try expect(locationCoordinateFieldEditable(customMode: true), "Custom coordinate mode should enable coordinate inputs")
    try expect(!locationCoordinateFieldEditable(customMode: false), "City mode should keep resolved coordinates read-only")
}

func testGuiStoreDoesNotContainSenderSymbols() throws {
    let sourceRoot = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources")
    let files = try FileManager.default.subpathsOfDirectory(atPath: sourceRoot.path)
    let text = try files
        .filter { $0.hasSuffix(".swift") }
        .map { try String(contentsOf: sourceRoot.appendingPathComponent($0), encoding: .utf8) }
        .joined(separator: "\n")
    try expect(!text.contains("URLSession"), "SwiftUI layer must not use URLSession")
    try expect(!text.contains("ntfy"), "SwiftUI layer must not mention ntfy")
    try expect(!text.contains("POST"), "SwiftUI layer must not send POST")
}

func testAstronomyUsesSharedPushIcons() throws {
    let contentView = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: contentView, encoding: .utf8)
    try expect(source.contains("case \"sunrise\": return \"☀️ ↑\""), "Sunrise settings must use the thin rise arrow")
    try expect(source.contains("case \"sunset\": return \"☀️ ↓\""), "Sunset settings must use the thin set arrow")
    try expect(source.contains("AstronomySummaryRow(icon: \"☀️ ↑\", label: \"Sunrise\""), "Sunrise summary must use the thin rise arrow")
    try expect(source.contains("AstronomySummaryRow(icon: \"☀️ ↓\", label: \"Sunset\""), "Sunset summary must use the thin set arrow")
    try expect(source.contains("case \"moonrise\": return \"🌙 ↑\""), "Moonrise settings must use the thin rise arrow")
    try expect(source.contains("case \"moonset\": return \"🌙 ↓\""), "Moonset settings must use the thin set arrow")
    try expect(source.contains("AstronomySummaryRow(icon: \"🌙 ↑\", label: \"Moonrise\""), "Moonrise summary must use the thin rise arrow")
    try expect(source.contains("AstronomySummaryRow(icon: \"🌙 ↓\", label: \"Moonset\""), "Moonset summary must use the thin set arrow")
}

func testAstronomyUsesSharedAlignedColumns() throws {
    let contentView = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: contentView, encoding: .utf8)
    try expect(source.contains("private struct AstronomyAlignedColumns"), "Astronomy must define one shared two-column layout")
    try expect(source.contains("AstronomyAlignedColumns {\n                        if let group = draft.notifications[\"sun\"]"), "Sun settings must occupy the left shared column")
    try expect(source.contains("AstronomyAlignedColumns {\n                sunSummary"), "Sun summary must occupy the left shared column")
}

func testAstronomyUsesDirectionalPhaseLabels() throws {
    let contentView = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: contentView, encoding: .utf8)
    try expect(source.contains("case \"waxing moon\": return \"🌒\""), "SwiftUI must render non-event waxing phases as a crescent")
    try expect(source.contains("case \"waning moon\": return \"🌘\""), "SwiftUI must render non-event waning phases as a crescent")
    try expect(source.contains("record.new_moon == nil && record.full_moon == nil"), "SwiftUI must omit trend arrows on exact phase-event days")
}

func testAttachmentWorkspaceRoundTrip() throws {
    let root = try temporaryRoot()
    let workspace = AttachmentWorkspace(root: root)
    let emptyFolder = try workspace.ensureAttachmentFolder(ownerID: "empty")
    try expect(FileManager.default.fileExists(atPath: emptyFolder.path), "Empty attachment folder should be created on demand")
    let emptyFiles = try workspace.files(ownerID: "empty")
    try expect(emptyFiles.isEmpty, "Empty attachment folder should enumerate no files")
    let draftID = try workspace.createDraft()
    let secondDraftID = try workspace.createDraft()
    try expect(draftID != secondDraftID && draftID.hasPrefix("draft-"), "Draft IDs should be unique UUIDs")
    try workspace.discard(draftID: secondDraftID)
    let source = root.appendingPathComponent("source.txt")
    try "attachment".write(to: source, atomically: true, encoding: .utf8)
    try workspace.addFiles([source], to: draftID)
    let removable = root.appendingPathComponent("removable.txt")
    try "remove me".write(to: removable, atomically: true, encoding: .utf8)
    try workspace.addFiles([removable], to: draftID)
    let draftFiles = try workspace.draftFiles(draftID: draftID)
    guard let removableCopy = draftFiles.first(where: { $0.lastPathComponent == "removable.txt" }) else {
        throw TestFailure(description: "Draft attachment to remove was not staged")
    }
    try workspace.removeDraftFile(removableCopy, draftID: draftID)
    try workspace.addJPEG(Data([0xFF, 0xD8, 0xFF, 0xD9]), to: draftID, date: Date(timeIntervalSince1970: 0))
    let manifest = try workspace.finalize(draftID: draftID, ownerID: "event-1")
    try expect(manifest.ownerID == "event-1", "Attachment owner ID is wrong")
    try expect(manifest.count == 2 && manifest.hasFiles, "Attachment manifest did not count the files")
    let target = workspace.attachmentURL(ownerID: "event-1")
    try expect(FileManager.default.fileExists(atPath: target.appendingPathComponent("source.txt").path), "Final attachment was not materialized")
    try Data("hidden".utf8).write(to: target.appendingPathComponent(".hidden.txt"))
    try FileManager.default.createDirectory(at: target.appendingPathComponent("nested"), withIntermediateDirectories: true)
    let ownerFiles = try workspace.files(ownerID: "event-1")
    try expect(ownerFiles.count == 2, "Owner folder should enumerate regular attachments")
    let names = try FileManager.default.contentsOfDirectory(at: target, includingPropertiesForKeys: nil).map(\.lastPathComponent)
    try expect(names.contains(where: { $0.hasPrefix("screenshot-") && $0.hasSuffix(".jpg") && !$0.contains("(formatter") }), "Screenshot should use a timestamped JPEG name")
}

func testExternalAttachmentFolderReconcilesManifest() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try "{\"version\":1,\"events\":[{\"id\":\"event-1\",\"title\":\"Folder\",\"start\":\"2099-09-12T12:30:00-07:00\",\"reminders_minutes_before\":[0],\"enabled\":true,\"requires_done\":true,\"done\":false}]}".write(to: agenda, atomically: true, encoding: .utf8)
    let workspace = AttachmentWorkspace(root: root)
    let owner = try workspace.ensureAttachmentFolder(ownerID: "event-1")
    try Data("external".utf8).write(to: owner.appendingPathComponent("from-finder.txt"))
    guard let event = BlinkStore(root: root).loadEvents(now: Date(timeIntervalSince1970: 0)).first else {
        throw TestFailure(description: "External folder event did not load")
    }
    try expect(event.hasAttachments && event.attachments?.count == 1, "External folder files should reconcile into the event manifest")
}

func testAttachmentDraftCancelAndMultilineEventContract() throws {
    let root = try temporaryRoot()
    let workspace = AttachmentWorkspace(root: root)
    let draftID = try workspace.createDraft()
    try workspace.discard(draftID: draftID)
    try expect(!FileManager.default.fileExists(atPath: workspace.draftURL(draftID).path), "Discarded draft still exists")

    let event = EditableEvent(
        id: "event-1",
        title: "First line\nSecond line",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 9, day: 12).date!,
        hour: 12,
        minute: 30,
        description: "Paragraph one\n\nParagraph two",
        reminderOffsets: [0],
        enabled: true,
        attachments: AttachmentManifest(ownerID: "event-1", count: 1, hasFiles: true)
    )
    let dictionary = event.toDictionary()
    try expect(dictionary["title"] as? String == "First line\nSecond line", "Title paragraphs were not preserved")
    try expect(dictionary["description"] as? String == "Paragraph one\n\nParagraph two", "Description paragraphs were not preserved")
    try expect((dictionary["attachments"] as? [String: Any])?["has_files"] as? Bool == true, "Attachment manifest was not serialized")

    let legacyAgenda = try JSONSerialization.data(withJSONObject: [
        "events": [[
            "id": "legacy",
            "title": "Legacy",
            "start": "2099-09-12T12:30:00-07:00",
            "reminders_minutes_before": [0],
            "enabled": true,
            "attachments": ["unexpected": "shape"]
        ]]
    ])
    let decoded = try JSONDecoder().decode(AgendaDocument.self, from: legacyAgenda)
    try expect(decoded.events.count == 1 && decoded.events[0].attachments?.hasFiles == false, "Malformed attachment metadata should migrate as empty")
}

func testSavingEventCommitsAttachmentsAndPreservesDraftOnFailure() throws {
    let root = try temporaryRoot()
    let store = BlinkStore(root: root)
    let workspace = AttachmentWorkspace(root: root)
    let draftID = try workspace.createDraft()
    let source = root.appendingPathComponent("meeting-notes.txt")
    try "notes".write(to: source, atomically: true, encoding: .utf8)
    try workspace.addFiles([source], to: draftID)
    let event = EditableEvent(
        id: "meeting",
        title: "Meeting",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2099, month: 9, day: 12).date!,
        hour: 12,
        minute: 30,
        description: "Agenda",
        reminderOffsets: [0],
        enabled: true
    )
    try store.save(event, attachmentWorkspace: workspace, draftID: draftID)
    let object = try readJSONObject(root.appendingPathComponent("agenda.json"))
    let saved = (object["events"] as? [[String: Any]])?.first
    try expect((saved?["attachments"] as? [String: Any])?["has_files"] as? Bool == true, "Saved event should advertise attachments")
    try expect(!FileManager.default.fileExists(atPath: workspace.draftURL(draftID).path), "Committed draft should be removed")
    try expect(FileManager.default.fileExists(atPath: workspace.attachmentURL(ownerID: "meeting").appendingPathComponent("meeting-notes.txt").path), "Committed file should remain under Blink root")
}

func testEventRowsExposeAttachmentAndHistoryContracts() throws {
    let sourceURL = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: sourceURL, encoding: .utf8)
    try expect(source.contains("TextEditor(text: $draft.title)"), "Title should use a multiline editor")
    try expect(source.contains("TextEditor(text: $draft.description)"), "Description should use a multiline editor")
    try expect(source.contains("Paste Screenshot"), "Context menu should expose screenshot paste")
    try expect(source.contains("Duplicate as new event"), "Context menu should expose History duplication")
    try expect(source.contains("contextMenu"), "Event rows should expose a context menu")
    try expect(source.contains("showsHistory"), "Event rows should know when History is frozen")
}

func testAttachmentFolderMenuAndPreviewContracts() throws {
    let sourceURL = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/ContentView.swift")
    let source = try String(contentsOf: sourceURL, encoding: .utf8)
    try expect(source.contains("if !showsHistory || event.hasAttachments"), "Active events should always expose their attachment folder")
    try expect(source.contains("if clipboardImageAvailable()"), "Paste Screenshot should appear only for image clipboard data")
    try expect(source.contains("AttachmentPreviewList"), "The editor should show attachment previews")
    try expect(source.contains("Remove"), "Draft attachments should have a remove action")
}

func testAttachmentWorkspaceFolderContracts() throws {
    let sourceURL = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("Sources/BlinkSwiftUICore/AttachmentStore.swift")
    let source = try String(contentsOf: sourceURL, encoding: .utf8)
    try expect(source.contains("ensureAttachmentFolder"), "Attachment workspace should create an empty owner folder on demand")
    try expect(source.contains("public func files(ownerID: String)"), "Attachment workspace should enumerate files for previews")
}

func testHistorySaveIsRejectedAndAttachmentMetadataPersists() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[{"id":"past","title":"Past","start":"2026-09-08T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":true,"done_at":"2026-09-08T10:00:00-07:00"}]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let store = BlinkStore(root: root)
    let past = EditableEvent(
        id: "past",
        title: "Changed",
        date: DateComponents(calendar: Calendar(identifier: .gregorian), year: 2026, month: 9, day: 8).date!,
        hour: 10,
        minute: 0,
        description: "Changed",
        reminderOffsets: [0],
        enabled: true
    )
    var rejected = false
    do {
        try store.save(past)
    } catch {
        rejected = true
    }
    try expect(rejected, "History event edit should be rejected")
}

func testRecurringDeleteKeepsSharedAttachmentOwner() throws {
    let root = try temporaryRoot()
    let agenda = root.appendingPathComponent("agenda.json")
    try """
    {"version":1,"events":[
      {"id":"series-g1","series_id":"series","title":"Past","start":"2026-09-08T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":true,"done_at":"2026-09-08T10:00:00-07:00"},
      {"id":"series-g2","series_id":"series","title":"Next","start":"2026-09-15T10:00:00-07:00","reminders_minutes_before":[0],"enabled":true,"requires_done":true,"done":false}
    ]}
    """.write(to: agenda, atomically: true, encoding: .utf8)
    let workspace = AttachmentWorkspace(root: root)
    let owner = workspace.attachmentURL(ownerID: "series")
    try FileManager.default.createDirectory(at: owner, withIntermediateDirectories: true)
    try Data("shared".utf8).write(to: owner.appendingPathComponent("shared.txt"))
    try BlinkStore(root: root).delete(eventID: "series-g1")
    try expect(FileManager.default.fileExists(atPath: owner.appendingPathComponent("shared.txt").path), "Shared recurring attachments should remain while the series has another occurrence")
}

let tests: [(String, () throws -> Void)] = [
    ("upsert preserves unknown fields", testUpsertPreservesUnknownFields),
    ("Los Angeles DST offset", testBuildEventUsesLosAngelesDstOffset),
    ("disable and delete events", testDisableAndDeleteEvents),
    ("save creates missing agenda", testSaveCreatesMissingAgenda),
    ("lifecycle sections and done persistence", testLifecycleSectionsAndDonePersistence),
    ("attention highest priority and exclusions", testAttentionHighestPriorityAndExclusions),
    ("legacy past events do not become active", testLegacyPastEventsDoNotBecomeActive),
    ("blinker offset starts attention before event start", testBlinkerOffsetStartsAttentionBeforeEventStart),
    ("event search matches title description date and status", testEventSearchMatchesTitleDescriptionDateAndStatus),
    ("new editable event writes done schema and attention level", testNewEditableEventWritesDoneSchemaAndAttentionLevel),
    ("done and attention writes preserve unknown fields", testDoneAndAttentionWritesPreserveUnknownFields),
    ("complete after done days recurring appends next event", testCompleteAfterDoneDaysRecurringAppendsNextEvent),
    ("complete weekly fixed recurring appends next weekday", testCompleteWeeklyFixedRecurringAppendsNextWeekday),
    ("editing done event is rejected", testEditingDoneEventIsRejected),
    ("editing done event to future is rejected", testEditingDoneEventToFutureIsRejected),
    ("loading stale completed future event repairs and moves it", testLoadingStaleCompletedFutureEventRepairsAndMovesIt),
    ("attention output mapping and transitions", testAttentionOutputMappingAndTransitions),
    ("loads astronomy v2 location and weather read-only files", testLoadsAstronomyV2LocationAndWeatherReadOnlyFiles),
    ("loads astronomy schedule status", testLoadsAstronomyScheduleStatus),
    ("event date time label includes date and time", testEventDateTimeLabelIncludesDateAndTime),
    ("reminder offsets respect event lead time", testReminderOffsetsRespectEventLeadTime),
    ("editable event drops unavailable reminder offsets", testEditableEventDropsUnavailableReminderOffsets),
    ("loads reminder config with fallback", testLoadsReminderConfigWithFallback),
    ("save weather config toggle preserves morning time", testSaveWeatherConfigTogglePreservesMorningTime),
    ("save weather settings preserves unknown fields", testSaveWeatherSettingsPreservesUnknownFields),
    ("briefing saves record configuration change instant", testBriefingSavesRecordConfigurationChangeInstant),
    ("save location invalidates derived caches", testSaveLocationInvalidatesDerivedCaches),
    ("menu bar summary shows active and next events", testMenuBarSummaryShowsActiveAndNextEvents),
    ("editable event writes recurrence contracts", testEditableEventWritesRecurrenceContracts),
    ("editor backdrop and time field UI contracts", testEditorBackdropAndTimeFieldUiContracts),
    ("event editor layout contracts", testEventEditorLayoutContracts),
    ("new event action stays inside window content", testNewEventActionStaysInsideWindowContent),
    ("new event plus button and tab hover contracts", testNewEventPlusButtonAndTabHoverContracts),
    ("importance picker uses event color", testImportancePickerUsesEventColor),
    ("active attention UI contracts", testActiveAttentionUiContracts),
    ("location search and custom coordinate contracts", testLocationSearchAndCustomCoordinateContracts),
    ("GUI store has no sender symbols", testGuiStoreDoesNotContainSenderSymbols),
    ("Astronomy uses shared push icons", testAstronomyUsesSharedPushIcons),
    ("Astronomy uses shared aligned columns", testAstronomyUsesSharedAlignedColumns),
    ("Astronomy uses directional phase labels", testAstronomyUsesDirectionalPhaseLabels),
    ("attachment workspace round trip", testAttachmentWorkspaceRoundTrip),
    ("external attachment folder reconciles manifest", testExternalAttachmentFolderReconcilesManifest),
    ("attachment draft cancel and multiline event contract", testAttachmentDraftCancelAndMultilineEventContract),
    ("saving event commits attachments", testSavingEventCommitsAttachmentsAndPreservesDraftOnFailure),
    ("event rows expose attachment and history contracts", testEventRowsExposeAttachmentAndHistoryContracts),
    ("attachment folder menu and preview contracts", testAttachmentFolderMenuAndPreviewContracts),
    ("attachment workspace folder contracts", testAttachmentWorkspaceFolderContracts),
    ("history save is rejected", testHistorySaveIsRejectedAndAttachmentMetadataPersists),
    ("recurring delete keeps shared attachments", testRecurringDeleteKeepsSharedAttachmentOwner)
]

do {
    for (name, test) in tests {
        try test()
        print("PASS \(name)")
    }
    print("Swift Blink store tests passed.")
} catch {
    print("FAIL \(error)")
    exit(1)
}
