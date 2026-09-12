import Dispatch
import Foundation

#if canImport(Darwin)
import Darwin
#endif

/// Observes the directory containing agenda.json so atomic file replacement
/// remains visible even when the agenda inode changes.
public final class AgendaDirectoryObserver {
    public typealias ChangeHandler = () -> Void
    public typealias FailureHandler = (Error) -> Void

    private let parentDirectoryURL: URL
    private let callbackQueue: DispatchQueue
    private let eventQueue: DispatchQueue
    private let debounceInterval: TimeInterval
    private let onChange: ChangeHandler
    private let onFailure: FailureHandler
    private let stateLock = NSLock()
    private var source: DispatchSourceFileSystemObject?
    private var pendingChange: DispatchWorkItem?
    private var lastSignature: AgendaSignature?

    private struct AgendaSignature: Equatable {
        let inode: UInt64?
        let size: Int64?
        let modificationTime: TimeInterval?
    }

    public init(
        agendaURL: URL,
        debounceInterval: TimeInterval = 0.2,
        callbackQueue: DispatchQueue = .main,
        onChange: @escaping ChangeHandler,
        onFailure: @escaping FailureHandler = { _ in }
    ) {
        self.parentDirectoryURL = agendaURL.deletingLastPathComponent()
        self.callbackQueue = callbackQueue
        self.eventQueue = DispatchQueue(label: "com.vitalii.blink.agenda-directory-observer")
        self.debounceInterval = max(0, debounceInterval)
        self.onChange = onChange
        self.onFailure = onFailure
    }

    deinit {
        stop()
    }

    public func start() {
        stateLock.lock()
        let alreadyStarted = source != nil
        stateLock.unlock()
        if alreadyStarted { return }

        #if canImport(Darwin)
        let descriptor = open(parentDirectoryURL.path, O_EVTONLY)
        #else
        let descriptor: Int32 = -1
        #endif
        guard descriptor >= 0 else {
            reportFailure(
                NSError(
                    domain: NSPOSIXErrorDomain,
                    code: Int(errno),
                    userInfo: [NSLocalizedDescriptionKey: "Could not observe agenda parent directory."]
                )
            )
            return
        }

        let eventMask: DispatchSource.FileSystemEvent = [
            .write, .extend, .attrib, .link, .rename, .delete, .revoke
        ]
        let newSource = DispatchSource.makeFileSystemObjectSource(
            fileDescriptor: descriptor,
            eventMask: eventMask,
            queue: eventQueue
        )
        newSource.setEventHandler { [weak self] in
            self?.scheduleChange()
        }
        newSource.setCancelHandler {
            #if canImport(Darwin)
            close(descriptor)
            #endif
        }

        stateLock.lock()
        if source == nil {
            lastSignature = signature()
            source = newSource
            stateLock.unlock()
            newSource.resume()
        } else {
            stateLock.unlock()
            newSource.cancel()
        }
    }

    public func stop() {
        stateLock.lock()
        let currentSource = source
        source = nil
        pendingChange?.cancel()
        pendingChange = nil
        stateLock.unlock()
        currentSource?.cancel()
    }

    private func scheduleChange() {
        stateLock.lock()
        guard source != nil else {
            stateLock.unlock()
            return
        }
        pendingChange?.cancel()
        let work = DispatchWorkItem { [weak self] in
            self?.deliverChangeIfNeeded()
        }
        pendingChange = work
        stateLock.unlock()
        callbackQueue.asyncAfter(deadline: .now() + debounceInterval, execute: work)
    }

    private func reportFailure(_ error: Error) {
        onFailure(error)
    }

    private func deliverChangeIfNeeded() {
        let current = signature()
        stateLock.lock()
        guard source != nil, current != lastSignature else {
            stateLock.unlock()
            return
        }
        lastSignature = current
        stateLock.unlock()
        onChange()
    }

    private func signature() -> AgendaSignature? {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: parentDirectoryURL.appendingPathComponent("agenda.json").path) else {
            return nil
        }
        let inode = (attributes[.systemFileNumber] as? NSNumber)?.uint64Value
        let size = (attributes[.size] as? NSNumber)?.int64Value
        let modificationTime = (attributes[.modificationDate] as? Date)?.timeIntervalSinceReferenceDate
        return AgendaSignature(inode: inode, size: size, modificationTime: modificationTime)
    }
}
