import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif
import Dispatch
@testable import PixeldiveSDK
import XCTest

final class NetworkCompatTests: XCTestCase {
    func testCompleteLoadMapsCallback() throws {
        let url = URL(string: "http://127.0.0.1/")!
        let response = URLResponse(
            url: url,
            mimeType: "application/json",
            expectedContentLength: 2,
            textEncodingName: nil
        )
        let pair = try completeLoad(data: Data("{}".utf8), response: response, error: nil)
        XCTAssertEqual(pair.0, Data("{}".utf8))
        XCTAssertThrowsError(try completeLoad(data: nil, response: nil, error: URLError(.timedOut)))
        XCTAssertThrowsError(try completeLoad(data: nil, response: nil, error: nil))
    }

    func testEphemeralSessionAndPublicInitFailClosed() async {
        let session = makeEphemeralSession(timeout: 1)
        XCTAssertEqual(session.configuration.timeoutIntervalForRequest, 1)
        let client = PixeldiveClient(
            baseURL: URL(string: "http://127.0.0.1:1")!,
            token: "secret",
            timeout: 1
        )
        do {
            _ = try await client.health()
            XCTFail("expected transport error")
        } catch PixeldiveError.transport {
            return
        } catch {
            XCTFail("unexpected \(error)")
        }
    }

    func testURLSessionPerformerRoundTrip() async throws {
        let server = LoopbackHTTP()
        try server.start(status: 200, body: Data("{\"status\":\"ok\"}".utf8))
        defer { server.stop() }
        let performer = URLSessionPerformer(session: makeEphemeralSession(timeout: 5))
        var request = URLRequest(url: server.url.appendingPathComponent("health"))
        request.httpMethod = "GET"
        let pair = try await performer.data(for: request)
        XCTAssertEqual(pair.0, Data("{\"status\":\"ok\"}".utf8))
        let http = try XCTUnwrap(pair.1 as? HTTPURLResponse)
        XCTAssertEqual(http.statusCode, 200)
    }

    #if canImport(ObjectiveC)
    func testRedirectDelegateDropsLocation() {
        let session = makeEphemeralSession(timeout: 1)
        let url = URL(string: "http://127.0.0.1/from")!
        let task = session.dataTask(with: url)
        let response = HTTPURLResponse(
            url: url,
            statusCode: 302,
            httpVersion: "HTTP/1.1",
            headerFields: ["Location": "https://evil.test/"]
        )!
        let expectation = expectation(description: "redirect")
        RedirectBlockingDelegate.shared.urlSession(
            session,
            task: task,
            willPerformHTTPRedirection: response,
            newRequest: URLRequest(url: URL(string: "https://evil.test/")!),
            completionHandler: { request in
                XCTAssertNil(request)
                expectation.fulfill()
            }
        )
        wait(for: [expectation], timeout: 1)
    }
    #endif
}

/// One-shot HTTP/1.1 listener so URLSession tests do not need the network.
final class LoopbackHTTP: @unchecked Sendable {
    private var fd: Int32 = -1
    private(set) var port: UInt16 = 0

    var url: URL { URL(string: "http://127.0.0.1:\(port)")! }

    func start(status: Int, body: Data) throws {
        fd = try openLoopback()
        port = try boundPort(fd)
        guard listen(fd, 1) == 0 else {
            throw URLError(.cannotDecodeRawData)
        }
        acceptOnce(listenFd: fd, status: status, body: body)
    }

    func stop() {
        if fd >= 0 {
            close(fd)
            fd = -1
        }
    }

    private func openLoopback() throws -> Int32 {
        let socketFd = socket(AF_INET, SOCK_STREAM, 0)
        guard socketFd >= 0 else {
            throw URLError(.cannotDecodeContentData)
        }
        var yes: Int32 = 1
        _ = setsockopt(socketFd, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_addr.s_addr = in_addr_t(UInt32(0x7F00_0001).bigEndian)
        addr.sin_port = 0
        let bindRc = withUnsafePointer(to: &addr) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(socketFd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard bindRc == 0 else {
            close(socketFd)
            throw URLError(.cannotDecodeRawData)
        }
        return socketFd
    }

    private func boundPort(_ socketFd: Int32) throws -> UInt16 {
        var bound = sockaddr_in()
        var length = socklen_t(MemoryLayout<sockaddr_in>.size)
        let nameRc = withUnsafeMutablePointer(to: &bound) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                getsockname(socketFd, $0, &length)
            }
        }
        guard nameRc == 0 else {
            throw URLError(.cannotDecodeRawData)
        }
        return UInt16(bigEndian: bound.sin_port)
    }

    private func acceptOnce(listenFd: Int32, status: Int, body: Data) {
        DispatchQueue.global().async {
            writeHTTP(listenFd: listenFd, status: status, body: body)
        }
    }
}

private func writeHTTP(listenFd: Int32, status: Int, body: Data) {
    var clientAddr = sockaddr_in()
    var clientLen = socklen_t(MemoryLayout<sockaddr_in>.size)
    let client = withUnsafeMutablePointer(to: &clientAddr) { pointer in
        pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            accept(listenFd, $0, &clientLen)
        }
    }
    guard client >= 0 else { return }
    var buf = [UInt8](repeating: 0, count: 2048)
    _ = buf.withUnsafeMutableBytes { raw in read(client, raw.baseAddress, raw.count) }
    let header = Data(
        "HTTP/1.1 \(status) OK\r\nContent-Length: \(body.count)\r\nConnection: close\r\n\r\n".utf8
    )
    _ = header.withUnsafeBytes { raw in write(client, raw.baseAddress, header.count) }
    _ = body.withUnsafeBytes { raw in write(client, raw.baseAddress, body.count) }
    close(client)
}
