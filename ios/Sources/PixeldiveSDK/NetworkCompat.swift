import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Byte transport used by ``HTTPTransport``. Tests inject a stub so Linux CI
/// does not depend on URLProtocol (libcurl URLSession ignores it).
protocol HTTPPerforming: Sendable {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
    func data(for request: URLRequest, fromFile fileURL: URL) async throws -> (Data, URLResponse)
}

extension HTTPPerforming {
    func data(for request: URLRequest, fromFile fileURL: URL) async throws -> (Data, URLResponse) {
        var copy = request
        copy.httpBody = try Data(contentsOf: fileURL)
        return try await data(for: copy)
    }
}

struct URLSessionPerformer: HTTPPerforming, @unchecked Sendable {
    let session: URLSession

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        try await loadURL(session, request)
    }

    func data(for request: URLRequest, fromFile fileURL: URL) async throws -> (Data, URLResponse) {
        try await uploadURL(session, request, fileURL)
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
    try await runTask(session, request, fileURL: nil)
}

func uploadURL(_ session: URLSession, _ request: URLRequest, _ fileURL: URL) async throws -> (Data, URLResponse) {
    #if canImport(FoundationNetworking)
    // libcurl URLSession's uploadTask(fromFile:) traps in _BodyFileSource on Linux.
    var copy = request
    copy.httpBody = try Data(contentsOf: fileURL)
    return try await loadURL(session, copy)
    #else
    try await runTask(session, request, fileURL: fileURL)
    #endif
}

func runTask(
    _ session: URLSession,
    _ request: URLRequest,
    fileURL: URL?
) async throws -> (Data, URLResponse) {
    let box = TaskBox()
    return try await withTaskCancellationHandler {
        try await withCheckedThrowingContinuation { continuation in
            let task: URLSessionTask
            if let fileURL {
                task = session.uploadTask(with: request, fromFile: fileURL) { data, response, error in
                    finish(continuation, data: data, response: response, error: error)
                }
            } else {
                task = session.dataTask(with: request) { data, response, error in
                    finish(continuation, data: data, response: response, error: error)
                }
            }
            box.task = task
            task.resume()
        }
    } onCancel: {
        box.task?.cancel()
    }
}

func finish(
    _ continuation: CheckedContinuation<(Data, URLResponse), Error>,
    data: Data?,
    response: URLResponse?,
    error: Error?
) {
    do {
        continuation.resume(returning: try completeLoad(data: data, response: response, error: error))
    } catch {
        continuation.resume(throwing: error)
    }
}

func redirectSafeSession(existing: URLSession?, timeout: TimeInterval) -> URLSession {
    guard let existing else {
        return makeEphemeralSession(timeout: timeout)
    }
    #if canImport(ObjectiveC)
    return URLSession(
        configuration: existing.configuration,
        delegate: RedirectBlockingDelegate.shared,
        delegateQueue: nil
    )
    #else
    return existing
    #endif
}

private final class TaskBox: @unchecked Sendable {
    var task: URLSessionTask?
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
