import Foundation
import Darwin

/// Interoperable advisory lock shared with Python's `fcntl.flock`.
public final class AgendaFileLock {
    private let descriptor: Int32

    public init(root: URL, blocking: Bool = true) throws {
        let lockURL = root.appendingPathComponent("agenda.lock")
        try FileManager.default.createDirectory(
            at: root,
            withIntermediateDirectories: true
        )
        let opened = open(lockURL.path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
        guard opened >= 0 else {
            throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO)
        }
        descriptor = opened

        var operation = Int32(LOCK_EX)
        if !blocking {
            operation |= Int32(LOCK_NB)
        }
        guard flock(descriptor, operation) == 0 else {
            let code = POSIXErrorCode(rawValue: errno) ?? .EIO
            close(descriptor)
            throw POSIXError(code)
        }
    }

    deinit {
        _ = flock(descriptor, LOCK_UN)
        close(descriptor)
    }
}
