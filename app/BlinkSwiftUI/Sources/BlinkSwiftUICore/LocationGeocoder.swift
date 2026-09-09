import Foundation

public enum LocationGeocoderError: Error {
    case invalidResponse
    case invalidLocation
}

public struct LocationGeocoder: Sendable {
    private struct Response: Decodable {
        let results: [Result]?
    }

    private struct Result: Decodable {
        let display_name: String
        let latitude: Double
        let longitude: Double
        let timezone: String
    }

    private let root: URL

    public init(root: URL = URL(fileURLWithPath: "/Users/vitaliiprotsiuk/Desktop/Blink")) {
        self.root = root
    }

    public static func searchURL(query: String) throws -> URL {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2 else { throw LocationGeocoderError.invalidLocation }
        var components = URLComponents()
        components.scheme = "https"
        components.host = "geocoding-api.open-meteo.com"
        components.path = "/v1/search"
        components.queryItems = [
            URLQueryItem(name: "name", value: trimmed),
            URLQueryItem(name: "count", value: "10"),
            URLQueryItem(name: "language", value: "en"),
            URLQueryItem(name: "format", value: "json")
        ]
        guard let url = components.url else { throw LocationGeocoderError.invalidLocation }
        return url
    }

    public func search(query: String) async throws -> [BlinkLocation] {
        let url = try Self.searchURL(query: query)
        let data = try await Task.detached(priority: .userInitiated) {
            try Self.runResolver(root: root, query: query, url: url)
        }.value
        let decoded = try JSONDecoder().decode(Response.self, from: data)
        return (decoded.results ?? []).compactMap { result in
            guard !result.timezone.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return nil }
            return BlinkLocation(
                display_name: result.display_name,
                latitude: result.latitude,
                longitude: result.longitude,
                timezone: result.timezone,
                coordinate_source: "city"
            )
        }
    }

    public func validate(_ location: BlinkLocation) throws {
        guard FileManager.default.fileExists(atPath: root.appendingPathComponent("app/location_geocoder.py").path) else {
            return
        }
        let url = try Self.searchURL(query: "validation")
        let payload: [String: Any] = [
            "version": 1,
            "display_name": location.display_name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone
        ]
        let data = try JSONSerialization.data(withJSONObject: payload)
        let process = Process()
        let input = Pipe()
        let output = Pipe()
        process.standardInput = input
        process.standardOutput = output
        process.standardError = Pipe()
        let pythonPath = [root.appendingPathComponent(".venv/bin/python").path, "/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]
            .first { FileManager.default.isExecutableFile(atPath: $0) }
        guard let pythonPath else { throw LocationGeocoderError.invalidResponse }
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = [root.appendingPathComponent("app/location_geocoder.py").path, "--validate", "--url", url.absoluteString]
        try process.run()
        input.fileHandleForWriting.write(data)
        input.fileHandleForWriting.closeFile()
        process.waitUntilExit()
        guard process.terminationStatus == 0 else { throw LocationGeocoderError.invalidLocation }
    }

    private static func runResolver(root: URL, query: String, url: URL) throws -> Data {
        let process = Process()
        let output = Pipe()
        let errorOutput = Pipe()
        let pythonCandidates = [
            root.appendingPathComponent(".venv/bin/python").path,
            root.appendingPathComponent(".venv/bin/python3").path,
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        let pythonPath = pythonCandidates
            .first { FileManager.default.isExecutableFile(atPath: $0) }
        guard let pythonPath else { throw LocationGeocoderError.invalidResponse }
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = [
            root.appendingPathComponent("app/location_geocoder.py").path,
            "--query",
            query,
            "--url",
            url.absoluteString
        ]
        process.standardOutput = output
        process.standardError = errorOutput
        try process.run()
        process.waitUntilExit()
        let data = output.fileHandleForReading.readDataToEndOfFile()
        guard process.terminationStatus == 0 else { throw LocationGeocoderError.invalidResponse }
        return data
    }
}
