import Foundation

public protocol AttentionOutput: AnyObject {
    func setState(_ state: AttentionState)
}

public final class AttentionManager {
    private let outputs: [AttentionOutput]
    public private(set) var state: AttentionState = .off

    public init(outputs: [AttentionOutput]) {
        self.outputs = outputs
    }

    public func setState(_ state: AttentionState) {
        guard self.state != state else { return }
        self.state = state
        for output in outputs {
            output.setState(state)
        }
    }
}

public final class RecordingAttentionOutput: AttentionOutput {
    public private(set) var states: [AttentionState] = []

    public init() {}

    public func setState(_ state: AttentionState) {
        states.append(state)
    }
}

#if canImport(AppKit)
import AppKit

@MainActor
private final class DockAttentionDriver {
    static let shared = DockAttentionDriver()

    private var timer: Timer?
    private var state: AttentionState = .off
    private var bright = true

    private init() {}

    func setState(_ state: AttentionState) {
        self.state = state
        timer?.invalidate()
        timer = nil

        if state == .off {
            NSApp.dockTile.contentView = nil
            NSApp.dockTile.display()
            return
        }

        renderDockTile()
        timer = Timer.scheduledTimer(withTimeInterval: 0.55, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.bright.toggle()
                self?.renderDockTile()
            }
        }
    }

    private func renderDockTile() {
        let view = DockPulseView(frame: NSRect(x: 0, y: 0, width: 128, height: 128))
        view.state = state
        view.bright = bright
        NSApp.dockTile.contentView = view
        NSApp.dockTile.display()
    }
}

public final class DockAttentionOutput: AttentionOutput {
    public init() {}

    public func setState(_ state: AttentionState) {
        Task { @MainActor in
            DockAttentionDriver.shared.setState(state)
        }
    }
}

final class DockPulseView: NSView {
    var state: AttentionState = .off
    var bright = true

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        NSColor.windowBackgroundColor.setFill()
        dirtyRect.fill()

        let color = nsColor(for: state).withAlphaComponent(bright ? 1.0 : 0.28)
        let inset: CGFloat = bright ? 10 : 18
        let rect = bounds.insetBy(dx: inset, dy: inset)
        let path = NSBezierPath(roundedRect: rect, xRadius: 28, yRadius: 28)
        color.setFill()
        path.fill()

        NSColor.white.withAlphaComponent(bright ? 1.0 : 0.65).setStroke()
        path.lineWidth = bright ? 8 : 4
        path.stroke()

        let text = "B" as NSString
        let attributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.boldSystemFont(ofSize: 62),
            .foregroundColor: NSColor.white
        ]
        let size = text.size(withAttributes: attributes)
        text.draw(
            at: NSPoint(x: bounds.midX - size.width / 2, y: bounds.midY - size.height / 2),
            withAttributes: attributes
        )
    }

    private func nsColor(for state: AttentionState) -> NSColor {
        switch state {
        case .off: return .clear
        case .green: return NSColor.systemGreen
        case .yellow: return NSColor.systemYellow
        case .red: return NSColor.systemRed
        }
    }
}
#endif
