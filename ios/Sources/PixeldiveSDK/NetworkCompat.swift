import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

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

func makeEphemeralSession(timeout: TimeInterval, protocolClasses: [AnyClass]? = nil) -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.timeoutIntervalForRequest = timeout
    config.timeoutIntervalForResource = timeout
    if let protocolClasses {
        config.protocolClasses = protocolClasses
    }
    return URLSession(configuration: config)
}
