import Foundation

public struct AgendaDocument: Codable {
    public var events: [BlinkEvent]
}

public struct BlinkEvent: Codable, Identifiable {
    public let id: String
    public let title: String
    public let description: String?
    public let start: String
    public let reminders_minutes_before: [Int]
    public let enabled: Bool
    public let source: String?
    public let requires_done: Bool?
    public let done: Bool?
    public let done_at: String?
    public let attention_level: String?
    public let blinker_minutes_before: Int?
    public let recurrence: EventRecurrence?
    public let series_id: String?
    public let attachments: AttachmentManifest?

    public init(
        id: String,
        title: String,
        description: String?,
        start: String,
        reminders_minutes_before: [Int],
        enabled: Bool,
        source: String?,
        requires_done: Bool?,
        done: Bool?,
        done_at: String?,
        attention_level: String?,
        blinker_minutes_before: Int? = nil,
        recurrence: EventRecurrence? = nil,
        series_id: String? = nil,
        attachments: AttachmentManifest? = nil
    ) {
        self.id = id
        self.title = title
        self.description = description
        self.start = start
        self.reminders_minutes_before = reminders_minutes_before
        self.enabled = enabled
        self.source = source
        self.requires_done = requires_done
        self.done = done
        self.done_at = done_at
        self.attention_level = attention_level
        self.blinker_minutes_before = blinker_minutes_before
        self.recurrence = recurrence
        self.series_id = series_id
        self.attachments = attachments
    }

    public var attentionLevel: AttentionState {
        AttentionState(rawValue: attention_level ?? "") ?? .green
    }

    public var blinkerMinutesBefore: Int {
        max(blinker_minutes_before ?? 0, 0)
    }

    public var isPersonal: Bool {
        (source ?? "personal") == "personal"
    }

    public var hasAttachments: Bool {
        attachments?.hasFiles == true
    }

    public var attachmentOwnerID: String {
        let candidate = series_id?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return candidate.isEmpty ? id : candidate
    }
}

public struct EventRecurrence: Codable, Equatable {
    public var mode: String
    public var days: Int?
    public var weekday: Int?
    public var time: String?

    public init(mode: String, days: Int? = nil, weekday: Int? = nil, time: String? = nil) {
        self.mode = mode
        self.days = days
        self.weekday = weekday
        self.time = time
    }

    public func toDictionary() -> [String: Any] {
        var output: [String: Any] = ["mode": mode]
        if let days {
            output["days"] = days
        }
        if let weekday {
            output["weekday"] = weekday
        }
        if let time {
            output["time"] = time
        }
        return output
    }
}

public struct AstronomyConfig: Codable {
    public struct EventSetting: Codable {
        public var enabled: Bool
        public var offsets_minutes_before: [Int]

        public init(enabled: Bool, offsets_minutes_before: [Int] = [0]) {
            self.enabled = enabled
            self.offsets_minutes_before = offsets_minutes_before
        }

        public init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if let enabled = try? container.decode(Bool.self) {
                self.enabled = enabled
                self.offsets_minutes_before = [0]
                return
            }
            let object = try container.decode([String: JSONValue].self)
            self.enabled = object["enabled"]?.boolValue ?? false
            self.offsets_minutes_before = object["offsets_minutes_before"]?.intArrayValue ?? [0]
        }
    }

    public struct NotificationGroup: Codable {
        public var enabled: Bool
        public var events: [String: EventSetting]
    }

    public struct Briefing: Codable {
        public var enabled: Bool
        public var time: String
        public var include_day_night: Bool
        public var include_weather: Bool

        public init(enabled: Bool = true, time: String = "06:30", include_day_night: Bool = true, include_weather: Bool = true) {
            self.enabled = enabled
            self.time = time
            self.include_day_night = include_day_night
            self.include_weather = include_weather
        }
    }

    public var timezone: String
    public var notifications: [String: NotificationGroup]
    public var briefing: Briefing

    public init(timezone: String, notifications: [String: NotificationGroup], briefing: Briefing = Briefing()) {
        self.timezone = timezone
        self.notifications = notifications
        self.briefing = briefing
    }

    private enum CodingKeys: String, CodingKey { case timezone, notifications, briefing }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        timezone = try container.decode(String.self, forKey: .timezone)
        notifications = try container.decode([String: NotificationGroup].self, forKey: .notifications)
            .filter { $0.key == "sun" || $0.key == "moon" }
        briefing = try container.decodeIfPresent(Briefing.self, forKey: .briefing) ?? Briefing()
    }
}

public struct AstronomySchedule: Codable {
    public let generation_status: String?
    public let generated_from: String?
    public let generated_through: String?
    public let daily_records: [AstronomyDailyRecord]?
}

public struct AstronomyTimeRecord: Codable {
    public let time: String?
}

public struct AstronomySunsetRecord: Codable {
    public let time: String?
    public let civil_twilight_end: String?
    public let day_length_minutes: Int?
}

public struct AstronomyMoonStatusRecord: Codable {
    public let above_horizon: Bool?
    public let illumination_percent: Double?
    public let phase_degrees: Double?
    public let phase_name: String?
    public let phase_trend: String?
    public let moonrise: String?
    public let moonset: String?
}

public struct AstronomyPhaseEventRecord: Codable {
    public let time: String?
}

public struct AstronomyDailyRecord: Codable {
    public let date: String
    public let day_length_minutes: Int?
    public let illumination: Double?
    public let sunrise: AstronomyTimeRecord?
    public let solar_noon: AstronomyTimeRecord?
    public let sunset: AstronomySunsetRecord?
    public let civil_twilight_end: AstronomyTimeRecord?
    public let moonrise: String?
    public let moonset: String?
    public let moon_status_at_sunset: AstronomyMoonStatusRecord?
    public let new_moon: AstronomyPhaseEventRecord?
    public let full_moon: AstronomyPhaseEventRecord?
    public let next_new_moon: String?
    public let next_full_moon: String?
}

public struct BlinkLocation: Codable, Identifiable, Sendable {
    public let display_name: String
    public let latitude: Double
    public let longitude: Double
    public let timezone: String
    public let coordinate_source: String?

    public var id: String {
        "\(display_name)|\(latitude)|\(longitude)|\(timezone)"
    }

    public init(display_name: String, latitude: Double, longitude: Double, timezone: String, coordinate_source: String? = "city") {
        self.display_name = display_name
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.coordinate_source = coordinate_source
    }
}

public func locationCoordinateFieldEditable(customMode: Bool) -> Bool {
    customMode
}

public struct WeatherConfig: Codable {
    public struct MorningBriefing: Codable {
        public let enabled: Bool
        public var time: String

        public init(enabled: Bool, time: String) {
            self.enabled = enabled
            self.time = time
        }
    }

    public struct Include: Codable {
        public var temperature: Bool?
        public var humidity: Bool?
        public var wind: Bool?
        public var rain: Bool?
        public var snow: Bool?

        public init(temperature: Bool?, humidity: Bool?, wind: Bool?, rain: Bool?, snow: Bool?) {
            self.temperature = temperature
            self.humidity = humidity
            self.wind = wind
            self.rain = rain
            self.snow = snow
        }
    }

    public var weather_enabled: Bool
    public var morning_briefing: MorningBriefing
    public var include: Include?

    public init(weather_enabled: Bool, morning_briefing: MorningBriefing, include: Include?) {
        self.weather_enabled = weather_enabled
        self.morning_briefing = morning_briefing
        self.include = include
    }

    public func includeValue(_ keyPath: KeyPath<Include, Bool?>) -> Bool {
        include?[keyPath: keyPath] ?? true
    }
}

public struct WeatherCache: Codable {
    public let status: String
    public let forecast_date: String?
    public let fetched_at: String?
    public let high_f: Int?
    public let low_f: Int?
    public let humidity_min_percent: Int?
    public let humidity_max_percent: Int?
    public let rain_probability_percent: Int?
    public let rain_window: String?
    public let snow_expected: Bool?
    public let wind_speed_mph: Int?
    public let wind_gust_mph: Int?
    public let wind_warning: Bool?
}

public struct ReminderConfig: Codable {
    public struct Preset: Codable, Identifiable {
        public let minutes_before: Int
        public let label: String

        public init(minutes_before: Int, label: String) {
            self.minutes_before = minutes_before
            self.label = label
        }

        public var id: Int { minutes_before }
    }

    public let presets: [Preset]

    public init(presets: [Preset]) {
        self.presets = presets
    }
}

public enum JSONValue: Codable {
    case bool(Bool)
    case int(Int)
    case array([JSONValue])
    case object([String: JSONValue])
    case string(String)
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Int.self) {
            self = .int(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            self = .object(try container.decode([String: JSONValue].self))
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .bool(let value): try container.encode(value)
        case .int(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        case .string(let value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }

    public var boolValue: Bool? {
        if case .bool(let value) = self { return value }
        return nil
    }

    public var intArrayValue: [Int]? {
        if case .array(let values) = self {
            return values.compactMap {
                if case .int(let value) = $0 { return value }
                return nil
            }
        }
        return nil
    }
}

public struct EditableEvent: Identifiable, Equatable {
    public var id: String
    public var title: String
    public var date: Date
    public var hour: Int
    public var minute: Int
    public var description: String
    public var reminderOffsets: [Int]
    public var blinkerMinutesBefore: Int?
    public var recurrence: EventRecurrence?
    public var enabled: Bool
    public var attentionLevel: AttentionState
    public var attachments: AttachmentManifest?
    public var seriesID: String?

    public init(
        id: String,
        title: String,
        date: Date,
        hour: Int,
        minute: Int,
        description: String,
        reminderOffsets: [Int],
        enabled: Bool,
        attentionLevel: AttentionState = .green,
        blinkerMinutesBefore: Int? = nil,
        recurrence: EventRecurrence? = nil,
        attachments: AttachmentManifest? = nil,
        seriesID: String? = nil
    ) {
        self.id = id
        self.title = title
        self.date = date
        self.hour = hour
        self.minute = minute
        self.description = description
        self.reminderOffsets = reminderOffsets
        self.blinkerMinutesBefore = blinkerMinutesBefore
        self.recurrence = recurrence
        self.enabled = enabled
        self.attentionLevel = attentionLevel
        self.attachments = attachments
        self.seriesID = seriesID
    }

    public init(event: BlinkEvent) {
        let parsed = parseISODate(event.start) ?? Date()
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = blinkTimeZone
        let parts = calendar.dateComponents([.hour, .minute], from: parsed)
        self.id = event.id
        self.title = event.title
        self.date = parsed
        self.hour = parts.hour ?? 9
        self.minute = parts.minute ?? 0
        self.description = event.description ?? ""
        self.reminderOffsets = event.reminders_minutes_before
        self.blinkerMinutesBefore = event.blinker_minutes_before
        self.recurrence = event.recurrence
        self.enabled = event.enabled
        self.attentionLevel = event.attentionLevel
        self.attachments = event.attachments
        self.seriesID = event.series_id
    }

    public static func blank() -> EditableEvent {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = blinkTimeZone
        let now = Date()
        let nextHour = calendar.date(byAdding: .hour, value: 1, to: now) ?? now
        let parts = calendar.dateComponents([.year, .month, .day, .hour], from: nextHour)
        let date = calendar.date(from: DateComponents(
            timeZone: blinkTimeZone,
            year: parts.year,
            month: parts.month,
            day: parts.day
        )) ?? calendar.startOfDay(for: now)
        return EditableEvent(
            id: "event-\(UUID().uuidString.lowercased())",
            title: "",
            date: date,
            hour: parts.hour ?? 9,
            minute: 0,
            description: "",
            reminderOffsets: [30, 0],
            enabled: true,
            attentionLevel: .green,
            blinkerMinutesBefore: 0,
            recurrence: nil,
            attachments: nil,
            seriesID: nil
        )
    }

    public func toDictionary(now: Date = Date()) -> [String: Any] {
        let start = startDate()
        let reminders = availableReminderOffsets(reminderOffsets, eventStart: start, now: now)
        var output: [String: Any] = [
            "id": id,
            "title": title.trimmingCharacters(in: .whitespacesAndNewlines),
            "start": startISOString(from: start),
            "reminders_minutes_before": reminders,
            "enabled": enabled,
            "requires_done": true,
            "done": false,
            "done_at": NSNull(),
            "attention_level": attentionLevel.rawValue,
            "blinker_minutes_before": blinkerMinutesBefore ?? NSNull()
        ]
        let ownerID = seriesID?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false ? seriesID! : id
        let manifest = attachments ?? AttachmentManifest(ownerID: ownerID, count: 0, hasFiles: false)
        output["attachments"] = manifest.toDictionary()
        if let seriesID, !seriesID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            output["series_id"] = seriesID
        } else if recurrence != nil {
            output["series_id"] = id
        }
        if let recurrence {
            output["recurrence"] = normalizedRecurrence(recurrence, start: start)
        } else {
            output["recurrence"] = NSNull()
        }
        let cleanedDescription = description.trimmingCharacters(in: .whitespacesAndNewlines)
        if !cleanedDescription.isEmpty {
            output["description"] = cleanedDescription
        }
        return output
    }

    private func normalizedRecurrence(_ recurrence: EventRecurrence, start: Date) -> [String: Any] {
        if recurrence.mode == "weekly_fixed" {
            return [
                "mode": "weekly_fixed",
                "weekday": isoWeekday(start),
                "time": clockTimeText(hour: hour, minute: minute)
            ]
        }
        if recurrence.mode == "after_done_days" {
            return [
                "mode": "after_done_days",
                "days": max(recurrence.days ?? 7, 1)
            ]
        }
        return recurrence.toDictionary()
    }

    public func startDate() -> Date {
        var readCalendar = Calendar(identifier: .gregorian)
        readCalendar.timeZone = blinkTimeZone
        let dateParts = readCalendar.dateComponents([.year, .month, .day], from: date)

        var localParts = DateComponents()
        localParts.timeZone = blinkTimeZone
        localParts.year = dateParts.year
        localParts.month = dateParts.month
        localParts.day = dateParts.day
        localParts.hour = hour
        localParts.minute = minute
        localParts.second = 0

        var localCalendar = Calendar(identifier: .gregorian)
        localCalendar.timeZone = blinkTimeZone
        return localCalendar.date(from: localParts) ?? date
    }

    private func startISOString(from localDate: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.timeZone = blinkTimeZone
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: localDate)
    }
}

public enum AttentionState: String, Codable, CaseIterable, Comparable, Sendable {
    case off
    case green
    case yellow
    case red

    private var rank: Int {
        switch self {
        case .off: return 0
        case .green: return 1
        case .yellow: return 2
        case .red: return 3
        }
    }

    public static func < (lhs: AttentionState, rhs: AttentionState) -> Bool {
        lhs.rank < rhs.rank
    }
}

public struct EventSnapshot {
    public let active: [BlinkEvent]
    public let today: [BlinkEvent]
    public let upcoming: [BlinkEvent]
    public let history: [BlinkEvent]
    public let attentionState: AttentionState

    public init(events: [BlinkEvent], now: Date) {
        var active: [BlinkEvent] = []
        var today: [BlinkEvent] = []
        var upcoming: [BlinkEvent] = []
        var history: [BlinkEvent] = []

        for event in events where event.isPersonal {
            guard let start = parseISODate(event.start) else { continue }
            if isActive(event, now: now) {
                active.append(event)
                continue
            }
            if event.requires_done == true {
                if event.done == true {
                    history.append(event)
                } else if start > now {
                    upcoming.append(event)
                    if isSameBlinkDay(start, now) {
                        today.append(event)
                    }
                } else {
                    // Disabling stops attention but must not hide a past event.
                    history.append(event)
                }
                continue
            }
            if start < now {
                history.append(event)
            } else {
                upcoming.append(event)
                if isSameBlinkDay(start, now) {
                    today.append(event)
                }
            }
        }

        self.active = active.sorted { $0.start < $1.start }
        self.today = today.sorted { $0.start < $1.start }
        self.upcoming = upcoming.sorted { $0.start < $1.start }
        self.history = history.sorted { ($0.done_at ?? $0.start) > ($1.done_at ?? $1.start) }
        self.attentionState = events.reduce(.off) { state, event in
            guard attentionEligible(event, now: now) else { return state }
            return max(state, event.attentionLevel)
        }
    }
}

public struct MenuBarSummary {
    public struct Item: Equatable {
        public let title: String
        public let detail: String
        public let attentionState: AttentionState

        public init(title: String, detail: String, attentionState: AttentionState) {
            self.title = title
            self.detail = detail
            self.attentionState = attentionState
        }
    }

    public let statusTitle: String
    public let attentionState: AttentionState
    public let activeItems: [Item]
    public let nextItem: Item?

    public init(snapshot: EventSnapshot) {
        self.attentionState = snapshot.attentionState
        let active = snapshot.active.sorted {
            if $0.attentionLevel != $1.attentionLevel {
                return $0.attentionLevel > $1.attentionLevel
            }
            return $0.start < $1.start
        }
        self.activeItems = active.map {
            Item(
                title: $0.title,
                detail: eventDateTimeLabel($0.start),
                attentionState: $0.attentionLevel
            )
        }
        self.nextItem = snapshot.upcoming.first.map {
            Item(
                title: $0.title,
                detail: eventDateTimeLabel($0.start),
                attentionState: $0.attentionLevel
            )
        }
        self.statusTitle = active.isEmpty ? "● OFF" : "● \(active.count) Active"
    }
}

public func isActive(_ event: BlinkEvent, now: Date) -> Bool {
    guard event.isPersonal,
          event.enabled,
          event.requires_done == true,
          event.done != true,
          let start = parseISODate(event.start)
    else {
        return false
    }
    return start <= now
}

public func attentionEligible(_ event: BlinkEvent, now: Date) -> Bool {
    guard event.isPersonal,
          event.enabled,
          event.requires_done == true,
          event.done != true,
          let start = parseISODate(event.start)
    else {
        return false
    }
    return attentionStartDate(event: event, start: start) <= now
}

public func eventIsHistoryFrozen(_ event: BlinkEvent, now: Date = Date()) -> Bool {
    if event.done == true { return true }
    guard let start = parseISODate(event.start), start < now else { return false }
    if event.requires_done == true && event.enabled && event.done != true {
        return false
    }
    return true
}

public struct BlinkStore {
    public let root: URL

    public init(root: URL? = nil) {
        if let root {
            self.root = root
            return
        }
        if let env = ProcessInfo.processInfo.environment["BLINK_DIR"] {
            self.root = URL(fileURLWithPath: env)
            return
        }
        let localBlinkRoot = URL(fileURLWithPath: "/Users/vitaliiprotsiuk/Desktop/Blink")
        if FileManager.default.fileExists(atPath: localBlinkRoot.appendingPathComponent("agenda.json").path) {
            self.root = localBlinkRoot
            return
        }
        self.root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    public func loadEvents(now: Date = Date()) -> [BlinkEvent] {
        guard var object = try? loadAgendaObject(),
              var rawEvents = object["events"] as? [[String: Any]] else {
            return []
        }
        var repaired = false
        let attachmentWorkspace = AttachmentWorkspace(root: root)
        for index in rawEvents.indices {
            let ownerID = attachmentOwnerID(for: rawEvents[index])
            if let manifest = try? attachmentWorkspace.manifest(ownerID: ownerID) {
                let current = rawEvents[index]["attachments"] as? [String: Any]
                let currentOwner = current?["owner_id"] as? String
                let currentCount = current?["count"] as? Int
                let currentHasFiles = current?["has_files"] as? Bool
                if currentOwner != manifest.ownerID || currentCount != manifest.count || currentHasFiles != manifest.hasFiles {
                    rawEvents[index]["attachments"] = manifest.toDictionary()
                    repaired = true
                }
            }
            guard (rawEvents[index]["source"] as? String ?? "personal") == "personal",
                  rawEvents[index]["requires_done"] as? Bool == true,
                  rawEvents[index]["done"] as? Bool == true,
                  let startText = rawEvents[index]["start"] as? String,
                  let start = parseISODate(startText), start > now else { continue }
            rawEvents[index]["done"] = false
            rawEvents[index]["done_at"] = NSNull()
            repaired = true
        }
        if repaired {
            object["events"] = rawEvents
            try? saveAgendaObject(object)
        }
        guard let data = try? JSONSerialization.data(withJSONObject: object),
              let document = try? JSONDecoder().decode(AgendaDocument.self, from: data) else {
            return []
        }
        return document.events.filter { ($0.source ?? "personal") == "personal" }
    }

    public func loadSnapshot(now: Date = Date()) -> EventSnapshot {
        EventSnapshot(events: loadEvents(now: now), now: now)
    }

    public func attachmentNames(for event: BlinkEvent) -> [String] {
        (try? AttachmentWorkspace(root: root).files(ownerID: event.attachmentOwnerID).map(\.lastPathComponent)) ?? []
    }

    public func loadAstronomyConfig() -> AstronomyConfig? {
        let url = root.appendingPathComponent("astronomy/astronomy_config.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(AstronomyConfig.self, from: data)
    }

    public func loadAstronomySchedule() -> AstronomySchedule? {
        let url = root.appendingPathComponent("astronomy/astronomy_schedule.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(AstronomySchedule.self, from: data)
    }

    public func saveAstronomySettings(_ config: AstronomyConfig) throws {
        let url = root.appendingPathComponent("astronomy/astronomy_config.json")
        var object = try loadJSONObject(url, fallback: ["version": 2])
        let encoded = try JSONEncoder().encode(config)
        let configObject = try JSONSerialization.jsonObject(with: encoded) as? [String: Any] ?? [:]
        object["timezone"] = config.timezone
        var briefing = configObject["briefing"] as? [String: Any] ?? [:]
        briefing["config_changed_at"] = configurationChangedAt(timezoneName: config.timezone)
        object["briefing"] = briefing
        object["notifications"] = configObject["notifications"] ?? [:]
        try saveJSONObject(object, to: url)
    }

    public func loadLocation() -> BlinkLocation? {
        let url = root.appendingPathComponent("location.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(BlinkLocation.self, from: data)
    }

    public func loadWeatherConfig() -> WeatherConfig? {
        let url = root.appendingPathComponent("weather/weather_config.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(WeatherConfig.self, from: data)
    }

    public func loadWeatherCache() -> WeatherCache? {
        let url = root.appendingPathComponent("weather/weather_cache.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(WeatherCache.self, from: data)
    }

    public func loadReminderConfig() -> ReminderConfig {
        let url = root.appendingPathComponent("reminders.json")
        guard let data = try? Data(contentsOf: url),
              let config = try? JSONDecoder().decode(ReminderConfig.self, from: data),
              !config.presets.isEmpty else {
            return defaultReminderConfig()
        }
        return config
    }

    public func saveWeatherEnabled(_ enabled: Bool) throws {
        let url = root.appendingPathComponent("weather/weather_config.json")
        var object = try loadJSONObject(url, fallback: [
            "version": 1,
            "weather_enabled": true,
            "morning_briefing": ["enabled": true, "time": "06:30"],
            "include": defaultWeatherInclude()
        ])
        let previousEnabled = object["weather_enabled"] as? Bool
        object["weather_enabled"] = enabled
        try saveJSONObject(object, to: url)
        if previousEnabled != enabled {
            resetWeatherDeliveryState()
        }
    }

    public func saveWeatherSettings(_ config: WeatherConfig) throws {
        let url = root.appendingPathComponent("weather/weather_config.json")
        var object = try loadJSONObject(url, fallback: [
            "version": 1,
            "weather_enabled": true,
            "morning_briefing": ["enabled": true, "time": "06:30"],
            "include": defaultWeatherInclude()
        ])
        let previousTime = (object["morning_briefing"] as? [String: Any])?["time"] as? String
        let previousEnabled = object["weather_enabled"] as? Bool
        object["weather_enabled"] = config.weather_enabled
        object["morning_briefing"] = [
            "enabled": config.morning_briefing.enabled,
            "time": config.morning_briefing.time
        ]
        object["include"] = [
            "temperature": config.includeValue(\.temperature),
            "humidity": config.includeValue(\.humidity),
            "wind": config.includeValue(\.wind),
            "rain": config.includeValue(\.rain),
            "snow": config.includeValue(\.snow)
        ]
        try saveJSONObject(object, to: url)
        if previousTime != config.morning_briefing.time || previousEnabled != config.weather_enabled {
            resetWeatherDeliveryState()
        }
    }

    private func resetWeatherDeliveryState() {
        let url = root.appendingPathComponent("weather/weather_state.json")
        guard var object = try? loadJSONObject(url, fallback: ["version": 1]) else { return }
        object["last_weather_briefing_date"] = NSNull()
        object["last_weather_briefing_key"] = NSNull()
        object["last_weather_briefing_scheduled_date"] = NSNull()
        object["last_weather_briefing_scheduled_key"] = NSNull()
        object["last_weather_briefing_status"] = "config_changed"
        object["briefing_config_changed_at"] = configurationChangedAt(
            timezoneName: loadLocation()?.timezone ?? blinkTimeZone.identifier
        )
        try? saveJSONObject(object, to: url)
    }

    private func configurationChangedAt(timezoneName: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.timeZone = TimeZone(identifier: timezoneName) ?? blinkTimeZone
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.string(from: Date())
    }

    public func saveLocation(_ location: BlinkLocation) throws {
        guard !location.display_name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              (-90...90).contains(location.latitude),
              (-180...180).contains(location.longitude),
              TimeZone(identifier: location.timezone) != nil else {
            throw NSError(domain: "BlinkLocation", code: 1, userInfo: [NSLocalizedDescriptionKey: "Location has invalid name, coordinates, or timezone."])
        }
        try LocationGeocoder(root: root).validate(location)
        let locationURL = root.appendingPathComponent("location.json")
        let object: [String: Any] = [
            "version": 1,
            "display_name": location.display_name.trimmingCharacters(in: .whitespacesAndNewlines),
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone.trimmingCharacters(in: .whitespacesAndNewlines),
            "coordinate_source": location.coordinate_source ?? "city"
        ]
        try saveJSONObject(object, to: locationURL)
        try invalidateWeatherCache(for: location)
        try updateAstronomyConfig(for: location)
        try invalidateAstronomySchedule(for: location)
    }

    public func save(
        _ event: EditableEvent,
        attachmentWorkspace: AttachmentWorkspace? = nil,
        draftID: String? = nil
    ) throws {
        var document = try loadAgendaObject()
        var events = document["events"] as? [[String: Any]] ?? []
        var newValues = event.toDictionary()
        let existingIndex = events.firstIndex(where: { ($0["id"] as? String) == event.id })
        if let index = existingIndex {
            if rawEventIsHistoryFrozen(events[index]) {
                throw NSError(
                    domain: "BlinkEvent",
                    code: 2,
                    userInfo: [NSLocalizedDescriptionKey: "History events are frozen. Use Duplicate as new event."]
                )
            }
        }
        if let attachmentWorkspace, let draftID {
            let ownerID = event.seriesID?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
                ? event.seriesID!
                : (event.attachments?.ownerID.isEmpty == false ? event.attachments!.ownerID : event.id)
            let manifest = try attachmentWorkspace.finalize(draftID: draftID, ownerID: ownerID)
            newValues["attachments"] = manifest.toDictionary()
        }
        if let index = existingIndex {
            var merged = events[index]
            for (key, value) in newValues {
                merged[key] = value
            }
            events[index] = merged
        } else {
            events.append(newValues)
        }
        document["events"] = events
        try saveAgendaObject(document)
        if let attachmentWorkspace, let draftID {
            try? attachmentWorkspace.discard(draftID: draftID)
        }
    }

    private func rawEventIsHistoryFrozen(_ event: [String: Any], now: Date = Date()) -> Bool {
        if event["done"] as? Bool == true { return true }
        guard let startText = event["start"] as? String,
              let start = parseISODate(startText),
              start < now else { return false }
        let requiresDone = event["requires_done"] as? Bool ?? false
        let enabled = event["enabled"] as? Bool ?? true
        if requiresDone && enabled && event["done"] as? Bool != true {
            return false
        }
        return true
    }

    public func complete(eventID: String, now: Date = Date()) throws {
        var document = try loadAgendaObject()
        var events = document["events"] as? [[String: Any]] ?? []
        guard let index = events.firstIndex(where: { ($0["id"] as? String) == eventID }) else { return }
        events[index]["requires_done"] = true
        events[index]["done"] = true
        events[index]["done_at"] = localISOString(now)
        let generation = (events[index]["generation"] as? Int) ?? 0
        let hasSuccessor = events.contains {
            ($0["recurrence_parent_id"] as? String) == eventID
                && (($0["generation"] as? Int) ?? -1) == generation + 1
        }
        if !hasSuccessor, let next = buildNextRecurringEvent(from: events[index], completedAt: now) {
            events.append(next)
        }
        document["events"] = events
        try saveAgendaObject(document)
    }

    public func setAttentionLevel(eventID: String, level: AttentionState) throws {
        var document = try loadAgendaObject()
        var events = document["events"] as? [[String: Any]] ?? []
        guard let index = events.firstIndex(where: { ($0["id"] as? String) == eventID }) else { return }
        events[index]["attention_level"] = level.rawValue
        document["events"] = events
        try saveAgendaObject(document)
    }

    public func setEnabled(eventID: String, enabled: Bool) throws {
        var document = try loadAgendaObject()
        var events = document["events"] as? [[String: Any]] ?? []
        guard let index = events.firstIndex(where: { ($0["id"] as? String) == eventID }) else { return }
        events[index]["enabled"] = enabled
        document["events"] = events
        try saveAgendaObject(document)
    }

    public func delete(eventID: String) throws {
        var document = try loadAgendaObject()
        let events = document["events"] as? [[String: Any]] ?? []
        let ownerID = events.first(where: { ($0["id"] as? String) == eventID }).flatMap { event in
            let seriesID = (event["series_id"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            return seriesID.isEmpty ? (event["id"] as? String) : seriesID
        }
        let remainingEvents = events.filter { ($0["id"] as? String) != eventID }
        let shouldTrashAttachments = ownerID.map { owner in
            !remainingEvents.contains { attachmentOwnerID(for: $0) == owner }
        } ?? false
        document["events"] = remainingEvents
        try saveAgendaObject(document)
        if shouldTrashAttachments, let ownerID {
            try? AttachmentWorkspace(root: root).moveOwnerToTrash(ownerID: ownerID)
        }
    }

    public func addFiles(eventID: String, urls: [URL]) throws {
        guard !urls.isEmpty else { return }
        var document = try loadAgendaObject()
        var events = document["events"] as? [[String: Any]] ?? []
        guard let index = events.firstIndex(where: { ($0["id"] as? String) == eventID }) else { return }
        let event = events[index]
        let ownerID = attachmentOwnerID(for: event)
        let workspace = AttachmentWorkspace(root: root)
        let draftID = try workspace.createDraft()
        do {
            try workspace.addFiles(urls, to: draftID)
            let manifest = try workspace.finalize(draftID: draftID, ownerID: ownerID)
            events[index]["attachments"] = manifest.toDictionary()
            document["events"] = events
            try saveAgendaObject(document)
            try? workspace.discard(draftID: draftID)
        } catch {
            try? workspace.discard(draftID: draftID)
            throw error
        }
    }

    public func addJPEG(eventID: String, data: Data) throws {
        var document = try loadAgendaObject()
        var events = document["events"] as? [[String: Any]] ?? []
        guard let index = events.firstIndex(where: { ($0["id"] as? String) == eventID }) else { return }
        let event = events[index]
        let ownerID = attachmentOwnerID(for: event)
        let workspace = AttachmentWorkspace(root: root)
        let draftID = try workspace.createDraft()
        do {
            try workspace.addJPEG(data, to: draftID)
            let manifest = try workspace.finalize(draftID: draftID, ownerID: ownerID)
            events[index]["attachments"] = manifest.toDictionary()
            document["events"] = events
            try saveAgendaObject(document)
            try? workspace.discard(draftID: draftID)
        } catch {
            try? workspace.discard(draftID: draftID)
            throw error
        }
    }

    private func attachmentOwnerID(for event: [String: Any]) -> String {
        let seriesID = (event["series_id"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if !seriesID.isEmpty { return seriesID }
        return (event["id"] as? String) ?? "event"
    }

    private var agendaURL: URL {
        root.appendingPathComponent("agenda.json")
    }

    private func loadAgendaObject() throws -> [String: Any] {
        if !FileManager.default.fileExists(atPath: agendaURL.path) {
            return ["version": 1, "events": []]
        }
        let data = try Data(contentsOf: agendaURL)
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? ["version": 1, "events": []]
    }

    private func saveAgendaObject(_ document: [String: Any]) throws {
        try saveJSONObject(document, to: agendaURL)
    }

    private func loadJSONObject(_ url: URL, fallback: [String: Any]) throws -> [String: Any] {
        if !FileManager.default.fileExists(atPath: url.path) {
            return fallback
        }
        let data = try Data(contentsOf: url)
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? fallback
    }

    private func saveJSONObject(_ object: [String: Any], to url: URL) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        var normalized = object
        normalized = normalizeJSONDictionary(normalized)
        let data = try JSONSerialization.data(withJSONObject: normalized, options: [.prettyPrinted, .sortedKeys])
        let temporaryURL = url.deletingLastPathComponent()
            .appendingPathComponent(".\(url.lastPathComponent).\(UUID().uuidString).tmp")
        try data.write(to: temporaryURL, options: .atomic)
        if FileManager.default.fileExists(atPath: url.path) {
            _ = try FileManager.default.replaceItemAt(url, withItemAt: temporaryURL)
        } else {
            try FileManager.default.moveItem(at: temporaryURL, to: url)
        }
    }

    private func invalidateWeatherCache(for location: BlinkLocation) throws {
        let url = root.appendingPathComponent("weather/weather_cache.json")
        var object = try loadJSONObject(url, fallback: ["version": 1])
        object["status"] = "stale_location_changed"
        object["fetched_at"] = NSNull()
        object["forecast"] = NSNull()
        object["location"] = [
            "version": 1,
            "display_name": location.display_name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone
        ]
        try saveJSONObject(object, to: url)
    }

    private func invalidateAstronomySchedule(for location: BlinkLocation) throws {
        let url = root.appendingPathComponent("astronomy/astronomy_schedule.json")
        var object = try loadJSONObject(url, fallback: ["version": 2])
        object["generation_status"] = "needs_regeneration"
        object["daily_records"] = []
        object["location"] = [
            "version": 1,
            "display_name": location.display_name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone
        ]
        object["timezone"] = location.timezone
        try saveJSONObject(object, to: url)
    }

    private func updateAstronomyConfig(for location: BlinkLocation) throws {
        let url = root.appendingPathComponent("astronomy/astronomy_config.json")
        var object = try loadJSONObject(url, fallback: ["version": 2])
        object["location"] = [
            "version": 1,
            "display_name": location.display_name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone
        ]
        object["timezone"] = location.timezone
        try saveJSONObject(object, to: url)
    }

    private func normalizeJSONDictionary(_ object: [String: Any]) -> [String: Any] {
        var result: [String: Any] = [:]
        for (key, value) in object {
            result[key] = normalizeJSONValue(value)
        }
        return result
    }

    private func normalizeJSONValue(_ value: Any) -> Any {
        if let dict = value as? [String: Any] {
            return normalizeJSONDictionary(dict)
        }
        if let array = value as? [Any] {
            return array.map { normalizeJSONValue($0) }
        }
        return value
    }

    private func buildNextRecurringEvent(from event: [String: Any], completedAt: Date) -> [String: Any]? {
        guard let recurrence = event["recurrence"] as? [String: Any],
              let startText = event["start"] as? String,
              let start = parseISODate(startText),
              let mode = recurrence["mode"] as? String else {
            return nil
        }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = blinkTimeZone
        let completedLocal = completedAt
        let startParts = calendar.dateComponents([.hour, .minute], from: start)
        let nextStart: Date?
        if mode == "after_done_days" {
            guard let days = recurrence["days"] as? Int, days > 0,
                  let nextDate = calendar.date(byAdding: .day, value: days, to: completedLocal) else {
                return nil
            }
            let dateParts = calendar.dateComponents([.year, .month, .day], from: nextDate)
            nextStart = calendar.date(from: DateComponents(
                timeZone: blinkTimeZone,
                year: dateParts.year,
                month: dateParts.month,
                day: dateParts.day,
                hour: startParts.hour,
                minute: startParts.minute,
                second: 0
            ))
        } else if mode == "weekly_fixed" {
            guard let weekday = recurrence["weekday"] as? Int,
                  (1...7).contains(weekday) else {
                return nil
            }
            let timeText = recurrence["time"] as? String ?? clockTimeText(
                hour: startParts.hour ?? 9,
                minute: startParts.minute ?? 0
            )
            guard let parsed = parseClockTime(timeText) else { return nil }
            let currentWeekday = isoWeekday(completedLocal, calendar: calendar)
            var daysAhead = (weekday - currentWeekday + 7) % 7
            let candidateBase = calendar.date(byAdding: .day, value: daysAhead, to: completedLocal) ?? completedLocal
            let candidateParts = calendar.dateComponents([.year, .month, .day], from: candidateBase)
            var candidate = calendar.date(from: DateComponents(
                timeZone: blinkTimeZone,
                year: candidateParts.year,
                month: candidateParts.month,
                day: candidateParts.day,
                hour: parsed.hour,
                minute: parsed.minute,
                second: 0
            ))
            if let currentCandidate = candidate, currentCandidate <= completedLocal {
                daysAhead += 7
                let nextBase = calendar.date(byAdding: .day, value: daysAhead, to: completedLocal) ?? completedLocal
                let nextParts = calendar.dateComponents([.year, .month, .day], from: nextBase)
                candidate = calendar.date(from: DateComponents(
                    timeZone: blinkTimeZone,
                    year: nextParts.year,
                    month: nextParts.month,
                    day: nextParts.day,
                    hour: parsed.hour,
                    minute: parsed.minute,
                    second: 0
                ))
            }
            nextStart = candidate
        } else {
            return nil
        }
        guard let nextStart else { return nil }
        var next = event
        let seriesID = (event["series_id"] as? String) ?? (event["id"] as? String ?? "event")
        let generation = ((event["generation"] as? Int) ?? 0) + 1
        next["id"] = "\(seriesID)-g\(generation)"
        next["series_id"] = seriesID
        next["generation"] = generation
        next["recurrence_parent_id"] = event["id"]
        next["start"] = localISOString(nextStart)
        next["requires_done"] = true
        next["done"] = false
        next["done_at"] = NSNull()
        next["enabled"] = true
        next.removeValue(forKey: "snoozed_until")
        next.removeValue(forKey: "snoozed_for_minutes")
        next.removeValue(forKey: "template_id")
        return next
    }

    private func isoWeekday(_ date: Date, calendar: Calendar) -> Int {
        let weekday = calendar.component(.weekday, from: date)
        return weekday == 1 ? 7 : weekday - 1
    }

    private func defaultWeatherInclude() -> [String: Bool] {
        [
            "temperature": true,
            "humidity": true,
            "wind": true,
            "rain": true,
            "snow": true
        ]
    }
}

public let blinkTimeZone = TimeZone(identifier: "America/Los_Angeles")!
public let reminderChoices = [1440, 720, 300, 60, 30, 10, 5, 0]
public func defaultReminderConfig() -> ReminderConfig {
    ReminderConfig(presets: [
        .init(minutes_before: 1440, label: "1 day before"),
        .init(minutes_before: 720, label: "12 hours before"),
        .init(minutes_before: 300, label: "5 hours before"),
        .init(minutes_before: 60, label: "60 min before"),
        .init(minutes_before: 30, label: "30 min before"),
        .init(minutes_before: 10, label: "10 min before"),
        .init(minutes_before: 5, label: "5 min before"),
        .init(minutes_before: 0, label: "At time")
    ])
}

public let commonTimezones = TimeZone.knownTimeZoneIdentifiers.sorted()

public func isReminderOffsetAvailable(_ minutes: Int, eventStart: Date, now: Date = Date()) -> Bool {
    let secondsUntilStart = eventStart.timeIntervalSince(now)
    if secondsUntilStart < 0 {
        return false
    }
    let minutesUntilStart = Int(ceil(secondsUntilStart / 60.0))
    return minutes <= minutesUntilStart
}

public func attentionStartDate(event: BlinkEvent) -> Date? {
    guard let start = parseISODate(event.start) else { return nil }
    return attentionStartDate(event: event, start: start)
}

public func attentionStartDate(event: BlinkEvent, start: Date) -> Date {
    Calendar(identifier: .gregorian).date(
        byAdding: .minute,
        value: -event.blinkerMinutesBefore,
        to: start
    ) ?? start
}

public func matchesEventSearch(_ event: BlinkEvent, query: String, attachmentNames: [String] = []) -> Bool {
    let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.isEmpty {
        return true
    }
    let status: String
    if event.done == true {
        status = "done history completed"
    } else if event.enabled {
        status = "active upcoming enabled"
    } else {
        status = "off disabled"
    }
    let haystack = [
        event.title,
        event.description ?? "",
        eventDateTimeLabel(event.start),
        dateLabel(parseISODate(event.start) ?? Date()),
        status,
        event.attention_level ?? "",
        attachmentNames.joined(separator: " ")
    ].joined(separator: " ").lowercased()
    return haystack.contains(trimmed.lowercased())
}

public func availableReminderOffsets(_ offsets: [Int], eventStart: Date, now: Date = Date()) -> [Int] {
    Array(Set(offsets))
        .filter { $0 >= 0 && isReminderOffsetAvailable($0, eventStart: eventStart, now: now) }
        .sorted(by: >)
}

public func parseISODate(_ value: String) -> Date? {
    ISO8601DateFormatter().date(from: value)
}

public func isoWeekday(_ date: Date) -> Int {
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = blinkTimeZone
    let weekday = calendar.component(.weekday, from: date)
    return weekday == 1 ? 7 : weekday - 1
}

public func timeLabel(_ value: String) -> String {
    guard let date = parseISODate(value) else { return value }
    let formatter = DateFormatter()
    formatter.timeZone = blinkTimeZone
    formatter.dateFormat = "HH:mm"
    return formatter.string(from: date)
}

public func eventDateTimeLabel(_ value: String) -> String {
    guard let date = parseISODate(value) else { return value }
    let formatter = DateFormatter()
    formatter.timeZone = blinkTimeZone
    formatter.dateFormat = "MMM d, yyyy HH:mm"
    return formatter.string(from: date)
}

public func dateLabel(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.timeZone = blinkTimeZone
    formatter.dateStyle = .medium
    formatter.timeStyle = .none
    return formatter.string(from: date)
}

public func localISOString(_ date: Date) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.timeZone = blinkTimeZone
    formatter.formatOptions = [.withInternetDateTime]
    return formatter.string(from: date)
}

public func timeStringToDate(_ value: String) -> Date {
    let parts = value.split(separator: ":", maxSplits: 1).compactMap { Int($0) }
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = blinkTimeZone
    var components = calendar.dateComponents([.year, .month, .day], from: Date())
    components.timeZone = blinkTimeZone
    components.hour = parts.indices.contains(0) ? min(max(parts[0], 0), 23) : 6
    components.minute = parts.indices.contains(1) ? min(max(parts[1], 0), 59) : 30
    components.second = 0
    return calendar.date(from: components) ?? Date()
}

public func timeString(from date: Date) -> String {
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = blinkTimeZone
    let parts = calendar.dateComponents([.hour, .minute], from: date)
    return String(format: "%02d:%02d", parts.hour ?? 0, parts.minute ?? 0)
}

public func clockTimeText(hour: Int, minute: Int) -> String {
    String(format: "%02d:%02d", min(max(hour, 0), 23), min(max(minute, 0), 59))
}

public let timeInputWidth: CGFloat = 112

public func saveButtonOpacity(hasUnsavedChanges: Bool) -> Double {
    hasUnsavedChanges ? 1.0 : 0.45
}

public func saveButtonTitle(defaultTitle: String, saved: Bool) -> String {
    saved ? "Saved" : defaultTitle
}

public func parseClockTime(_ value: String) -> (hour: Int, minute: Int)? {
    let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
    let parts = trimmed.split(separator: ":", maxSplits: 1)
    guard parts.count == 2,
          let hour = Int(parts[0]),
          let minute = Int(parts[1]),
          (0...23).contains(hour),
          (0...59).contains(minute) else {
        return nil
    }
    return (hour, minute)
}

public func isSameBlinkDay(_ lhs: Date, _ rhs: Date) -> Bool {
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = blinkTimeZone
    return calendar.isDate(lhs, inSameDayAs: rhs)
}
