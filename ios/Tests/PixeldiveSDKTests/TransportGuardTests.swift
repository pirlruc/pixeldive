import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import PixeldiveSDK
import XCTest

final class OffOriginPerformer: HTTPPerforming, @unchecked Sendable {
    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        let response = HTTPURLResponse(
            url: URL(string: "https://evil.test/health")!,
            statusCode: 200,
            httpVersion: "HTTP/1.1",
            headerFields: ["Content-Type": "application/json"]
        )!
        return (Data("{\"status\":\"ok\"}".utf8), response)
    }
}

final class TransportGuardTests: XCTestCase {
    private let sessionID = UUID(uuidString: "123e4567-e89b-12d3-a456-426614174000")!

    func testWhitespaceTokenIsOmitted() async throws {
        let stub = StubPerformer()
        stub.steps = [try jsonStep(["status": "ok"])]
        let client = PixeldiveClient(
            baseURL: URL(string: "http://test")!,
            token: "   ",
            performer: stub
        )
        _ = try await client.health()
        XCTAssertNil(stub.requests.first?.value(forHTTPHeaderField: "Authorization"))
    }

    func testKeepsBasePathPrefix() async throws {
        let stub = StubPerformer()
        stub.steps = [try jsonStep(["status": "ok"])]
        let client = PixeldiveClient(
            baseURL: URL(string: "http://test/pixeldive")!,
            token: nil,
            performer: stub
        )
        _ = try await client.health()
        XCTAssertEqual(stub.requests.first?.url?.path, "/pixeldive/health")
    }

    func testUploadRejectsNonFileURL() async {
        let stub = StubPerformer()
        let client = PixeldiveClient(
            baseURL: URL(string: "http://test")!,
            token: nil,
            performer: stub
        )
        do {
            _ = try await client.uploadImage(
                sessionID: sessionID.uuidString,
                fileURL: URL(string: "https://evil.test/x.png")!
            )
            XCTFail("expected error")
        } catch PixeldiveError.transport {
            XCTAssertTrue(stub.requests.isEmpty)
        } catch {
            XCTFail("unexpected \(error)")
        }
    }

    func testFollowedRedirectOffOriginIsRefused() async {
        let stub = OffOriginPerformer()
        let client = PixeldiveClient(
            baseURL: URL(string: "http://test")!,
            token: "secret",
            performer: stub
        )
        do {
            _ = try await client.health()
            XCTFail("expected error")
        } catch PixeldiveError.transport(let detail) {
            XCTAssertTrue(detail.contains("redirect refused"))
        } catch {
            XCTFail("unexpected \(error)")
        }
    }

    private func jsonStep(_ object: Any) throws -> StubPerformer.Step {
        let body = try JSONSerialization.data(withJSONObject: object)
        return StubPerformer.Step(
            status: 200,
            headers: ["Content-Type": "application/json"],
            body: body
        )
    }
}
