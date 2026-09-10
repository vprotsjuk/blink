import Foundation

public struct AttachmentManifest: Codable, Equatable {
    public let ownerID: String
    public let count: Int
    public let hasFiles: Bool

    public init(ownerID: String, count: Int, hasFiles: Bool) {
        self.ownerID = ownerID
        self.count = max(count, 0)
        self.hasFiles = hasFiles && self.count > 0
    }

    private enum CodingKeys: String, CodingKey {
        case ownerID = "owner_id"
        case count
        case hasFiles = "has_files"
    }

    public init(from decoder: Decoder) throws {
        guard let container = try? decoder.container(keyedBy: CodingKeys.self) else {
            self.ownerID = ""
            self.count = 0
            self.hasFiles = false
            return
        }
        let ownerID = (try? container.decode(String.self, forKey: .ownerID)) ?? ""
        let count = max((try? container.decode(Int.self, forKey: .count)) ?? 0, 0)
        let hasFiles = (try? container.decode(Bool.self, forKey: .hasFiles)) ?? false
        self.ownerID = ownerID
        self.count = count
        self.hasFiles = hasFiles && count > 0 && !ownerID.isEmpty
    }

    public func toDictionary() -> [String: Any] {
        [
            "owner_id": ownerID,
            "count": count,
            "has_files": hasFiles
        ]
    }
}

public final class AttachmentWorkspace {
    public let root: URL
    private let fileManager: FileManager

    public init(root: URL, fileManager: FileManager = .default) {
        self.root = root
        self.fileManager = fileManager
    }

    public func createDraft() throws -> String {
        let draftID = "draft-\(UUID().uuidString.lowercased())"
        let url = draftURL(draftID)
        try fileManager.createDirectory(at: url, withIntermediateDirectories: true)
        try Data("blink-draft-v1\n".utf8).write(to: url.appendingPathComponent(".blink-draft"), options: .atomic)
        return draftID
    }

    public func draftURL(_ draftID: String) -> URL {
        draftRoot.appendingPathComponent(safeComponent(draftID))
    }

    public func attachmentURL(ownerID: String) -> URL {
        attachmentsRoot.appendingPathComponent(safeComponent(ownerID))
    }

    /// Creates the owner folder when an editable event asks to reveal it.
    /// This intentionally does not create a manifest entry by itself; the
    /// normal event reload reconciles the folder contents with agenda.json.
    @discardableResult
    public func ensureAttachmentFolder(ownerID: String) throws -> URL {
        let target = attachmentURL(ownerID: ownerID)
        try fileManager.createDirectory(at: target, withIntermediateDirectories: true)
        return target
    }

    /// Returns visible regular files in an owner folder, ignoring hidden
    /// metadata and nested directories so previews stay predictable.
    public func files(ownerID: String) throws -> [URL] {
        try files(in: attachmentURL(ownerID: ownerID))
    }

    public func draftFiles(draftID: String) throws -> [URL] {
        try files(in: try validatedDraftURL(draftID))
    }

    public func removeDraftFile(_ url: URL, draftID: String) throws {
        let draft = try validatedDraftURL(draftID).standardizedFileURL
        let target = url.standardizedFileURL
        guard target.path.hasPrefix(draft.path + "/"),
              (try? target.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true else {
            throw NSError(domain: "BlinkAttachments", code: 3, userInfo: [NSLocalizedDescriptionKey: "Attachment is outside the current draft."])
        }
        try fileManager.removeItem(at: target)
    }

    private func files(in target: URL) throws -> [URL] {
        guard fileManager.fileExists(atPath: target.path) else { return [] }
        return try fileManager.contentsOfDirectory(
            at: target,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        ).filter { url in
            (try? url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true
        }.sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
    }

    public func addFiles(_ urls: [URL], to draftID: String) throws {
        let draft = try validatedDraftURL(draftID)
        for source in urls {
            guard source.isFileURL else { continue }
            let destination = uniqueDestination(for: source.lastPathComponent, in: draft)
            try fileManager.copyItem(at: source, to: destination)
        }
    }

    @discardableResult
    public func addJPEG(_ data: Data, to draftID: String, date: Date = Date()) throws -> URL {
        let draft = try validatedDraftURL(draftID)
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = blinkTimeZone
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        let base = "screenshot-\(formatter.string(from: date)).jpg"
        let destination = uniqueDestination(for: base, in: draft)
        try data.write(to: destination, options: .atomic)
        return destination
    }

    public func finalize(draftID: String, ownerID: String) throws -> AttachmentManifest {
        let draft = try validatedDraftURL(draftID)
        let target = attachmentURL(ownerID: ownerID)
        try fileManager.createDirectory(at: target, withIntermediateDirectories: true)
        let stagedFiles = try fileManager.contentsOfDirectory(
            at: draft,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        ).filter { url in
            (try? url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true
        }
        for source in stagedFiles {
            let destination = target.appendingPathComponent(source.lastPathComponent)
            if !fileManager.fileExists(atPath: destination.path) {
                try fileManager.copyItem(at: source, to: destination)
            }
        }
        // Keep the draft until the agenda JSON is saved. This makes a failed
        // save recoverable and lets the editor retry without losing files.
        return try manifest(ownerID: ownerID)
    }

    public func manifest(ownerID: String) throws -> AttachmentManifest {
        let files = try files(ownerID: ownerID)
        return AttachmentManifest(ownerID: ownerID, count: files.count, hasFiles: !files.isEmpty)
    }

    public func discard(draftID: String) throws {
        let draft = try validatedDraftURL(draftID)
        if fileManager.fileExists(atPath: draft.path) {
            try fileManager.removeItem(at: draft)
        }
    }

    public func cleanupStaleDrafts(olderThan age: TimeInterval = 7 * 24 * 60 * 60) {
        guard let drafts = try? fileManager.contentsOfDirectory(
            at: draftRoot,
            includingPropertiesForKeys: [.contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else { return }
        let cutoff = Date().addingTimeInterval(-age)
        for draft in drafts {
            guard draft.lastPathComponent.hasPrefix("draft-"),
                  let values = try? draft.resourceValues(forKeys: [.contentModificationDateKey]),
                  let modified = values.contentModificationDate,
                  modified < cutoff,
                  fileManager.fileExists(atPath: draft.appendingPathComponent(".blink-draft").path) else { continue }
            try? fileManager.removeItem(at: draft)
        }
    }

    public func moveOwnerToTrash(ownerID: String) throws {
        let target = attachmentURL(ownerID: ownerID)
        guard fileManager.fileExists(atPath: target.path) else { return }
        try fileManager.trashItem(at: target, resultingItemURL: nil)
    }

    private var eventDataRoot: URL { root.appendingPathComponent("event_data") }
    private var attachmentsRoot: URL { eventDataRoot.appendingPathComponent("attachments") }
    private var draftRoot: URL { eventDataRoot.appendingPathComponent("drafts") }

    private func validatedDraftURL(_ draftID: String) throws -> URL {
        let url = draftURL(draftID)
        guard fileManager.fileExists(atPath: url.appendingPathComponent(".blink-draft").path) else {
            throw NSError(domain: "BlinkAttachments", code: 1, userInfo: [NSLocalizedDescriptionKey: "Attachment draft is missing or invalid."])
        }
        return url
    }

    private func uniqueDestination(for name: String, in directory: URL) -> URL {
        let original = URL(fileURLWithPath: name).lastPathComponent
        let base = URL(fileURLWithPath: original).deletingPathExtension().lastPathComponent
        let ext = URL(fileURLWithPath: original).pathExtension
        var candidate = directory.appendingPathComponent(original)
        var index = 2
        while fileManager.fileExists(atPath: candidate.path) {
            let suffix = ext.isEmpty ? "-\(index)" : "-\(index).\(ext)"
            candidate = directory.appendingPathComponent("\(base)\(suffix)")
            index += 1
        }
        return candidate
    }

    private func safeComponent(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty,
              trimmed != ".",
              trimmed != "..",
              !trimmed.contains("/"),
              !trimmed.contains("\\") else {
            return "invalid-owner"
        }
        return trimmed
    }
}
