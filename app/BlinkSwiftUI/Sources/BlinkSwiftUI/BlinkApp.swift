import SwiftUI
import BlinkSwiftUICore

@main
struct BlinkApp: App {
    @StateObject private var appState = BlinkAppState()
    @Environment(\.openWindow) private var openWindow

    var body: some Scene {
        WindowGroup("Blink", id: "main") {
            ContentView(
                store: appState.store,
                newEventToken: appState.newEventRequestToken,
                onSnapshotChange: appState.applySnapshot
            )
                .frame(minWidth: 760, minHeight: 520)
        }

        MenuBarExtra {
            MenuBarBlinkView(
                summary: MenuBarSummary(snapshot: appState.snapshot),
                newEvent: {
                    openWindow(id: "main")
                    appState.requestNewEvent()
                    activateBlink()
                },
                openBlink: {
                    openWindow(id: "main")
                    activateBlink()
                }
            )
        } label: {
            Text(menuBarGlyph(for: appState.snapshot.attentionState))
        }
    }

    private func activateBlink() {
        #if canImport(AppKit)
        NSApp.activate()
        #endif
    }
}

@MainActor
final class BlinkAppState: ObservableObject {
    let store = BlinkStore()
    let attentionManager: AttentionManager
    @Published private(set) var snapshot = EventSnapshot(events: [], now: Date())
    @Published var newEventRequestToken: UUID?
    private var timer: Timer?

    init() {
        #if canImport(AppKit)
        self.attentionManager = AttentionManager(outputs: [DockAttentionOutput()])
        #else
        self.attentionManager = AttentionManager(outputs: [])
        #endif
        refreshAttention()
        timer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refreshAttention()
            }
        }
    }

    func refreshAttention() {
        let result = store.loadEventResult()
        guard result.state == .loaded else {
            // Keep the last-good menu-bar snapshot visible when agenda.json is
            // temporarily unreadable or malformed.
            return
        }
        applySnapshot(EventSnapshot(events: result.events, now: Date()))
    }

    func applySnapshot(_ snapshot: EventSnapshot) {
        self.snapshot = snapshot
        attentionManager.setState(snapshot.attentionState)
    }

    func requestNewEvent() {
        newEventRequestToken = UUID()
    }
}

struct MenuBarBlinkView: View {
    let summary: MenuBarSummary
    let newEvent: () -> Void
    let openBlink: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(summary.statusTitle)
                .font(.headline)
            if summary.activeItems.isEmpty {
                Text("No active events")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(summary.activeItems.enumerated()), id: \.offset) { _, item in
                    Label(item.title, systemImage: symbol(for: item.attentionState))
                }
            }
            Divider()
            if let next = summary.nextItem {
                Text("Next:")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("\(next.detail) \(next.title)")
            } else {
                Text("Next: none")
                    .foregroundStyle(.secondary)
            }
            Divider()
            Button("+ New", action: newEvent)
            Button("Open Blink", action: openBlink)
        }
        .padding(.vertical, 4)
    }

    private func symbol(for state: AttentionState) -> String {
        switch state {
        case .off: return "circle"
        case .green: return "circle.fill"
        case .yellow: return "circle.fill"
        case .red: return "circle.fill"
        }
    }
}

private func menuBarGlyph(for state: AttentionState) -> String {
    switch state {
    case .off: return "○"
    case .green: return "🟢"
    case .yellow: return "🟡"
    case .red: return "🔴"
    }
}
