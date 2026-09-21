import Foundation
import PixeldiveSDK
import SwiftUI

/// UI state for the capture demo. Sessions use REST; image bytes use gRPC.
@MainActor
final class DemoModel: ObservableObject {
    @Published var baseURLText = "http://127.0.0.1:8000"
    @Published var grpcHost = "127.0.0.1"
    @Published var grpcPort = "50051"
    @Published var token = ""
    @Published var log = "Ready."
    @Published var sessions: [SessionRead] = []
    @Published var images: [SessionImage] = []
    @Published var selectedSession: SessionRead?
    @Published var preview: Data?
    @Published var busy = false
    @Published var capturing = false

    let camera = CameraFeed()
    private var uploading = false
    private var grpcKey: String?
    private var grpc: PixeldiveGrpcClient?

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
        await sendFrame(session: session, data: data, filename: filename, contentType: contentType)
    }

    func startCamera() {
        guard selectedSession != nil else {
            log = "Create or select a session first."
            return
        }
        camera.onJPEG = { [weak self] data in
            Task { await self?.upload(data: data, filename: "frame.jpg", contentType: "image/jpeg") }
        }
        camera.requestAndStart()
        capturing = true
        log = "Camera feed → gRPC UploadImage"
    }

    func stopCamera() {
        capturing = false
        camera.onJPEG = nil
        camera.stop()
        log = "Camera stopped."
    }

    func downloadFirst() async {
        guard let session = selectedSession, let image = images.first else {
            log = "No image to download."
            return
        }
        do {
            let bytes = try await grpcClient().downloadImage(
                sessionID: session.id.uuidString,
                imageID: image.id.uuidString
            )
            preview = bytes
            log = "Downloaded \(bytes.count) bytes via gRPC"
        } catch {
            log = "download failed: \(error.localizedDescription)"
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

    private func sendFrame(
        session: SessionRead,
        data: Data,
        filename: String,
        contentType: String
    ) async {
        if uploading {
            return
        }
        uploading = true
        camera.setBusy(true)
        defer {
            uploading = false
            camera.setBusy(false)
        }
        do {
            let image = try await grpcClient().uploadImage(
                sessionID: session.id.uuidString,
                filename: filename,
                payload: data,
                contentType: contentType
            )
            log = "Uploaded \(image.filename) (\(image.sizeBytes) bytes) via gRPC"
            record(image)
        } catch {
            log = "upload failed: \(error.localizedDescription)"
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

    private func record(_ image: SessionImage) {
        if images.contains(where: { $0.id == image.id }) {
            return
        }
        images.insert(image, at: 0)
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

    private func grpcClient() throws -> PixeldiveGrpcClient {
        let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
        let key = "\(grpcHost)|\(grpcPort)|\(trimmed)"
        if let grpc, grpcKey == key {
            return grpc
        }
        grpc?.close()
        #if canImport(GRPC)
        let port = Int(grpcPort) ?? 50051
        let created = PixeldiveGrpcClient.insecure(
            host: grpcHost,
            port: port,
            token: trimmed.isEmpty ? nil : trimmed
        )
        grpc = created
        grpcKey = key
        return created
        #else
        throw PixeldiveError.transport("gRPC streaming requires Apple platforms")
        #endif
    }

    private static func stamp() -> String {
        ISO8601DateFormatter().string(from: Date())
    }
}
