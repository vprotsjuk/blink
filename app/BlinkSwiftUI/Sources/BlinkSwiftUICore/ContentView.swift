import SwiftUI
import AppKit
import UniformTypeIdentifiers

public enum BlinkDesign {
    public static let pagePadding: CGFloat = 18
    public static let cardPadding: CGFloat = 14
    public static let cardRadius: CGFloat = 8
    public static let fieldWidth: CGFloat = 112
}

private let eventEditorModalHeight: CGFloat = 720

extension View {
    func blinkSettingsCard() -> some View {
        self
            .padding(BlinkDesign.cardPadding)
            .background(.quaternary.opacity(0.28), in: RoundedRectangle(cornerRadius: BlinkDesign.cardRadius))
    }

    func eventEditorFieldCard() -> some View {
        self
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(
                .background.opacity(0.78),
                in: RoundedRectangle(cornerRadius: 12, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Color.primary.opacity(0.14), lineWidth: 1)
            }
    }
}

private enum BlinkTab: Hashable {
    case today
    case upcoming
    case history
    case astronomy
    case weather
    case location
    case health
}

private struct BlinkTabButton: View {
    let title: String
    let selected: Bool
    let attentionColor: Color?
    let pulseVisible: Bool
    let action: () -> Void
    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .foregroundStyle(displayColor)
                .padding(.horizontal, 14)
                .padding(.vertical, 7)
                .background(
                    selected
                        ? Color.primary.opacity(0.12)
                        : (isHovered ? Color.primary.opacity(0.07) : .clear),
                    in: Capsule()
                )
                .animation(.easeInOut(duration: 0.3), value: pulseVisible)
        }
        .buttonStyle(.plain)
        .onHover { isHovered in
            self.isHovered = isHovered
        }
    }

    private var displayColor: Color {
        guard let attentionColor else { return .primary }
        return pulseVisible ? attentionColor : .primary
    }
}

private struct BlinkTabBar: View {
    @Binding var selectedTab: BlinkTab
    let todayAttentionColor: Color?
    let pulseVisible: Bool

    var body: some View {
        HStack(spacing: 2) {
            BlinkTabButton(
                title: "Today",
                selected: selectedTab == .today,
                attentionColor: todayAttentionColor,
                pulseVisible: pulseVisible
            ) {
                selectedTab = .today
            }
            BlinkTabButton(title: "Upcoming", selected: selectedTab == .upcoming, attentionColor: nil, pulseVisible: true) { selectedTab = .upcoming }
            BlinkTabButton(title: "History", selected: selectedTab == .history, attentionColor: nil, pulseVisible: true) { selectedTab = .history }
            BlinkTabButton(title: "Astronomy", selected: selectedTab == .astronomy, attentionColor: nil, pulseVisible: true) { selectedTab = .astronomy }
            BlinkTabButton(title: "Weather", selected: selectedTab == .weather, attentionColor: nil, pulseVisible: true) { selectedTab = .weather }
            BlinkTabButton(title: "Location", selected: selectedTab == .location, attentionColor: nil, pulseVisible: true) { selectedTab = .location }
            BlinkTabButton(title: "Health", selected: selectedTab == .health, attentionColor: nil, pulseVisible: true) { selectedTab = .health }
        }
    }
}

private struct BlinkTopToolbar: ToolbarContent {
    @Binding var selectedTab: BlinkTab
    let todayAttentionColor: Color?
    let pulseVisible: Bool
    @Binding var searchQuery: String

    var body: some ToolbarContent {
        ToolbarItem(placement: .principal) {
            BlinkTabBar(
                selectedTab: $selectedTab,
                todayAttentionColor: todayAttentionColor,
                pulseVisible: pulseVisible
            )
        }
        ToolbarItemGroup(placement: .automatic) {
            TextField("Search", text: $searchQuery)
                .textFieldStyle(.roundedBorder)
                .frame(width: 220)
        }
    }
}

public struct ContentView: View {
    let store: BlinkStore
    let attentionManager: AttentionManager?
    let newEventToken: UUID?
    let onSnapshotChange: ((EventSnapshot) -> Void)?
    @State private var events: [BlinkEvent] = []
    @State private var snapshot = EventSnapshot(events: [], now: Date())
    @State private var eventLoadState: EventLoadState = .error
    @State private var eventLoadError: String?
    @State private var eventSourcePath = ""
    @State private var eventLastSuccessfulLoad: Date?
    @State private var hasLoadedEventSnapshot = false
    @State private var astronomyConfig: AstronomyConfig?
    @State private var astronomySchedule: AstronomySchedule?
    @State private var blinkLocation: BlinkLocation?
    @State private var weatherConfig: WeatherConfig?
    @State private var weatherCache: WeatherCache?
    @State private var reminderConfig = defaultReminderConfig()
    @State private var editorEvent: EditableEvent?
    @State private var editorAttachmentWorkspace: AttachmentWorkspace?
    @State private var editorDraftID: String?
    @State private var editorIsDirty = false
    @State private var locationEditor: EditableLocation?
    @State private var searchQuery = ""
    @State private var errorMessage: String?
    @State private var feedbackMessage: String?
    @State private var pendingDelete: BlinkEvent?
    @State private var attentionPulseOn = true
    @State private var selectedTab: BlinkTab = .today

    public init(
        store: BlinkStore,
        attentionManager: AttentionManager? = nil,
        newEventToken: UUID? = nil,
        onSnapshotChange: ((EventSnapshot) -> Void)? = nil
    ) {
        self.store = store
        self.attentionManager = attentionManager
        self.newEventToken = newEventToken
        self.onSnapshotChange = onSnapshotChange
    }

    public var body: some View {
        ZStack {
            pageContent
            eventEditorOverlay
        }
        .toolbar {
            BlinkTopToolbar(
                selectedTab: $selectedTab,
                todayAttentionColor: todayTabAttentionColor,
                pulseVisible: attentionPulseOn,
                searchQuery: $searchQuery
            )
        }
        .sheet(item: $locationEditor) { location in
            LocationEditorView(location: location, resolverRoot: store.root) { savedLocation in
                perform {
                    try store.saveLocation(savedLocation.toLocation())
                    reload()
                    locationEditor = nil
                }
            }
            .frame(minWidth: 620, minHeight: 460)
        }
        .alert("Blink", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK") { errorMessage = nil }
        } message: {
            Text(errorMessage ?? "")
        }
        .overlay(alignment: .bottom) {
            if let feedbackMessage {
                Text(feedbackMessage)
                    .font(.callout.weight(.medium))
                    .padding(.horizontal, 14)
                    .padding(.vertical, 9)
                    .background(.regularMaterial, in: Capsule())
                    .shadow(radius: 8)
                    .padding(.bottom, 14)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .confirmationDialog(
            "Delete event?",
            isPresented: Binding(
                get: { pendingDelete != nil },
                set: { if !$0 { pendingDelete = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                guard let event = pendingDelete else { return }
                pendingDelete = nil
                perform {
                    try store.delete(eventID: event.id)
                    reload()
                }
            }
            Button("Cancel", role: .cancel) { pendingDelete = nil }
        } message: {
            Text(pendingDelete?.hasAttachments == true
                ? "The event will be removed and its Blink attachments moved to Trash."
                : "The event will be removed from Blink.")
        }
        .onAppear(perform: reload)
        .onChange(of: newEventToken) {
            guard newEventToken != nil else { return }
            openEditor(EditableEvent.blank())
        }
        .onReceive(Timer.publish(every: 30, on: .main, in: .common).autoconnect()) { _ in
            reload()
        }
        .onReceive(Timer.publish(every: 0.7, on: .main, in: .common).autoconnect()) { _ in
            if snapshot.active.isEmpty {
                attentionPulseOn = true
            } else {
                attentionPulseOn.toggle()
            }
        }
    }

    @ViewBuilder
    private var eventEditorOverlay: some View {
        if let event = editorEvent {
            Color.black.opacity(0.22)
                .ignoresSafeArea()
                .onTapGesture {
                    if shouldDismissEventEditorOnBackdropTap(editorIsDirty: editorIsDirty) {
                        closeEditor()
                    }
                }
            EventEditorView(
                event: event,
                reminderConfig: reminderConfig,
                // Keep the preview backed by the project-local workspace even
                // while SwiftUI is settling the editor state assignment.
                attachmentWorkspace: editorAttachmentWorkspace ?? AttachmentWorkspace(root: store.root),
                draftID: editorDraftID,
                onDirtyChange: { editorIsDirty = $0 },
                onCancel: { closeEditor() },
                onOpenAttachments: {
                    let workspace = editorAttachmentWorkspace ?? AttachmentWorkspace(root: store.root)
                    if let draftID = editorDraftID, !events.contains(where: { $0.id == event.id }) {
                        NSWorkspace.shared.open(workspace.draftURL(draftID))
                    } else {
                        _ = try? workspace.ensureAttachmentFolder(ownerID: event.id)
                        NSWorkspace.shared.open(workspace.attachmentURL(ownerID: event.id))
                    }
                }
            ) { savedEvent, pendingRemovedNames in
                perform {
                    let workspace = editorAttachmentWorkspace
                    for name in pendingRemovedNames {
                        let fileURL = workspace?.attachmentURL(ownerID: savedEvent.id).appendingPathComponent(name)
                        if let fileURL { try? workspace?.moveFileToTrash(fileURL, ownerID: savedEvent.id) }
                    }
                    try store.save(
                        savedEvent,
                        attachmentWorkspace: editorAttachmentWorkspace,
                        draftID: editorDraftID
                    )
                    reload()
                    closeEditor(discardDraft: false)
                }
            }
            .frame(width: 760, height: eventEditorModalHeight)
            .background(.regularMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
            .shadow(radius: 18)
        }
    }

    @ViewBuilder
    private var pageContent: some View {
        Group {
            switch selectedTab {
            case .today:
                VStack(alignment: .leading, spacing: 10) {
                    eventLoadBanner
                    TodayView(
                        snapshot: snapshot,
                        actions: actions,
                        searchQuery: searchQuery,
                        attachmentNames: { store.attachmentNames(for: $0) },
                        attachmentRoot: store.root,
                        activeEventIDs: activeEventIDs,
                        pulseVisible: attentionPulseOn
                    )
                }
            case .upcoming:
                VStack(alignment: .leading, spacing: 10) {
                    eventLoadBanner
                    EventListView(
                        title: "Upcoming",
                        events: filtered(snapshot.upcoming),
                        actions: actions,
                        attachmentRoot: store.root,
                        activeEventIDs: activeEventIDs,
                        pulseVisible: attentionPulseOn
                    )
                }
            case .history:
                VStack(alignment: .leading, spacing: 10) {
                    eventLoadBanner
                    EventListView(
                        title: "History",
                        events: filtered(snapshot.history),
                        actions: actions,
                        attachmentRoot: store.root,
                        activeEventIDs: activeEventIDs,
                        pulseVisible: attentionPulseOn
                    )
                }
            case .astronomy:
                AstronomySettingsView(config: astronomyConfig, schedule: astronomySchedule) { updatedConfig in
                    perform {
                        try store.saveAstronomySettings(updatedConfig)
                        reload()
                    }
                }
            case .weather:
                WeatherView(config: weatherConfig, cache: weatherCache) { updatedConfig in
                    perform {
                        try store.saveWeatherSettings(updatedConfig)
                        reload()
                    }
                }
            case .location:
                LocationView(location: blinkLocation) {
                    if let blinkLocation {
                        locationEditor = EditableLocation(location: blinkLocation)
                    }
                }
            case .health:
                SystemHealthView(
                    root: store.root,
                    eventLoadState: eventLoadState,
                    eventCount: events.count,
                    eventSourcePath: eventSourcePath,
                    eventLastSuccessfulLoad: eventLastSuccessfulLoad,
                    eventLoadError: eventLoadError
                )
            }
        }
        .padding(18)
    }

    @ViewBuilder
    private var eventLoadBanner: some View {
        if !hasLoadedEventSnapshot {
            Label(
                eventLoadState == .error ? "Couldn’t refresh events" : "Loading events…",
                systemImage: eventLoadState == .error ? "exclamationmark.triangle" : "arrow.clockwise"
            )
            .foregroundStyle(eventLoadState == .error ? .red : .secondary)
        } else if eventLoadState == .error {
            Label("Couldn’t refresh events — showing last loaded data", systemImage: "exclamationmark.triangle")
                .foregroundStyle(.orange)
        }
    }

    private var actions: EventRowActions {
        EventRowActions(
            newEvent: { openEditor(EditableEvent.blank()) },
            edit: { event in
                guard !eventIsHistoryFrozen(event) else { return }
                openEditor(EditableEvent(event: event))
            },
            duplicate: { event in
                openEditor(duplicateEditableEvent(from: event))
            },
            duplicateWithAttachments: { event in
                duplicateWithAttachments(from: event)
            },
            addFiles: { event in
                chooseFiles(for: event)
            },
            paste: { event in
                paste(for: event)
            },
            openAttachments: { event in
                openAttachmentsFolder(for: event)
            },
            done: { event in
                perform {
                    try store.complete(eventID: event.id)
                    reload()
                }
            },
            toggle: { event in
                perform {
                    try store.setEnabled(eventID: event.id, enabled: !event.enabled)
                    reload()
                }
            },
            delete: { event in
                pendingDelete = event
            }
        )
    }

    private func openEditor(_ event: EditableEvent, workspace: AttachmentWorkspace? = nil, draftID: String? = nil) {
        editorIsDirty = false
        let resolvedWorkspace = workspace ?? AttachmentWorkspace(root: store.root)
        let resolvedDraftID: String?
        if let draftID {
            resolvedDraftID = draftID
        } else {
            resolvedDraftID = try? resolvedWorkspace.createDraft()
        }
        editorAttachmentWorkspace = resolvedWorkspace
        editorDraftID = resolvedDraftID
        editorEvent = event
    }

    private func closeEditor(discardDraft: Bool = true) {
        if discardDraft,
           let workspace = editorAttachmentWorkspace,
           let draftID = editorDraftID {
            try? workspace.discard(draftID: draftID)
        }
        editorEvent = nil
        editorAttachmentWorkspace = nil
        editorDraftID = nil
        editorIsDirty = false
    }

    private func duplicateEditableEvent(from event: BlinkEvent) -> EditableEvent {
        var duplicate = EditableEvent(event: event)
        duplicate.id = "event-\(UUID().uuidString.lowercased())"
        duplicate.attachments = nil
        duplicate.seriesID = nil
        duplicate.recurrence = nil
        duplicate.enabled = true
        return duplicate
    }

    private func duplicateWithAttachments(from event: BlinkEvent) {
        let duplicate = duplicateEditableEvent(from: event)
        let workspace = AttachmentWorkspace(root: store.root)
        guard let draftID = try? workspace.createDraft() else { return }
        let sourceFiles = (try? workspace.files(ownerID: event.id)) ?? []
        do {
            try workspace.addFiles(sourceFiles, to: draftID)
            openEditor(duplicate, workspace: workspace, draftID: draftID)
        } catch {
            try? workspace.discard(draftID: draftID)
            errorMessage = error.localizedDescription
        }
    }

    private func chooseFiles(for event: BlinkEvent) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        guard panel.runModal() == .OK, !panel.urls.isEmpty else { return }
        perform {
            try store.addFiles(eventID: event.id, urls: panel.urls)
            reload()
            showFeedback("✓ Attached \(panel.urls.count) file\(panel.urls.count == 1 ? "" : "s")")
        }
    }

    private func paste(for event: BlinkEvent) {
        let urls = clipboardFileURLs()
        if !urls.isEmpty {
            perform {
                try store.addFiles(eventID: event.id, urls: urls)
                reload()
                showFeedback("✓ Attached \(urls.count) file\(urls.count == 1 ? "" : "s")")
            }
        } else if let imageData = clipboardJPEGData() {
            perform {
                try store.addJPEG(eventID: event.id, data: imageData)
                reload()
                showFeedback("✓ Attached image")
            }
        }
    }

    private func openAttachmentsFolder(for event: BlinkEvent) {
        let workspace = AttachmentWorkspace(root: store.root)
        if !eventIsHistoryFrozen(event) {
            _ = try? workspace.ensureAttachmentFolder(ownerID: event.id)
        }
        NSWorkspace.shared.open(workspace.attachmentURL(ownerID: event.id))
    }

    private func filtered(_ source: [BlinkEvent]) -> [BlinkEvent] {
        source.filter { matchesEventSearch($0, query: searchQuery, attachmentNames: store.attachmentNames(for: $0)) }
    }

    private var activeEventIDs: Set<String> {
        Set(snapshot.active.map(\.id))
    }

    private var todayTabAttentionColor: Color? {
        snapshot.active.isEmpty ? nil : color(for: snapshot.attentionState)
    }

    private func reload() {
        let result = store.loadEventResult()
        eventLoadState = result.state
        eventSourcePath = result.sourcePath
        eventLoadError = result.errorMessage
        if result.state == .loaded {
            events = result.events
            snapshot = EventSnapshot(events: events, now: Date())
            eventLastSuccessfulLoad = result.loadedAt
            hasLoadedEventSnapshot = true
            attentionManager?.setState(snapshot.attentionState)
            onSnapshotChange?(snapshot)
        }
        astronomyConfig = store.loadAstronomyConfig()
        astronomySchedule = store.loadAstronomySchedule()
        blinkLocation = store.loadLocation()
        weatherConfig = store.loadWeatherConfig()
        weatherCache = store.loadWeatherCache()
        reminderConfig = store.loadReminderConfig()
    }

    @discardableResult
    private func perform(_ action: () throws -> Void) -> Bool {
        do {
            try action()
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    private func showFeedback(_ message: String) {
        withAnimation { feedbackMessage = message }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
            guard feedbackMessage == message else { return }
            withAnimation { feedbackMessage = nil }
        }
    }

}

struct SystemHealthView: View {
    let root: URL
    let eventLoadState: EventLoadState
    let eventCount: Int
    let eventSourcePath: String
    let eventLastSuccessfulLoad: Date?
    let eventLoadError: String?
    @State private var rows: [(String, String)] = []

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Label("System Health", systemImage: "heart.text.square.fill")
                    .font(.title.bold())
                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                    HStack {
                        Text(row.0)
                        Spacer()
                        Text(row.1).foregroundStyle(.secondary)
                    }
                    Divider()
                }
                if rows.isEmpty {
                    Text("No diagnostics available").foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .onAppear(perform: refresh)
        .onChange(of: eventLoadState) { refresh() }
        .onChange(of: eventCount) { refresh() }
        .onReceive(Timer.publish(every: 30, on: .main, in: .common).autoconnect()) { _ in
            refresh()
        }
    }

    private func refresh() {
        rows = [
            ("Events", eventLoadState == .loaded ? "Loaded (\(eventCount))" : "Error / stale"),
            ("Events source", eventSourcePath.isEmpty ? root.appendingPathComponent("agenda.json").path : eventSourcePath),
            ("Events last successful load", eventLastSuccessfulLoad.map(eventHealthDateLabel) ?? "None"),
            ("Events last error", eventLoadError ?? "None"),
            ("Watcher", status(from: "watcher_runtime.json", key: "last_heartbeat_at")),
            ("Weather", status(from: "weather/weather_state.json", key: "status")),
            ("Astronomy", status(from: "astronomy/astronomy_schedule.json", key: "generation_status")),
            ("Remote queue", status(from: "n" + "tfy_schedule_state.json", key: "status")),
            ("Location", status(from: "location.json", key: "display_name"))
        ]
    }

    private func eventHealthDateLabel(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateStyle = .medium
        formatter.timeStyle = .medium
        return formatter.string(from: date)
    }

    private func status(from path: String, key: String) -> String {
        let url = root.appendingPathComponent(path)
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let value = object[key] else {
            return "Unavailable"
        }
        return String(describing: value)
    }
}

struct TodayView: View {
    let snapshot: EventSnapshot
    let actions: EventRowActions
    let searchQuery: String
    let attachmentNames: (BlinkEvent) -> [String]
    let attachmentRoot: URL
    let activeEventIDs: Set<String>
    let pulseVisible: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Button(action: actions.newEvent) {
                    Image(systemName: "plus")
                        .font(.headline.weight(.bold))
                        .foregroundStyle(.white)
                        .frame(width: 30, height: 30)
                        .background(Color.accentColor, in: Circle())
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .help("New Event")
                Text("Today").font(.title.bold())
            }
            Text("Active").font(.headline)
            EventRows(
                events: filtered(snapshot.active),
                actions: actions,
                attachmentRoot: attachmentRoot,
                activeEventIDs: activeEventIDs,
                pulseVisible: pulseVisible,
                showsDone: true
            )
            Divider()
            Text("Today's Events").font(.headline)
            EventRows(
                events: filtered(snapshot.today),
                actions: actions,
                attachmentRoot: attachmentRoot,
                activeEventIDs: activeEventIDs,
                pulseVisible: pulseVisible,
            )
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func filtered(_ source: [BlinkEvent]) -> [BlinkEvent] {
        source.filter { matchesEventSearch($0, query: searchQuery, attachmentNames: attachmentNames($0)) }
    }
}

struct EventListView: View {
    let title: String
    let events: [BlinkEvent]
    let actions: EventRowActions
    let attachmentRoot: URL
    let activeEventIDs: Set<String>
    let pulseVisible: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title).font(.title.bold())
            EventRows(
                events: events,
                actions: actions,
                attachmentRoot: attachmentRoot,
                activeEventIDs: activeEventIDs,
                pulseVisible: pulseVisible,
                showsToggle: title != "History",
                showsHistory: title == "History"
            )
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct EventRows: View {
    let events: [BlinkEvent]
    let actions: EventRowActions
    let attachmentRoot: URL
    let activeEventIDs: Set<String>
    let pulseVisible: Bool
    var showsDone = false
    var showsToggle = true
    var showsHistory = false

    var body: some View {
        if events.isEmpty {
            Text("No events").foregroundStyle(.secondary)
        } else {
            List(events) { event in
                EventRowView(
                    event: event,
                    actions: actions,
                    attachmentRoot: attachmentRoot,
                    activeEventIDs: activeEventIDs,
                    pulseVisible: pulseVisible,
                    showsDone: showsDone,
                    showsToggle: showsToggle,
                    showsHistory: showsHistory,
                    rowContentOpacity: rowContentOpacity(for:)
                )
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func rowContentOpacity(for event: BlinkEvent) -> Double {
        guard event.enabled else { return 0.42 }
        guard activeEventIDs.contains(event.id) else { return 1 }
        return pulseVisible ? 1 : 0.35
    }
}

private struct EventRowView: View {
    let event: BlinkEvent
    let actions: EventRowActions
    let attachmentRoot: URL
    let activeEventIDs: Set<String>
    let pulseVisible: Bool
    let showsDone: Bool
    let showsToggle: Bool
    let showsHistory: Bool
    let rowContentOpacity: (BlinkEvent) -> Double
    @State private var isHovered = false
    @State private var showAttachmentPopover = false

    var body: some View {
        HStack {
            rowContent
            Spacer()
            if showsDone {
                Button("Done") { actions.done(event) }
                    .buttonStyle(.borderedProminent)
            }
            if !showsHistory || event.hasAttachments {
                Button { actions.openAttachments(event) } label: {
                    Image(systemName: "folder")
                }
                .buttonStyle(.bordered)
                .help("Open Attachments Folder")
            }
            if showsToggle {
                Button(event.enabled ? "On" : "Off") { actions.toggle(event) }
                    .buttonStyle(.bordered)
                    .foregroundStyle(event.enabled ? .green : .red)
            }
            if !showsHistory {
                Button("Edit") { actions.edit(event) }
                    .buttonStyle(.bordered)
            }
            Button("Delete", role: .destructive) { actions.delete(event) }
                .buttonStyle(.bordered)
        }
        .padding(.vertical, 4)
        .background(isHovered ? Color.primary.opacity(0.06) : .clear, in: RoundedRectangle(cornerRadius: 6))
        .contentShape(Rectangle())
        .simultaneousGesture(TapGesture(count: 2).onEnded {
            if !showsHistory { actions.edit(event) }
        })
        .onHover { isHovered = $0 }
        .contextMenu {
            if !showsHistory {
                Button("Edit") { actions.edit(event) }
                Button("Add Files") { actions.addFiles(event) }
                if clipboardAttachmentAvailable() {
                    Button("Paste") { actions.paste(event) }
                }
            }
            Button("Duplicate as new event") { actions.duplicate(event) }
            if event.hasAttachments {
                Button("Duplicate with Attachments") { actions.duplicateWithAttachments(event) }
            }
            if !showsHistory || event.hasAttachments {
                Button("Open Attachments Folder") { actions.openAttachments(event) }
            }
            if showsDone {
                Button("Done") { actions.done(event) }
            }
            if showsToggle {
                Button(event.enabled ? "Turn Off" : "Turn On") { actions.toggle(event) }
            }
            Button("Delete", role: .destructive) { actions.delete(event) }
        }
    }

    private var rowContent: some View {
        HStack {
            Text(eventDateTimeLabel(event.start))
                .font(.system(.body, design: .monospaced))
                .frame(width: 150, alignment: .leading)
            Circle()
                .fill(color(for: event.attentionLevel))
                .frame(width: 12, height: 12)
            VStack(alignment: .leading) {
                HStack(spacing: 6) {
                    Text(event.title)
                    if event.hasAttachments {
                        Button {
                            showAttachmentPopover.toggle()
                        } label: {
                            Text("📎 \(event.attachments?.count ?? 0)")
                        }
                        .buttonStyle(.plain)
                        .popover(isPresented: $showAttachmentPopover) {
                            AttachmentPopover(root: attachmentRoot, ownerID: event.id) {
                                actions.openAttachments(event)
                            }
                        }
                    }
                }
                if let description = event.description, !description.isEmpty {
                    Text(description).foregroundStyle(.secondary).lineLimit(2)
                }
            }
        }
        .opacity(rowContentOpacity(event))
        .animation(.easeInOut(duration: 0.3), value: pulseVisible)
    }
}

private struct AttachmentPreviewItem: Identifiable {
    let url: URL
    let isDraft: Bool

    var id: String { "\(isDraft ? "draft" : "saved"):\(url.path)" }
}

private struct AttachmentPopover: View {
    let root: URL
    let ownerID: String
    let openFolder: () -> Void
    @State private var files: [URL] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Attachments").font(.headline)
            if files.isEmpty {
                Text("No attachments").foregroundStyle(.secondary)
            } else {
                ForEach(files, id: \.self) { file in
                    HStack(spacing: 8) {
                        Image(systemName: attachmentSymbol(for: file)).foregroundStyle(.secondary)
                        Text(file.lastPathComponent).lineLimit(1).truncationMode(.middle)
                        Spacer(minLength: 4)
                    }
                }
            }
            Button("Open Attachments Folder", action: openFolder)
        }
        .padding(14)
        .frame(minWidth: 260, maxWidth: 360)
        .onAppear { files = (try? AttachmentWorkspace(root: root).files(ownerID: ownerID)) ?? [] }
    }
}

private struct AttachmentPreviewList: View {
    let workspace: AttachmentWorkspace?
    let draftID: String?
    let ownerID: String
    let refreshToken: Int
    let hiddenSavedNames: Set<String>
    let onRemoveSaved: (String) -> Void
    let onChange: () -> Void
    @State private var items: [AttachmentPreviewItem] = []

    init(
        workspace: AttachmentWorkspace?,
        draftID: String?,
        ownerID: String,
        refreshToken: Int,
        hiddenSavedNames: Set<String>,
        onRemoveSaved: @escaping (String) -> Void,
        onChange: @escaping () -> Void
    ) {
        self.workspace = workspace
        self.draftID = draftID
        self.ownerID = ownerID
        self.refreshToken = refreshToken
        self.hiddenSavedNames = hiddenSavedNames
        self.onRemoveSaved = onRemoveSaved
        self.onChange = onChange
        self._items = State(initialValue: Self.loadItems(
            workspace: workspace,
            draftID: draftID,
            ownerID: ownerID,
            hiddenSavedNames: hiddenSavedNames
        ))
    }

    var body: some View {
        Group {
            if items.isEmpty {
                EmptyView()
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(items) { item in
                            HStack(spacing: 8) {
                                AttachmentThumbnail(url: item.url)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(item.url.lastPathComponent)
                                        .lineLimit(1)
                                        .truncationMode(.middle)
                                    Text(fileTypeLabel(item.url))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Text(fileSizeLabel(item.url))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer(minLength: 4)
                                Button("Remove") {
                                    if item.isDraft {
                                        guard let workspace, let draftID else { return }
                                        try? workspace.removeDraftFile(item.url, draftID: draftID)
                                    } else {
                                        onRemoveSaved(item.url.lastPathComponent)
                                    }
                                    onChange()
                                }
                                .buttonStyle(.bordered)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
                // A ScrollView with only a max height may collapse to zero in
                // a VStack. Give a non-empty attachment list a real minimum
                // height so names/types remain visible in the editor.
                .frame(minHeight: 56, maxHeight: 180)
            }
        }
        .onAppear(perform: reload)
        .onChange(of: refreshToken) { reload() }
        .onChange(of: ownerID) { reload() }
        .onChange(of: draftID) { reload() }
        .onChange(of: hiddenSavedNames) { reload() }
        .task(id: previewReloadIdentity) { reload() }
    }

    private var previewReloadIdentity: String {
        [workspace?.root.path ?? "none", draftID ?? "none", ownerID, String(refreshToken)]
            .joined(separator: "|")
    }

    private func reload() {
        items = Self.loadItems(
            workspace: workspace,
            draftID: draftID,
            ownerID: ownerID,
            hiddenSavedNames: hiddenSavedNames
        )
    }

    private static func loadItems(
        workspace: AttachmentWorkspace?,
        draftID: String?,
        ownerID: String,
        hiddenSavedNames: Set<String>
    ) -> [AttachmentPreviewItem] {
        guard let workspace else { return [] }
        var loaded = ((try? workspace.files(ownerID: ownerID)) ?? []).map {
            AttachmentPreviewItem(url: $0, isDraft: false)
        }.filter { !hiddenSavedNames.contains($0.url.lastPathComponent) }
        if let draftID {
            loaded.append(contentsOf: ((try? workspace.draftFiles(draftID: draftID)) ?? []).map {
                AttachmentPreviewItem(url: $0, isDraft: true)
            })
        }
        return loaded
    }
}

private struct AttachmentThumbnail: View {
    let url: URL

    var body: some View {
        Group {
            if let image = NSImage(contentsOf: url) {
                Image(nsImage: image)
                    .resizable()
                    .scaledToFill()
            } else {
                Image(systemName: "doc")
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(width: 42, height: 42)
        .background(.quaternary.opacity(0.35), in: RoundedRectangle(cornerRadius: 6))
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }
}

struct EventEditorView: View {
    @State private var draft: EditableEvent
    @State private var timeText: String
    @State private var stagedAttachmentCount: Int
    @State private var pendingRemovedAttachmentNames: Set<String> = []
    private let original: EditableEvent
    let reminderConfig: ReminderConfig
    let attachmentWorkspace: AttachmentWorkspace?
    let draftID: String?
    let onDirtyChange: (Bool) -> Void
    let onCancel: () -> Void
    let onOpenAttachments: () -> Void
    let onSave: (EditableEvent, Set<String>) -> Void

    init(
        event: EditableEvent,
        reminderConfig: ReminderConfig,
        attachmentWorkspace: AttachmentWorkspace?,
        draftID: String?,
        onDirtyChange: @escaping (Bool) -> Void,
        onCancel: @escaping () -> Void,
        onOpenAttachments: @escaping () -> Void,
        onSave: @escaping (EditableEvent, Set<String>) -> Void
    ) {
        self._draft = State(initialValue: event)
        self._timeText = State(initialValue: clockTimeText(hour: event.hour, minute: event.minute))
        self._stagedAttachmentCount = State(initialValue: event.attachments?.count ?? 0)
        self.original = event
        self.reminderConfig = reminderConfig
        self.attachmentWorkspace = attachmentWorkspace
        self.draftID = draftID
        self.onDirtyChange = onDirtyChange
        self.onCancel = onCancel
        self.onOpenAttachments = onOpenAttachments
        self.onSave = onSave
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                RequiredLabel("Title")
                ZStack(alignment: .topLeading) {
                    TextEditor(text: $draft.title)
                        .scrollContentBackground(.hidden)
                        .padding(2)
                    if draft.title.isEmpty {
                        Text("Required")
                            .foregroundStyle(.secondary)
                            .padding(.top, 12)
                            .padding(.leading, 13)
                            .allowsHitTesting(false)
                    }
                }
                .frame(minHeight: 48, maxHeight: 96)
                .eventEditorFieldCard()
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("Description")
                TextEditor(text: $draft.description)
                    .scrollContentBackground(.hidden)
                    .padding(2)
                    .frame(minHeight: 72, maxHeight: 180)
                    .eventEditorFieldCard()
            }
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Attachments").font(.headline)
                    Spacer()
                    Text("\(stagedAttachmentCount)").foregroundStyle(.secondary)
                }
                AttachmentPreviewList(
                    workspace: attachmentWorkspace,
                    draftID: draftID,
                    ownerID: attachmentOwnerID,
                    refreshToken: stagedAttachmentCount,
                    hiddenSavedNames: pendingRemovedAttachmentNames,
                    onRemoveSaved: { name in
                        pendingRemovedAttachmentNames.insert(name)
                        stagedAttachmentCount = stagedCount()
                    },
                    onChange: { stagedAttachmentCount = stagedCount() }
                )
                .id(attachmentPreviewIdentity)
                HStack(spacing: 10) {
                    Button("+ Add Files") { chooseFiles() }
                    if clipboardAttachmentAvailable() {
                        Button("Paste") { paste() }
                    }
                    Button(action: onOpenAttachments) { Image(systemName: "folder") }
                        .buttonStyle(.bordered)
                        .help("Open Attachments Folder")
                }
                Text("Drop files here • folders are not imported")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(12)
            .background(.quaternary.opacity(0.22), in: RoundedRectangle(cornerRadius: 10))
            .onDrop(of: [UTType.fileURL.identifier], isTargeted: nil) { providers in
                handleDrop(providers)
            }
            DatePicker(selection: $draft.date, displayedComponents: .date) {
                RequiredLabel("Date")
            }
            .datePickerStyle(.graphical)
            HStack {
                RequiredLabel("Time")
                    .frame(width: 80, alignment: .trailing)
                TextField("HH:mm", text: $timeText)
                    .font(.system(.body, design: .monospaced))
                    .multilineTextAlignment(.center)
                    .frame(width: eventEditorTimeFieldWidth)
                Stepper("", value: timeMinutesBinding, in: 0...1439)
                    .labelsHidden()
                Text("HH:mm")
                    .foregroundStyle(.secondary)
                    .font(.caption)
                Spacer()
            }
            Toggle("Enabled", isOn: $draft.enabled)
            Picker("Importance", selection: $draft.attentionLevel) {
                Text("Normal").tag(AttentionState.green)
                Text("Important").tag(AttentionState.yellow)
                Text("Critical").tag(AttentionState.red)
            }
            .pickerStyle(.segmented)
            .tint(color(for: draft.attentionLevel))
            Section {
                Picker("Repeat", selection: recurrenceModeBinding) {
                    Text("None").tag("none")
                    Text("Every selected weekday/time").tag("weekly_fixed")
                    Text("Days after Done").tag("after_done_days")
                }
                if draft.recurrence?.mode == "weekly_fixed" {
                    Text("Next event will repeat every \(weekdayName(draft.startDate())) at \(clockTimeText(hour: draft.hour, minute: draft.minute)) after Done.")
                        .foregroundStyle(.secondary)
                }
                if draft.recurrence?.mode == "after_done_days" {
                    Stepper(value: recurrenceDaysBinding, in: 1...730) {
                        Text("\(draft.recurrence?.days ?? 7) days after Done")
                    }
                }
            }
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(reminderConfig.presets) { preset in
                        Toggle(preset.label, isOn: reminderBinding(preset.minutes_before))
                            .disabled(!isReminderAvailable(preset.minutes_before))
                            .foregroundStyle(isReminderAvailable(preset.minutes_before) ? .primary : .secondary)
                    }
                }
            } header: {
                RequiredLabel("Reminders")
            }
            Picker("Start blinking", selection: blinkerSelectionBinding) {
                ForEach(reminderConfig.presets) { preset in
                    Text(preset.label).tag(preset.minutes_before)
                }
            }
            .disabled(!isReminderAvailable(draft.blinkerMinutesBefore ?? 0))
            HStack {
                Button("Cancel") {
                    onCancel()
                }
                Button("Save") {
                    pruneUnavailableReminders()
                    onSave(draft, pendingRemovedAttachmentNames)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!canSave)
            }
            }
        }
        .frame(maxWidth: 620, alignment: .leading)
        .frame(maxHeight: .infinity, alignment: .top)
        .padding(.horizontal, 30)
        .padding(.vertical, 16)
        .onChange(of: draft.date) {
            pruneUnavailableReminders()
        }
        .onChange(of: draft.hour) {
            pruneUnavailableReminders()
        }
        .onChange(of: draft.minute) {
            pruneUnavailableReminders()
        }
        .onChange(of: timeText) {
            applyTimeText()
        }
        .onChange(of: draft) {
            onDirtyChange(draft != original || stagedAttachmentCount != (original.attachments?.count ?? 0))
        }
        .onChange(of: stagedAttachmentCount) {
            onDirtyChange(draft != original || stagedAttachmentCount != (original.attachments?.count ?? 0))
        }
        .onAppear {
            stagedAttachmentCount = stagedCount()
        }
    }

    private func chooseFiles() {
        guard let attachmentWorkspace, let draftID else { return }
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        guard panel.runModal() == .OK else { return }
        do {
            try attachmentWorkspace.addFiles(panel.urls, to: draftID)
            stagedAttachmentCount = stagedCount()
        } catch {
            // The parent owns the error surface; a failed staging operation
            // simply leaves the editor draft untouched.
        }
    }

    private var attachmentOwnerID: String {
        draft.id
    }

    private var attachmentPreviewIdentity: String {
        [attachmentWorkspace?.root.path ?? "none", draftID ?? "none", attachmentOwnerID]
            .joined(separator: "|")
    }

    private func paste() {
        if !clipboardFileURLs().isEmpty {
            pasteAttachments()
        } else {
            pasteScreenshot()
        }
    }

    private func pasteScreenshot() {
        guard let attachmentWorkspace, let draftID,
              let data = clipboardJPEGData() else { return }
        do {
            try attachmentWorkspace.addJPEG(data, to: draftID)
            stagedAttachmentCount = stagedCount()
        } catch {
            // See chooseFiles().
        }
    }

    private func pasteAttachments() {
        guard let attachmentWorkspace, let draftID else { return }
        let urls = clipboardFileURLs()
        guard !urls.isEmpty else { return }
        do {
            try attachmentWorkspace.addFiles(urls, to: draftID)
            stagedAttachmentCount = stagedCount()
        } catch {
            // See chooseFiles().
        }
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        guard let attachmentWorkspace, let draftID else { return false }
        let group = DispatchGroup()
        let collector = DropURLCollector()
        for provider in providers {
            guard provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) else { continue }
            group.enter()
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                defer { group.leave() }
                if let data = item as? Data,
                   let url = URL(dataRepresentation: data, relativeTo: nil),
                   (try? url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true {
                    collector.append(url)
                } else if let url = item as? URL,
                          (try? url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true {
                    collector.append(url)
                }
            }
        }
        group.notify(queue: .main) {
            let urls = collector.values
            guard !urls.isEmpty else { return }
            try? attachmentWorkspace.addFiles(urls, to: draftID)
            stagedAttachmentCount = stagedCount()
        }
        return !providers.isEmpty
    }

    private func stagedCount() -> Int {
        guard let attachmentWorkspace, let draftID,
              let values = try? FileManager.default.contentsOfDirectory(
                at: attachmentWorkspace.draftURL(draftID),
                includingPropertiesForKeys: [.isRegularFileKey],
                options: [.skipsHiddenFiles]
              ) else { return stagedAttachmentCount }
        let staged = values.filter { (try? $0.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true }.count
        let saved = max((original.attachments?.count ?? 0) - pendingRemovedAttachmentNames.count, 0)
        return staged + saved
    }

    private func reminderBinding(_ offset: Int) -> Binding<Bool> {
        Binding(
            get: { draft.reminderOffsets.contains(offset) && isReminderAvailable(offset) },
            set: { selected in
                guard isReminderAvailable(offset) else {
                    draft.reminderOffsets.removeAll { $0 == offset }
                    return
                }
                if selected {
                    draft.reminderOffsets.append(offset)
                } else {
                    draft.reminderOffsets.removeAll { $0 == offset }
                }
            }
        )
    }

    private var canSave: Bool {
        !draft.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        && !availableReminderOffsets(draft.reminderOffsets, eventStart: draft.startDate()).isEmpty
        && parseClockTime(timeText) != nil
        && (draft.blinkerMinutesBefore == nil || isReminderAvailable(draft.blinkerMinutesBefore ?? 0))
        && (draft.recurrence?.mode != "after_done_days" || (draft.recurrence?.days ?? 0) > 0)
    }

    private var blinkerSelectionBinding: Binding<Int> {
        Binding(
            get: { draft.blinkerMinutesBefore ?? 0 },
            set: { draft.blinkerMinutesBefore = max($0, 0) }
        )
    }

    private var timeMinutesBinding: Binding<Int> {
        Binding(
            get: { draft.hour * 60 + draft.minute },
            set: { totalMinutes in
                draft.hour = totalMinutes / 60
                draft.minute = totalMinutes % 60
                timeText = clockTimeText(hour: draft.hour, minute: draft.minute)
                pruneUnavailableReminders()
            }
        )
    }

    private func isReminderAvailable(_ offset: Int) -> Bool {
        isReminderOffsetAvailable(offset, eventStart: draft.startDate())
    }

    private func pruneUnavailableReminders() {
        draft.reminderOffsets = availableReminderOffsets(draft.reminderOffsets, eventStart: draft.startDate())
    }

    private func applyTimeText() {
        guard let parsed = parseClockTime(timeText) else { return }
        draft.hour = parsed.hour
        draft.minute = parsed.minute
        pruneUnavailableReminders()
    }

    private var recurrenceModeBinding: Binding<String> {
        Binding(
            get: { draft.recurrence?.mode ?? "none" },
            set: { mode in
                if mode == "weekly_fixed" {
                    draft.recurrence = EventRecurrence(mode: "weekly_fixed")
                } else if mode == "after_done_days" {
                    draft.recurrence = EventRecurrence(
                        mode: "after_done_days",
                        days: max(draft.recurrence?.days ?? 7, 1)
                    )
                } else {
                    draft.recurrence = nil
                }
            }
        )
    }

    private var recurrenceDaysBinding: Binding<Int> {
        Binding(
            get: { max(draft.recurrence?.days ?? 7, 1) },
            set: { value in
                draft.recurrence = EventRecurrence(mode: "after_done_days", days: max(value, 1))
            }
        )
    }

    private func weekdayName(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeZone = blinkTimeZone
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "EEEE"
        return formatter.string(from: date)
    }
}

private final class DropURLCollector: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: [URL] = []

    func append(_ url: URL) {
        lock.lock()
        stored.append(url)
        lock.unlock()
    }

    var values: [URL] {
        lock.lock()
        defer { lock.unlock() }
        return stored
    }
}

struct AstronomySettingsView: View {
    let config: AstronomyConfig?
    let schedule: AstronomySchedule?
    let onSave: (AstronomyConfig) -> Bool
    @State private var draft: AstronomyConfig?
    @State private var savedDraft: AstronomyConfig?
    @State private var briefingTimeText: String
    @State private var didSave = false

    init(config: AstronomyConfig?, schedule: AstronomySchedule?, onSave: @escaping (AstronomyConfig) -> Bool) {
        self.config = config
        self.schedule = schedule
        self.onSave = onSave
        self._draft = State(initialValue: config)
        self._savedDraft = State(initialValue: config)
        self._briefingTimeText = State(initialValue: config?.briefing.time ?? "06:30")
    }

    var body: some View {
        ScrollView(.vertical) {
            VStack(alignment: .leading, spacing: 14) {
                Text("✨ Astronomy").font(.title.bold())
                if let schedule {
                    Label(astronomyStatusLabel(schedule.generation_status), systemImage: "checkmark.seal")
                        .font(.headline)
                    if let from = schedule.generated_from, let through = schedule.generated_through {
                        Text("\(from) through \(through)")
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Text("Preparing astronomy data…").foregroundStyle(.secondary)
                }
                if let draft {
                    VStack(alignment: .leading, spacing: 10) {
                        Label(draft.timezone, systemImage: "globe")
                            .foregroundStyle(.secondary)
                        Toggle("Daily Astronomy Briefing", isOn: briefingBoolBinding(\.enabled))
                        HStack {
                            Text("Briefing time")
                            TextField("HH:mm", text: $briefingTimeText)
                                .font(.system(.body, design: .monospaced))
                                .multilineTextAlignment(.center)
                                .frame(width: timeInputWidth)
                                .disabled(!draft.briefing.enabled || draft.briefing.include_weather)
                                .onChange(of: briefingTimeText) {
                                    didSave = false
                                    applyBriefingTimeText()
                                }
                            Stepper("", value: briefingMinutesBinding, in: 0...1439)
                                .labelsHidden()
                                .disabled(!draft.briefing.enabled || draft.briefing.include_weather)
                            Text("HH:mm").foregroundStyle(.secondary).font(.caption)
                            Toggle("Use Weather briefing time", isOn: briefingBoolBinding(\.include_weather))
                                .disabled(!draft.briefing.enabled)
                        }
                        Toggle("Include day/night duration", isOn: briefingBoolBinding(\.include_day_night))
                            .disabled(!draft.briefing.enabled)
                    }
                    .blinkSettingsCard()

                    AstronomyAlignedColumns {
                        if let group = draft.notifications["sun"] {
                            astronomyGroupPanel(key: "sun", group: group)
                        }
                    } right: {
                        if let group = draft.notifications["moon"] {
                            astronomyGroupPanel(key: "moon", group: group)
                        }
                    }
                    Button(saveButtonTitle(defaultTitle: "Save Astronomy", saved: didSave)) {
                        if onSave(draft) {
                            savedDraft = draft
                            didSave = true
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!astronomyIsDirty || didSave)
                    .opacity(saveButtonOpacity(hasUnsavedChanges: astronomyIsDirty && !didSave))

                    if let record = todayAstronomyRecord {
                        Divider()
                        AstronomyTodaySummaryView(record: record)
                    } else if schedule?.generation_status == "fresh" {
                        Divider()
                        Text("Today's astronomy data is unavailable")
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Text("Astronomy config not found").foregroundStyle(.secondary)
                }
                Spacer(minLength: 24)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(BlinkDesign.pagePadding)
        }
        .scrollIndicators(.visible)
    }

    private var todayAstronomyRecord: AstronomyDailyRecord? {
        guard let records = schedule?.daily_records, !records.isEmpty else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = blinkTimeZone
        formatter.dateFormat = "yyyy-MM-dd"
        let today = formatter.string(from: Date())
        return records.first(where: { $0.date == today }) ?? records.first
    }

    private func astronomyGroupPanel(key: String, group: AstronomyConfig.NotificationGroup) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("\(key == "sun" ? "☀️ Sun" : "🌙 Moon")")
                .font(.headline)
            Toggle("\(key == "sun" ? "Sun" : "Moon") notifications", isOn: groupBinding(key))
            ForEach(group.events.keys.sorted(), id: \.self) { eventName in
                Toggle(
                    "\(astronomyEventEmoji(eventName)) \(eventName.replacingOccurrences(of: "_", with: " ").capitalized)",
                    isOn: eventBinding(key, eventName)
                )
                .disabled(!group.enabled)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.quaternary.opacity(0.35), in: RoundedRectangle(cornerRadius: 8))
    }

    private func astronomyStatusLabel(_ status: String?) -> String {
        switch status {
        case "fresh": return "Astronomy data ready"
        case "pending_precise_ephemeris": return "Preparing astronomy data…"
        default: return "Astronomy data unavailable"
        }
    }

    private func astronomyEventEmoji(_ event: String) -> String {
        switch event {
        case "sunrise": return "☀️ ↑"
        case "sunset": return "☀️ ↓"
        case "solar_noon": return "☀️"
        case "civil_twilight": return "✨"
        case "moonrise": return "🌙 ↑"
        case "moonset": return "🌙 ↓"
        case "full_moon": return "🌕"
        case "new_moon": return "🌑"
        default: return "✨"
        }
    }

    private func briefingBoolBinding(_ keyPath: WritableKeyPath<AstronomyConfig.Briefing, Bool>) -> Binding<Bool> {
        Binding(
            get: { draft?.briefing[keyPath: keyPath] ?? false },
            set: { value in
                guard var current = draft else { return }
                current.briefing[keyPath: keyPath] = value
                draft = current
                didSave = false
            }
        )
    }

    private func groupBinding(_ key: String) -> Binding<Bool> {
        Binding(
            get: { draft?.notifications[key]?.enabled == true },
            set: { value in
                guard var current = draft, var groupValue = current.notifications[key] else { return }
                groupValue.enabled = value
                current.notifications[key] = groupValue
                draft = current
                didSave = false
            }
        )
    }

    private func eventBinding(_ group: String, _ event: String) -> Binding<Bool> {
        Binding(
            get: { draft?.notifications[group]?.events[event]?.enabled == true },
            set: { value in
                guard var current = draft, var groupValue = current.notifications[group], var eventValue = groupValue.events[event] else { return }
                eventValue.enabled = value
                groupValue.events[event] = eventValue
                current.notifications[group] = groupValue
                draft = current
                didSave = false
            }
        )
    }

    private var astronomyIsDirty: Bool {
        guard let draft, let savedDraft,
              let draftData = try? JSONEncoder().encode(draft),
              let savedData = try? JSONEncoder().encode(savedDraft) else { return false }
        return draftData != savedData
    }

    private var briefingMinutesBinding: Binding<Int> {
        Binding(
            get: {
                guard let parsed = parseClockTime(briefingTimeText) else { return 390 }
                return parsed.hour * 60 + parsed.minute
            },
            set: { minutes in
                briefingTimeText = String(format: "%02d:%02d", minutes / 60, minutes % 60)
                didSave = false
                applyBriefingTimeText()
            }
        )
    }

    private func applyBriefingTimeText() {
        guard let parsed = parseClockTime(briefingTimeText), var current = draft else { return }
        current.briefing.time = String(format: "%02d:%02d", parsed.hour, parsed.minute)
        draft = current
    }
}

private struct AstronomyAlignedColumns<Left: View, Right: View>: View {
    private let left: Left
    private let right: Right

    init(
        @ViewBuilder left: () -> Left,
        @ViewBuilder right: () -> Right
    ) {
        self.left = left()
        self.right = right()
    }

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            left.frame(maxWidth: .infinity, alignment: .leading)
            right.frame(maxWidth: .infinity, alignment: .leading)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct AstronomyTodaySummaryView: View {
    let record: AstronomyDailyRecord

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(record.date, systemImage: "calendar")
                .font(.headline)

            AstronomyAlignedColumns {
                sunSummary
            } right: {
                moonSummary
            }
        }
    }

    private var sunSummary: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("☀️ Sun").font(.headline)
            AstronomySummaryRow(icon: "☀️ ↑", label: "Sunrise", value: timeLabel(record.sunrise?.time))
            AstronomySummaryRow(icon: "☀️", label: "Solar noon", value: timeLabel(record.solar_noon?.time))
            AstronomySummaryRow(icon: "☀️ ↓", label: "Sunset", value: timeLabel(record.sunset?.time))
            AstronomySummaryRow(icon: "✨", label: "Civil twilight ends", value: timeLabel(record.civil_twilight_end?.time ?? record.sunset?.civil_twilight_end))
            if let dayLength = record.day_length_minutes {
                AstronomySummaryRow(icon: "🌞", label: "Day length", value: durationLabel(dayLength))
                AstronomySummaryRow(icon: "🌙", label: "Night length", value: durationLabel(max(0, 1440 - dayLength)))
            }
        }
    }

    private var moonSummary: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("🌙 Moon").font(.headline)
            if let status = record.moon_status_at_sunset {
                let phase = status.phase_name ?? "Moon phase"
                let trend = record.new_moon == nil && record.full_moon == nil
                    ? status.phase_trend.map { " \(moonDirectionEmoji($0))" } ?? ""
                    : ""
                AstronomySummaryRow(icon: moonPhaseEmoji(status.phase_name), label: "Phase", value: "\(phase)\(trend)")
                if let illumination = status.illumination_percent ?? record.illumination {
                    AstronomySummaryRow(icon: "◐", label: "Illumination", value: String(format: "%.1f%%", illumination))
                }
                AstronomySummaryRow(icon: "🌙 ↑", label: "Moonrise", value: timeLabel(record.moonrise ?? status.moonrise))
                AstronomySummaryRow(icon: "🌙 ↓", label: "Moonset", value: timeLabel(record.moonset ?? status.moonset))
            } else if let illumination = record.illumination {
                AstronomySummaryRow(icon: moonPhaseEmoji(nil), label: "Illumination", value: String(format: "%.1f%%", illumination))
            }
            AstronomySummaryRow(icon: "🌑", label: "Next new moon", value: moonDateLabel(record.next_new_moon))
            AstronomySummaryRow(icon: "🌕", label: "Next full moon", value: moonDateLabel(record.next_full_moon))
        }
    }
}

private struct AstronomySummaryRow: View {
    let icon: String
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Text(icon)
            Text("\(label): \(value)")
        }
        .foregroundStyle(.secondary)
    }
}

private func astronomyDate(_ value: String?) -> Date? {
    guard let value else { return nil }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = blinkTimeZone
    for pattern in ["yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXXXX", "yyyy-MM-dd'T'HH:mm:ssXXXXX"] {
        formatter.dateFormat = pattern
        if let date = formatter.date(from: value) { return date }
    }
    let iso = ISO8601DateFormatter()
    iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return iso.date(from: value)
}

private func timeLabel(_ value: String?) -> String {
    guard let value, let date = astronomyDate(value) else { return "Unavailable" }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = blinkTimeZone
    formatter.dateFormat = "HH:mm"
    return formatter.string(from: date)
}

private func moonDateLabel(_ value: String?) -> String {
    guard let value, let date = astronomyDate(value) else { return "Unavailable" }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = blinkTimeZone
    formatter.dateFormat = "MMM d, yyyy"
    let days = max(0, Int(ceil(date.timeIntervalSinceNow / 86400.0)))
    let dayLabel = days == 1 ? "1 day" : "\(days) days"
    return "\(formatter.string(from: date)) (\(dayLabel))"
}

private func durationLabel(_ minutes: Int) -> String {
    "\(minutes / 60) h \(minutes % 60) min"
}

private func moonPhaseEmoji(_ phaseName: String?) -> String {
    switch phaseName?.lowercased() {
    case "new moon": return "🌑"
    case "waxing moon": return "🌒"
    case "waxing crescent": return "🌒"
    case "first quarter": return "🌓"
    case "waxing gibbous": return "🌔"
    case "full moon": return "🌕"
    case "waning moon": return "🌘"
    case "waning gibbous": return "🌖"
    case "last quarter", "third quarter": return "🌗"
    case "waning crescent": return "🌘"
    default: return "🌙"
    }
}

private func moonDirectionEmoji(_ trend: String) -> String {
    trend.lowercased() == "waning" ? "⬇️" : "⬆️"
}

struct WeatherView: View {
    let config: WeatherConfig?
    let cache: WeatherCache?
    let onSave: (WeatherConfig) -> Bool

    var body: some View {
        ScrollView(.vertical) {
        VStack(alignment: .leading, spacing: 14) {
            Text("🌤️ Weather").font(.title.bold())
            if let config {
                WeatherSettingsForm(config: config, onSave: onSave)
            } else {
                Text("Weather config not found").foregroundStyle(.secondary)
            }
            Divider()
            if let cache, cache.status == "fresh" {
                Label(cache.forecast_date ?? "Forecast", systemImage: "calendar")
                    .font(.headline)
                if let high = cache.high_f, let low = cache.low_f {
                    Text("🌡️ High today: \(high)°F / Low tonight: \(low)°F")
                }
                if let humidityMin = cache.humidity_min_percent,
                   let humidityMax = cache.humidity_max_percent {
                    Text("💧 Humidity: \(humidityMin)-\(humidityMax)%")
                        .foregroundStyle(.secondary)
                }
                if let rain = cache.rain_probability_percent {
                    Text(cache.rain_window.map { "🌧️ Rain: \(rain)% / \($0)" } ?? "🌧️ Rain: \(rain)%")
                        .foregroundStyle(.secondary)
                }
                if cache.snow_expected == true {
                    Text("❄️ Snow expected").foregroundStyle(.secondary)
                }
                if let speed = cache.wind_speed_mph,
                   let gust = cache.wind_gust_mph {
                    Text("💨 Wind: \(speed) mph / Gusts \(gust) mph")
                        .foregroundStyle(cache.wind_warning == true ? .primary : .secondary)
                }
                if let fetched = cache.fetched_at {
                    Label("Updated \(formattedUpdatedTime(fetched))", systemImage: "arrow.clockwise")
                        .foregroundStyle(.secondary)
                }
            } else {
                Text(cache?.status ?? "Weather cache not found").foregroundStyle(.secondary)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(BlinkDesign.pagePadding)
        }
    }
}

struct WeatherSettingsForm: View {
    @State private var draft: WeatherConfig
    @State private var savedDraft: WeatherConfig
    @State private var morningTimeText: String
    @State private var didSave = false
    let onSave: (WeatherConfig) -> Bool

    init(config: WeatherConfig, onSave: @escaping (WeatherConfig) -> Bool) {
        var normalized = config
        if normalized.include == nil {
            normalized.include = WeatherConfig.Include(temperature: true, humidity: true, wind: true, rain: true, snow: true)
        }
        self._draft = State(initialValue: normalized)
        self._savedDraft = State(initialValue: normalized)
        self._morningTimeText = State(initialValue: normalized.morning_briefing.time)
        self.onSave = onSave
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle("Weather pushes", isOn: $draft.weather_enabled)
                .toggleStyle(.switch)
                .onChange(of: draft.weather_enabled) { _, _ in didSave = false }
            HStack {
                RequiredLabel("Weather briefing time")
                TextField("HH:mm", text: $morningTimeText)
                    .font(.system(.body, design: .monospaced))
                    .multilineTextAlignment(.center)
                    .frame(width: timeInputWidth)
                    .onChange(of: morningTimeText) {
                        didSave = false
                        applyMorningTimeText()
                    }
                Stepper("", value: morningMinutesBinding, in: 0...1439)
                    .labelsHidden()
                Text("HH:mm").foregroundStyle(.secondary).font(.caption)
            }
            .disabled(!draft.weather_enabled)
            Text("Include in briefing").font(.headline)
                Toggle("🌡️ Temperature", isOn: includeBinding(\.temperature))
                    .onChange(of: draft.include?.temperature) { _, _ in didSave = false }
                Toggle("💧 Humidity", isOn: includeBinding(\.humidity))
                    .onChange(of: draft.include?.humidity) { _, _ in didSave = false }
                Toggle("💨 Wind", isOn: includeBinding(\.wind))
                    .onChange(of: draft.include?.wind) { _, _ in didSave = false }
                Toggle("🌧️ Rain", isOn: includeBinding(\.rain))
                    .onChange(of: draft.include?.rain) { _, _ in didSave = false }
                Toggle("❄️ Snow", isOn: includeBinding(\.snow))
                    .onChange(of: draft.include?.snow) { _, _ in didSave = false }
            Button(saveButtonTitle(defaultTitle: "Save Weather", saved: didSave)) {
                let value = draft
                if onSave(value) {
                    savedDraft = value
                    didSave = true
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!canSave || didSave || !weatherIsDirty)
            .opacity(saveButtonOpacity(hasUnsavedChanges: weatherIsDirty && !didSave))
        }
    }

    private var canSave: Bool {
        !draft.morning_briefing.time.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var weatherIsDirty: Bool {
        guard let draftData = try? JSONEncoder().encode(draft),
              let savedData = try? JSONEncoder().encode(savedDraft) else { return false }
        return draftData != savedData
    }

    private var morningMinutesBinding: Binding<Int> {
        Binding(
            get: {
                guard let parsed = parseClockTime(morningTimeText) else { return 390 }
                return parsed.hour * 60 + parsed.minute
            },
            set: { minutes in
                morningTimeText = String(format: "%02d:%02d", minutes / 60, minutes % 60)
                applyMorningTimeText()
            }
        )
    }

    private func applyMorningTimeText() {
        guard let parsed = parseClockTime(morningTimeText) else { return }
        draft.morning_briefing.time = String(format: "%02d:%02d", parsed.hour, parsed.minute)
    }

    private func includeBinding(_ keyPath: WritableKeyPath<WeatherConfig.Include, Bool?>) -> Binding<Bool> {
        Binding(
            get: {
                let include = draft.include ?? WeatherConfig.Include(temperature: true, humidity: true, wind: true, rain: true, snow: true)
                return include[keyPath: keyPath] ?? true
            },
            set: { selected in
                var include = draft.include ?? WeatherConfig.Include(temperature: true, humidity: true, wind: true, rain: true, snow: true)
                include[keyPath: keyPath] = selected
                draft.include = include
            }
        )
    }
}

struct LocationView: View {
    let location: BlinkLocation?
    let onEdit: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Location").font(.title.bold())
            if let location {
                Text(location.display_name).font(.headline)
                Text("\(location.latitude), \(location.longitude)")
                    .foregroundStyle(.secondary)
                Text(location.timezone).foregroundStyle(.secondary)
                Button("Edit Location") {
                    onEdit()
                }
                .buttonStyle(.borderedProminent)
            } else {
                Text("Location not found").foregroundStyle(.secondary)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct EditableLocation: Identifiable {
    let id = UUID()
    var displayName: String
    var latitude: String
    var longitude: String
    var timezone: String
    var coordinateSource: String

    init(location: BlinkLocation) {
        self.displayName = location.display_name
        self.latitude = String(format: "%.6f", location.latitude)
        self.longitude = String(format: "%.6f", location.longitude)
        self.timezone = location.timezone
        self.coordinateSource = location.coordinate_source ?? "city"
    }

    func toLocation() -> BlinkLocation {
        BlinkLocation(
            display_name: displayName,
            latitude: Double(latitude) ?? 0,
            longitude: Double(longitude) ?? 0,
            timezone: timezone,
            coordinate_source: coordinateSource
        )
    }
}

struct LocationEditorView: View {
    @State private var draft: EditableLocation
    @State private var usesCustomTimezone = false
    @State private var usesCustomCoordinates = false
    @State private var cityQuery = ""
    @State private var suggestions: [BlinkLocation] = []
    @State private var isSearching = false
    @State private var searchError: String?
    let resolverRoot: URL
    let onSave: (EditableLocation) -> Void

    init(location: EditableLocation, resolverRoot: URL, onSave: @escaping (EditableLocation) -> Void) {
        self._draft = State(initialValue: location)
        self._usesCustomTimezone = State(initialValue: !commonTimezones.contains(location.timezone))
        self._usesCustomCoordinates = State(initialValue: location.coordinateSource == "custom")
        self._cityQuery = State(initialValue: location.displayName)
        self.resolverRoot = resolverRoot
        self.onSave = onSave
    }

    var body: some View {
        Form {
            Picker("Coordinate source", selection: $usesCustomCoordinates) {
                Text("City search").tag(false)
                Text("Custom coordinates").tag(true)
            }
            .pickerStyle(.segmented)
            .onChange(of: usesCustomCoordinates) { _, isCustom in
                draft.coordinateSource = isCustom ? "custom" : "city"
                if !isCustom {
                    cityQuery = draft.displayName
                }
            }

            if usesCustomCoordinates {
                TextField("Name", text: $draft.displayName)
                    .formLabel("Name", required: true)
                TextField("Latitude", text: $draft.latitude)
                    .formLabel("Latitude", required: true)
                TextField("Longitude", text: $draft.longitude)
                    .formLabel("Longitude", required: true)
                Text("Astronomy will use these coordinates directly.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                TextField("Start typing a city", text: $cityQuery)
                    .formLabel("City", required: true)
                    .onChange(of: cityQuery) { _, _ in
                        suggestions = []
                        searchError = nil
                    }
                if isSearching {
                    ProgressView()
                        .controlSize(.small)
                }
                if let searchError {
                    Text(searchError)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if !suggestions.isEmpty {
                    ScrollView(.vertical) {
                        VStack(alignment: .leading, spacing: 0) {
                            ForEach(suggestions) { suggestion in
                                Button {
                                    select(suggestion)
                                } label: {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(suggestion.display_name)
                                        Text("\(suggestion.latitude, specifier: "%.4f"), \(suggestion.longitude, specifier: "%.4f") · \(suggestion.timezone)")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(.vertical, 5)
                                }
                                .buttonStyle(.plain)
                                if suggestion.id != suggestions.last?.id {
                                    Divider()
                                }
                            }
                        }
                    }
                    .padding(8)
                    .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
                    .frame(maxHeight: 180)
                }
                Text("Coordinates and timezone are filled from the selected city.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                TextField("Latitude", text: $draft.latitude)
                    .formLabel("Latitude", required: true)
                    .disabled(true)
                TextField("Longitude", text: $draft.longitude)
                    .formLabel("Longitude", required: true)
                    .disabled(true)
            }

            if usesCustomCoordinates {
                Picker(selection: timezoneSelection) {
                    ForEach(commonTimezones, id: \.self) { timezone in
                        Text(timezone).tag(timezone)
                    }
                    Text("Custom").tag("__custom__")
                } label: {
                    RequiredLabel("Timezone")
                }
                if usesCustomTimezone {
                    TextField("Timezone", text: $draft.timezone)
                        .formLabel("Custom timezone", required: true)
                }
            } else {
                HStack {
                    RequiredLabel("Timezone")
                    Text(draft.timezone)
                        .foregroundStyle(.secondary)
                }
            }

            Button("Save") {
                onSave(draft)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!canSave)
        }
        .padding()
        .task(id: cityQuery) {
            guard !usesCustomCoordinates else { return }
            let query = cityQuery.trimmingCharacters(in: .whitespacesAndNewlines)
            guard query.count >= 2 else { return }
            try? await Task.sleep(for: .milliseconds(350))
            guard !Task.isCancelled else { return }
            isSearching = true
            defer { isSearching = false }
            do {
                let results = try await LocationGeocoder(root: resolverRoot).search(query: query)
                guard !Task.isCancelled, cityQuery == query else { return }
                suggestions = results
            } catch is CancellationError {
                return
            } catch {
                guard !Task.isCancelled, cityQuery == query else { return }
                suggestions = []
                searchError = "Could not search locations. Check your connection."
            }
        }
    }

    private var timezoneSelection: Binding<String> {
        Binding(
            get: { usesCustomTimezone ? "__custom__" : draft.timezone },
            set: { value in
                if value == "__custom__" {
                    usesCustomTimezone = true
                } else {
                    usesCustomTimezone = false
                    draft.timezone = value
                }
            }
        )
    }

    private var canSave: Bool {
        !draft.displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        && Double(draft.latitude) != nil
        && Double(draft.longitude) != nil
        && !draft.timezone.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        && (usesCustomCoordinates || cityQuery.trimmingCharacters(in: .whitespacesAndNewlines) == draft.displayName)
    }

    private func select(_ location: BlinkLocation) {
        draft.displayName = location.display_name
        draft.latitude = String(format: "%.6f", location.latitude)
        draft.longitude = String(format: "%.6f", location.longitude)
        draft.timezone = location.timezone
        draft.coordinateSource = "city"
        cityQuery = location.display_name
        suggestions = []
        searchError = nil
        usesCustomTimezone = false
    }
}

struct RequiredLabel: View {
    let title: String

    init(_ title: String) {
        self.title = title
    }

    var body: some View {
        HStack(spacing: 2) {
            Text(title)
            Text("*").foregroundStyle(.red)
        }
    }
}

public let eventEditorTimeFieldWidth: CGFloat = 112

public func shouldDismissEventEditorOnBackdropTap(editorIsDirty: Bool) -> Bool {
    true
}

extension View {
    func formLabel(_ title: String, required: Bool) -> some View {
        LabeledContent {
            self
        } label: {
            if required {
                RequiredLabel(title)
            } else {
                Text(title)
            }
        }
    }
}

struct EventRowActions {
    var newEvent: () -> Void
    var edit: (BlinkEvent) -> Void
    var duplicate: (BlinkEvent) -> Void
    var duplicateWithAttachments: (BlinkEvent) -> Void
    var addFiles: (BlinkEvent) -> Void
    var paste: (BlinkEvent) -> Void
    var openAttachments: (BlinkEvent) -> Void
    var done: (BlinkEvent) -> Void
    var toggle: (BlinkEvent) -> Void
    var delete: (BlinkEvent) -> Void
}

private func clipboardImageAvailable() -> Bool {
    clipboardImageData() != nil
}

private func clipboardAttachmentAvailable() -> Bool {
    !clipboardFileURLs().isEmpty || clipboardImageAvailable()
}

private func clipboardFileURLs() -> [URL] {
    let options: [NSPasteboard.ReadingOptionKey: Any] = [
        .urlReadingFileURLsOnly: true
    ]
    guard let objects = NSPasteboard.general.readObjects(
        forClasses: [NSURL.self],
        options: options
    ) else { return [] }
    return objects.compactMap { object in
        guard let url = (object as? NSURL)?.filePathURL,
              url.isFileURL,
              (try? url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true else {
            return nil
        }
        return url
    }
}

private func clipboardImageData() -> Data? {
    let pasteboard = NSPasteboard.general
    let imageTypes: [NSPasteboard.PasteboardType] = [
        .tiff,
        .png,
        NSPasteboard.PasteboardType(rawValue: "public.jpeg"),
        NSPasteboard.PasteboardType(rawValue: "public.heic")
    ]
    for type in imageTypes {
        guard let sourceData = pasteboard.data(forType: type),
              NSImage(data: sourceData) != nil else { continue }
        return sourceData
    }
    return nil
}

private func clipboardJPEGData() -> Data? {
    guard let sourceData = clipboardImageData(),
          let image = NSImage(data: sourceData),
          let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff) else { return nil }
    return bitmap.representation(using: .jpeg, properties: [:])
}

private func fileSizeLabel(_ url: URL) -> String {
    let bytes = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
    let formatter = ByteCountFormatter()
    formatter.countStyle = .file
    return formatter.string(fromByteCount: Int64(bytes))
}

private func fileTypeLabel(_ url: URL) -> String {
    let ext = url.pathExtension.trimmingCharacters(in: .whitespacesAndNewlines)
    return ext.isEmpty ? "File" : "\(ext.uppercased()) file"
}

private func attachmentSymbol(for url: URL) -> String {
    switch url.pathExtension.lowercased() {
    case "pdf": return "doc.richtext"
    case "xls", "xlsx", "xlsm", "csv": return "tablecells"
    case "jpg", "jpeg", "png", "heic", "gif", "tiff": return "photo"
    case "doc", "docx", "rtf", "txt": return "doc.text"
    case "zip", "7z", "rar": return "archivebox"
    default: return "doc"
    }
}

private func reminderLabel(_ minutes: Int) -> String {
    switch minutes {
    case 0: return "At time"
    case 5, 10, 30, 60: return "\(minutes) min before"
    case 300: return "5 hours before"
    case 720: return "12 hours before"
    case 1440: return "1 day before"
    default: return "\(minutes) min before"
    }
}

private func formattedUpdatedTime(_ value: String) -> String {
    let date: Date? = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        for pattern in ["yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXXXX", "yyyy-MM-dd'T'HH:mm:ssXXXXX"] {
            formatter.dateFormat = pattern
            if let parsed = formatter.date(from: value) { return parsed }
        }
        return ISO8601DateFormatter().date(from: value)
    }()
    guard let date else { return value }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = blinkTimeZone
    formatter.dateFormat = "HH:mm"
    return formatter.string(from: date)
}

private func color(for state: AttentionState) -> Color {
    switch state {
    case .off: return .secondary
    case .green: return .green
    case .yellow: return .yellow
    case .red: return .red
    }
}
