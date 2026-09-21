import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

struct HTTPTransport: @unchecked Sendable {
    let baseURL: URL
    let token: String?
    let performer: HTTPPerforming

    func json<Body: Encodable, Result: Decodable>(
        _ method: String,
        path: String,
        body: Body
    ) async throws -> Result {
        let data = try JSONCodec.makeEncoder().encode(body)
        let response = try await dataRequest(method, path: path, payload: data, contentType: "application/json")
        return try decode(Result.self, from: response)
    }

    func json<Result: Decodable>(_ method: String, path: String, query: [String: String] = [:]) async throws -> Result {
        let response = try await dataRequest(method, path: path, query: query, payload: nil, contentType: nil)
        return try decode(Result.self, from: response)
    }

    func empty(_ method: String, path: String) async throws {
        _ = try await dataRequest(method, path: path, payload: nil, contentType: nil)
    }

    func upload<Result: Decodable>(_ path: String, form: MultipartForm) async throws -> Result {
        if let fileURL = form.fileURL {
            let response = try await fileRequest(path, fileURL: fileURL, contentType: form.contentType)
            return try decode(Result.self, from: response)
        }
        let response = try await dataRequest(
            "POST",
            path: path,
            payload: form.body,
            contentType: form.contentType
        )
        return try decode(Result.self, from: response)
    }

    func download(_ path: String) async throws -> Data {
        try await dataRequest("GET", path: path, payload: nil, contentType: nil)
    }

    private func dataRequest(
        _ method: String,
        path: String,
        query: [String: String] = [:],
        payload: Data?,
        contentType: String?
    ) async throws -> Data {
        var request = URLRequest(url: try makeURL(path: path, query: query))
        request.httpMethod = method
        request.httpBody = payload
        if let contentType {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        applyBearer(&request)
        return try await send(request)
    }

    private func fileRequest(_ path: String, fileURL: URL, contentType: String) async throws -> Data {
        var request = URLRequest(url: try makeURL(path: path, query: [:]))
        request.httpMethod = "POST"
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        applyBearer(&request)
        return try await send(request, fromFile: fileURL)
    }

    private func applyBearer(_ request: inout URLRequest) {
        let trimmed = token?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if !trimmed.isEmpty {
            request.setValue("Bearer \(trimmed)", forHTTPHeaderField: "Authorization")
        }
    }

    private func makeURL(path: String, query: [String: String]) throws -> URL {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw PixeldiveError.transport("invalid base URL")
        }
        let basePath = components.path.hasSuffix("/") ? String(components.path.dropLast()) : components.path
        components.path = basePath + path
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components.url else {
            throw PixeldiveError.transport("invalid request URL")
        }
        return url
    }

    private func send(_ request: URLRequest, fromFile fileURL: URL? = nil) async throws -> Data {
        let pair: (Data, URLResponse)
        do {
            if let fileURL {
                pair = try await performer.data(for: request, fromFile: fileURL)
            } else {
                pair = try await performer.data(for: request)
            }
        } catch {
            throw PixeldiveError.transport(error.localizedDescription)
        }
        return try accept(pair, request: request)
    }

    private func accept(_ pair: (Data, URLResponse), request: URLRequest) throws -> Data {
        guard let http = pair.1 as? HTTPURLResponse else {
            throw PixeldiveError.transport("non-HTTP response")
        }
        if redirectedOffOrigin(request: request, response: http) {
            throw PixeldiveError.transport("redirect refused")
        }
        // Refuse 3xx as well as 4xx/5xx so a redirect cannot look like success
        // when the session still followed it (SWIFT-SEC / Authorization leak).
        if http.statusCode < 200 || http.statusCode >= 300 {
            let body = String(data: pair.0.prefix(2048), encoding: .utf8) ?? ""
            throw PixeldiveError.httpStatus(http.statusCode, body: body)
        }
        return pair.0
    }

    private func decode<Result: Decodable>(_ type: Result.Type, from data: Data) throws -> Result {
        do {
            return try JSONCodec.makeDecoder().decode(type, from: data)
        } catch {
            throw PixeldiveError.decoding(String(describing: error))
        }
    }
}

func pageQuery(limit: Int, cursor: String?) -> [String: String] {
    var query = ["limit": String(limit)]
    if let cursor, !cursor.isEmpty {
        query["cursor"] = cursor
    }
    return query
}

func redirectedOffOrigin(request: URLRequest, response: HTTPURLResponse) -> Bool {
    guard let requested = request.url, let final = response.url else {
        return false
    }
    return requested.host?.lowercased() != final.host?.lowercased()
        || requested.scheme?.lowercased() != final.scheme?.lowercased()
}
