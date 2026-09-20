import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import PixeldiveSDK
import XCTest

final class StubURLProtocol: URLProtocol, @unchecked Sendable {
    struct Step: Sendable {
        var status: Int
        var headers: [String: String]
        var body: Data
    }

    nonisolated(unsafe) static var steps: [Step] = []
    nonisolated(unsafe) static var requests: [URLRequest] = []
    nonisolated(unsafe) static var bodies: [Data] = []

    static func reset() {
        steps = []
        requests = []
        bodies = []
    }

    override class func canInit(with request: URLRequest) -> Bool { true }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        Self.requests.append(request)
        Self.bodies.append(readBody(request))
        guard !Self.steps.isEmpty else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }
        let step = Self.steps.removeFirst()
        let response = HTTPURLResponse(
            url: request.url ?? URL(string: "http://test")!,
            statusCode: step.status,
            httpVersion: "HTTP/1.1",
            headerFields: step.headers
        )!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: step.body)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

func readBody(_ request: URLRequest) -> Data {
    if let body = request.httpBody {
        return body
    }
    guard let stream = request.httpBodyStream else {
        return Data()
    }
    stream.open()
    defer { stream.close() }
    var data = Data()
    let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 4096)
    defer { buffer.deallocate() }
    while stream.hasBytesAvailable {
        let count = stream.read(buffer, maxLength: 4096)
        if count <= 0 {
            break
        }
        data.append(buffer, count: count)
    }
    return data
}

final class ClientTests: XCTestCase {
    private let sessionID = UUID(uuidString: "123e4567-e89b-12d3-a456-426614174000")!
    private let imageID = UUID(uuidString: "123e4567-e89b-12d3-a456-426614174001")!

    override func setUp() {
        super.setUp()
        StubURLProtocol.reset()
    }

    func testHealthReadyAndSessionRoundTrip() async throws {
        StubURLProtocol.steps = [
            jsonStep(["status": "ok"]),
            jsonStep(["status": "ok"]),
            jsonStep(sessionJSON()),
            jsonStep(["items": [sessionJSON()], "next_cursor": NSNull()]),
            jsonStep(sessionJSON()),
            jsonStep(sessionJSON()),
            StubURLProtocol.Step(status: 204, headers: [:], body: Data()),
        ]
        let client = makeClient()
        let health = try await client.health()
        XCTAssertEqual(health.status, "ok")
        let ready = try await client.ready()
        XCTAssertEqual(ready.status, "ok")
        let created = try await client.createSession(DeviceSnapshot.sampleiPhone())
        XCTAssertEqual(created.id, sessionID)
        let listed = try await client.listSessions(limit: 10)
        XCTAssertEqual(listed.items.first?.id, sessionID)
        _ = try await client.getSession(id: sessionID.uuidString)
        _ = try await client.updateSession(
            id: sessionID.uuidString,
            payload: SessionUpdate(metadata: ["k": .string("v")], mergeMetadata: true)
        )
        try await client.deleteSession(id: sessionID.uuidString)
        XCTAssertEqual(StubURLProtocol.requests.map(\.httpMethod), [
            "GET", "GET", "POST", "GET", "GET", "PUT", "DELETE",
        ])
        let createBody = StubURLProtocol.bodies[2]
        XCTAssertFalse(createBody.isEmpty)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: createBody) as? [String: Any])
        XCTAssertEqual((object["phone_info"] as? [String: Any])?["sdk_int"] as? Int, 18)
    }

    func testUploadListDownload() async throws {
        let png = TestPNG.bytes
        StubURLProtocol.steps = [
            jsonStep(imageJSON()),
            jsonStep(["items": [imageJSON()], "next_cursor": NSNull()]),
            StubURLProtocol.Step(
                status: 200,
                headers: ["Content-Type": "image/png"],
                body: png
            ),
        ]
        let client = makeClient()
        let uploaded = try await client.uploadImage(
            sessionID: sessionID.uuidString,
            filename: "frame.png",
            payload: png,
            metadata: "{\"iso\":64}"
        )
        XCTAssertEqual(uploaded.id, imageID)
        XCTAssertNil(Mirror(reflecting: uploaded).children.first { $0.label == "storagePath" })
        let listed = try await client.listImages(sessionID: sessionID.uuidString)
        XCTAssertEqual(listed.items.count, 1)
        let downloaded = try await client.downloadImage(
            sessionID: sessionID.uuidString,
            imageID: imageID.uuidString
        )
        XCTAssertEqual(downloaded, png)
        let upload = StubURLProtocol.requests[0]
        XCTAssertEqual(upload.httpMethod, "POST")
        let contentType = try XCTUnwrap(upload.value(forHTTPHeaderField: "Content-Type"))
        XCTAssertTrue(contentType.hasPrefix("multipart/form-data"))
        let body = StubURLProtocol.bodies[0]
        XCTAssertFalse(body.isEmpty)
        XCTAssertTrue(
            String(data: body, encoding: .utf8)?.contains("filename=\"frame.png\"") == true
                || body.contains(png)
        )
    }

    func testUploadBatchAndFile() async throws {
        StubURLProtocol.steps = [
            jsonStep([imageJSON()]),
            jsonStep(imageJSON()),
        ]
        let client = makeClient()
        let batch = try await client.uploadImagesBatch(
            sessionID: sessionID.uuidString,
            items: [("a.png", TestPNG.bytes, "image/png")]
        )
        XCTAssertEqual(batch.count, 1)
        let temp = FileManager.default.temporaryDirectory.appendingPathComponent("frame.png")
        try TestPNG.bytes.write(to: temp)
        _ = try await client.uploadImage(sessionID: sessionID.uuidString, fileURL: temp)
        try? FileManager.default.removeItem(at: temp)
    }

    func testHTTPErrorAndAuthHeader() async {
        StubURLProtocol.steps = [
            StubURLProtocol.Step(status: 404, headers: [:], body: Data("{\"detail\":\"gone\"}".utf8)),
        ]
        let client = makeClient(token: "secret-token")
        do {
            _ = try await client.health()
            XCTFail("expected error")
        } catch PixeldiveError.httpStatus(let code, let body) {
            XCTAssertEqual(code, 404)
            XCTAssertTrue(body.contains("gone"))
        } catch {
            XCTFail("unexpected \(error)")
        }
        XCTAssertEqual(
            StubURLProtocol.requests.first?.value(forHTTPHeaderField: "Authorization"),
            "Bearer secret-token"
        )
    }

    func testRejectsNonUUIDSession() async {
        let client = makeClient()
        do {
            _ = try await client.getSession(id: "../etc/passwd")
            XCTFail("expected error")
        } catch PixeldiveError.invalidResourceID {
            return
        } catch {
            XCTFail("unexpected \(error)")
        }
    }

    private func makeClient(token: String? = nil) -> PixeldiveClient {
        let session = makeEphemeralSession(timeout: 60, protocolClasses: [StubURLProtocol.self])
        return PixeldiveClient(
            baseURL: URL(string: "http://test")!,
            token: token,
            session: session
        )
    }

    private func jsonStep(_ object: Any) -> StubURLProtocol.Step {
        let body = try! JSONSerialization.data(withJSONObject: object)
        return StubURLProtocol.Step(
            status: 200,
            headers: ["Content-Type": "application/json"],
            body: body
        )
    }

    private func sessionJSON() -> [String: Any] {
        [
            "id": sessionID.uuidString.lowercased(),
            "session_name": "ios-demo-capture",
            "status": "CREATED",
            "created_at": "2026-09-20T12:00:00.000000Z",
            "updated_at": "2026-09-20T12:00:00.000000Z",
            "phone_info": [
                "manufacturer": "Apple",
                "model": "iPhone 16 Pro",
                "brand": "apple",
                "device": "iPhone17,1",
                "board": "iPhone17,1",
                "android_version": "18.6",
                "sdk_int": 18,
            ],
            "phone_capabilities": [
                "total_ram_mb": 8192,
                "available_ram_mb": 4096,
                "cpu_abi": "arm64",
                "cpu_cores": 6,
                "screen_width_px": 1206,
                "screen_height_px": 2622,
                "screen_density_dpi": 460,
                "is_low_ram_device": false,
            ],
            "camera_capabilities": [
                "camera_count": 0,
                "cameras": [],
            ],
            "metadata": ["source": "pixeldive-ios-sdk"],
        ]
    }

    private func imageJSON() -> [String: Any] {
        [
            "id": imageID.uuidString.lowercased(),
            "session_id": sessionID.uuidString.lowercased(),
            "filename": "frame.png",
            "content_type": "image/png",
            "size_bytes": TestPNG.bytes.count,
            "uploaded_at": "2026-09-20T12:00:00.000000Z",
            "metadata": ["iso": 64],
        ]
    }
}

enum TestPNG {
    static let bytes = Data([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
        0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
        0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
        0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
    ])
}
