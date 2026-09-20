import Foundation
import PixeldiveSDK
import SwiftUI

/// UI state for the capture demo. All service calls go through ``PixeldiveClient``.
@MainActor
final class DemoModel: ObservableObject {
    @Published var baseURLText = "http://127.0.0.1:8000"
    @Published var token = ""
    @Published var log = "Ready."
    @Published var sessions: [SessionRead] = []
    @Published var images: [SessionImage] = []
    @Published var selectedSession: SessionRead?
    @Published var preview: Data?
    @Published var busy = false

    func createSession() async {
        await run("create session") { client in
            let payload = DeviceSnapshot.current(sessionName: "ios-demo-\(Self.stamp())")
            let created = try await client.createSession(payload)
            self.selectedSession = created
            self.log = "Created \(created.id.uuidString.lowercased())"
            try await self.refresh(client)
        }
    }

    func refresh() async {
        await run("refresh") { client in
            try await self.refresh(client)
            self.log = "Listed \(self.sessions.count) sessions"
        }
    }

    func upload(data: Data, filename: String, contentType: String) async {
        guard let session = selectedSession else {
            log = "Create or select a session first."
            return
        }
        await run("upload") { client in
            let image = try await client.uploadImage(
                sessionID: session.id.uuidString,
                filename: filename,
                payload: data,
                contentType: contentType
            )
            self.log = "Uploaded \(image.filename) (\(image.sizeBytes) bytes)"
            try await self.refresh(client)
        }
    }

    func downloadFirst() async {
        guard let session = selectedSession, let image = images.first else {
            log = "No image to download."
            return
        }
        await run("download") { client in
            let bytes = try await client.downloadImage(
                sessionID: session.id.uuidString,
                imageID: image.id.uuidString
            )
            self.preview = bytes
            self.log = "Downloaded \(bytes.count) bytes"
        }
    }

    func deleteSelected() async {
        guard let session = selectedSession else {
            log = "No session selected."
            return
        }
        await run("delete") { client in
            try await client.deleteSession(id: session.id.uuidString)
            self.selectedSession = nil
            self.images = []
            self.preview = nil
            try await self.refresh(client)
            self.log = "Deleted session"
        }
    }

    private func refresh(_ client: PixeldiveClient) async throws {
        let page = try await client.listSessions(limit: 20)
        sessions = page.items
        if selectedSession == nil {
            selectedSession = page.items.first
        }
        guard let session = selectedSession else {
            images = []
            return
        }
        let listed = try await client.listImages(sessionID: session.id.uuidString)
        images = listed.items
    }

    private func run(_ label: String, body: (PixeldiveClient) async throws -> Void) async {
        busy = true
        defer { busy = false }
        do {
            try await body(makeClient())
        } catch {
            log = "\(label) failed: \(error.localizedDescription)"
        }
    }

    private func makeClient() throws -> PixeldiveClient {
        guard let url = URL(string: baseURLText), url.scheme != nil else {
            throw PixeldiveError.transport("invalid base URL")
        }
        let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
        return PixeldiveClient(baseURL: url, token: trimmed.isEmpty ? nil : trimmed)
    }

    private static func stamp() -> String {
        ISO8601DateFormatter().string(from: Date())
    }
}
