import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Thin URLSession client for pixeldive `/api/v1` (REST; mirrors Python `RestClient`).
public struct PixeldiveClient: Sendable {
    let http: HTTPTransport

    /// Bind a base URL, optional bearer token, and optional shared session.
    public init(
        baseURL: URL,
        token: String? = nil,
        session: URLSession? = nil,
        timeout: TimeInterval = 60
    ) {
        let resolved = session ?? makeEphemeralSession(timeout: timeout)
        self.init(baseURL: baseURL, token: token, performer: URLSessionPerformer(session: resolved))
    }

    init(baseURL: URL, token: String?, performer: HTTPPerforming) {
        self.http = HTTPTransport(baseURL: baseURL, token: token, performer: performer)
    }

    /// GET `/health`.
    public func health() async throws -> HealthStatus {
        try await http.json("GET", path: "/health")
    }

    /// GET `/ready`.
    public func ready() async throws -> HealthStatus {
        try await http.json("GET", path: "/ready")
    }

    /// POST `/api/v1/sessions`.
    public func createSession(_ payload: SessionCreate) async throws -> SessionRead {
        try await http.json("POST", path: "/api/v1/sessions", body: payload)
    }

    /// GET `/api/v1/sessions`.
    public func listSessions(limit: Int = 50, cursor: String? = nil) async throws -> SessionPage {
        try await http.json("GET", path: "/api/v1/sessions", query: pageQuery(limit: limit, cursor: cursor))
    }

    /// GET `/api/v1/sessions/{id}`.
    public func getSession(id: String) async throws -> SessionRead {
        let sessionID = try ResourceID.parse(id)
        return try await http.json("GET", path: "/api/v1/sessions/\(sessionID)")
    }

    /// PUT `/api/v1/sessions/{id}`.
    public func updateSession(id: String, payload: SessionUpdate) async throws -> SessionRead {
        let sessionID = try ResourceID.parse(id)
        return try await http.json("PUT", path: "/api/v1/sessions/\(sessionID)", body: payload)
    }

    /// DELETE `/api/v1/sessions/{id}`.
    public func deleteSession(id: String) async throws {
        let sessionID = try ResourceID.parse(id)
        try await http.empty("DELETE", path: "/api/v1/sessions/\(sessionID)")
    }

    /// POST multipart `/api/v1/sessions/{id}/images`.
    public func uploadImage(
        sessionID: String,
        filename: String,
        payload: Data,
        contentType: String = "image/png",
        metadata: String? = nil
    ) async throws -> SessionImage {
        let parsed = try ResourceID.parse(sessionID)
        var fields: [String: String] = [:]
        if let metadata {
            fields["metadata"] = metadata
        }
        let form = MultipartForm.make(
            fileField: "file",
            filename: filename,
            payload: payload,
            contentType: contentType,
            fields: fields
        )
        return try await http.upload("/api/v1/sessions/\(parsed)/images", form: form)
    }

    /// POST multipart `/api/v1/sessions/{id}/images/batch`.
    public func uploadImagesBatch(
        sessionID: String,
        items: [(filename: String, payload: Data, contentType: String)],
        metadata: String? = nil
    ) async throws -> [SessionImage] {
        let parsed = try ResourceID.parse(sessionID)
        var fields: [String: String] = [:]
        if let metadata {
            fields["metadata"] = metadata
        }
        let form = MultipartForm.makeBatch(items: items, fields: fields)
        return try await http.upload("/api/v1/sessions/\(parsed)/images/batch", form: form)
    }

    /// GET `/api/v1/sessions/{id}/images`.
    public func listImages(sessionID: String, limit: Int = 50, cursor: String? = nil) async throws -> ImagePage {
        let parsed = try ResourceID.parse(sessionID)
        return try await http.json(
            "GET",
            path: "/api/v1/sessions/\(parsed)/images",
            query: pageQuery(limit: limit, cursor: cursor)
        )
    }

    /// GET `/api/v1/sessions/{id}/images/{image_id}` as in-memory bytes.
    public func downloadImage(sessionID: String, imageID: String) async throws -> Data {
        let parsedSession = try ResourceID.parse(sessionID)
        let parsedImage = try ResourceID.parse(imageID)
        return try await http.download("/api/v1/sessions/\(parsedSession)/images/\(parsedImage)")
    }

    /// POST multipart from a file URL without requiring the caller to buffer first.
    public func uploadImage(
        sessionID: String,
        fileURL: URL,
        filename: String? = nil,
        contentType: String = "image/png",
        metadata: String? = nil
    ) async throws -> SessionImage {
        let data = try Data(contentsOf: fileURL)
        return try await uploadImage(
            sessionID: sessionID,
            filename: filename ?? fileURL.lastPathComponent,
            payload: data,
            contentType: contentType,
            metadata: metadata
        )
    }
}
