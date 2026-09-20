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

func completeLoad(data: Data?, response: URLResponse?, error: Error?) throws -> (Data, URLResponse) {
    if let error {
        throw error
    }
    guard let data, let response else {
        throw URLError(.badServerResponse)
    }
    return (data, response)
}

func loadURL(_ session: URLSession, _ request: URLRequest) async throws -> (Data, URLResponse) {
    try await withCheckedThrowingContinuation { continuation in
        let task = session.dataTask(with: request) { data, response, error in
            do {
                continuation.resume(returning: try completeLoad(data: data, response: response, error: error))
            } catch {
                continuation.resume(throwing: error)
            }
        }
        task.resume()
    }
}

func makeEphemeralSession(timeout: TimeInterval) -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.timeoutIntervalForRequest = timeout
    config.timeoutIntervalForResource = timeout
    #if canImport(ObjectiveC)
    return URLSession(
        configuration: config,
        delegate: RedirectBlockingDelegate.shared,
        delegateQueue: nil
    )
    #else
    return URLSession(configuration: config)
    #endif
}

#if canImport(ObjectiveC)
/// Default sessions must not follow redirects: the Authorization header would
/// otherwise be replayed onto the Location host.
final class RedirectBlockingDelegate: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    static let shared = RedirectBlockingDelegate()

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest,
        completionHandler: @escaping (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }
}
#endif
