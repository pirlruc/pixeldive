import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Byte transport used by ``HTTPTransport``. Tests inject a stub so Linux CI
/// does not depend on URLProtocol (libcurl URLSession ignores it).
protocol HTTPPerforming: Sendable {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
}

struct URLSessionPerformer: HTTPPerforming, @unchecked Sendable {
    let session: URLSession

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        try await loadURL(session, request)
    }
}

func loadURL(_ session: URLSession, _ request: URLRequest) async throws -> (Data, URLResponse) {
    try await withCheckedThrowingContinuation { continuation in
        let task = session.dataTask(with: request) { data, response, error in
            if let error {
                continuation.resume(throwing: error)
                return
            }
            guard let data, let response else {
                continuation.resume(throwing: URLError(.badServerResponse))
                return
            }
            continuation.resume(returning: (data, response))
        }
        task.resume()
    }
}

func makeEphemeralSession(timeout: TimeInterval) -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.timeoutIntervalForRequest = timeout
    config.timeoutIntervalForResource = timeout
    return URLSession(configuration: config)
}
