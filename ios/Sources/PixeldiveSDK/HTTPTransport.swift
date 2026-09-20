import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

struct HTTPTransport: @unchecked Sendable {
    let baseURL: URL
    let token: String?
    let performer: HTTPPerforming
    let encoder: JSONEncoder
    let decoder: JSONDecoder

    init(baseURL: URL, token: String?, performer: HTTPPerforming) {
        self.baseURL = baseURL
        self.token = token
        self.performer = performer
        self.encoder = JSONCodec.makeEncoder()
        self.decoder = JSONCodec.makeDecoder()
    }

    func json<Body: Encodable, Result: Decodable>(
        _ method: String,
        path: String,
        body: Body
    ) async throws -> Result {
        let data = try encoder.encode(body)
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
        let url = try makeURL(path: path, query: query)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = payload
        if let contentType {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        if let token, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return try await send(request)
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

    private func send(_ request: URLRequest) async throws -> Data {
        let pair: (Data, URLResponse)
        do {
            pair = try await performer.data(for: request)
        } catch {
            throw PixeldiveError.transport(error.localizedDescription)
        }
        guard let http = pair.1 as? HTTPURLResponse else {
            throw PixeldiveError.transport("non-HTTP response")
        }
        // Refuse 3xx as well as 4xx/5xx so a redirect cannot look like success
        // when the session still followed it (SWIFT-SEC / Authorization leak).
        if http.statusCode < 200 || http.statusCode >= 300 {
            let body = String(data: pair.0, encoding: .utf8) ?? ""
            throw PixeldiveError.httpStatus(http.statusCode, body: body)
        }
        return pair.0
    }

    private func decode<Result: Decodable>(_ type: Result.Type, from data: Data) throws -> Result {
        do {
            return try decoder.decode(type, from: data)
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
