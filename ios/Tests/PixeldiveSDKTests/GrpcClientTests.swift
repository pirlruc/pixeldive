import Foundation
@testable import PixeldiveSDK
import XCTest

final class StubGrpc: GrpcStreaming, @unchecked Sendable {
    var response: Data
    var serverMessages: [Data]
    var clientPath: String?
    var serverPath: String?
    var token: String?
    var clientMessages: [Data] = []

    init(response: Data, serverMessages: [Data] = []) {
        self.response = response
        self.serverMessages = serverMessages
    }

    func clientStreaming(path: String, messages: [Data], token: String?) async throws -> Data {
        clientPath = path
        clientMessages = messages
        self.token = token
        return response
    }

    func serverStreaming(path: String, request: Data, token: String?) async throws -> [Data] {
        serverPath = path
        self.token = token
        return serverMessages
    }
}

final class GrpcClientTests: XCTestCase {
    private let sessionID = "123e4567-e89b-12d3-a456-426614174000"
    private let imageID = "123e4567-e89b-12d3-a456-426614174001"
    private let uploadHex =
        "0a6c0a2431323365343536372d653839622d313264332d613435362d343236363134313734303031"
        + "122431323365343536372d653839622d313264332d613435362d343236363134313734303030"
        + "1a096672616d652e706e672209696d6167652f706e6728433a0608c095bfd506"

    func testUploadDownloadAndBatch() async throws {
        let stub = StubGrpc(
            response: Data(hex: uploadHex),
            serverMessages: [Data([0x2A, 0x02, 0x68, 0x69])]
        )
        let client = PixeldiveGrpcClient(stream: stub, token: "secret", chunkSize: 1)
        let uploaded = try await client.uploadImage(
            sessionID: sessionID,
            filename: "f.png",
            payload: Data("hi".utf8),
            metadata: "{}"
        )
        XCTAssertEqual(uploaded.filename, "frame.png")
        XCTAssertEqual(stub.clientPath, GrpcPath.uploadImage)
        XCTAssertEqual(stub.token, "secret")
        XCTAssertEqual(stub.clientMessages.count, 2)
        let downloaded = try await client.downloadImage(sessionID: sessionID, imageID: imageID)
        XCTAssertEqual(downloaded, Data("hi".utf8))
        XCTAssertEqual(stub.serverPath, GrpcPath.download)
        stub.response = Data(hex: uploadHex)
        let batch = try await client.uploadImagesBatch(
            sessionID: sessionID,
            items: [UploadPart(filename: "a.png", payload: Data("hi".utf8))]
        )
        XCTAssertEqual(batch.count, 1)
        XCTAssertEqual(stub.clientPath, GrpcPath.uploadBatch)
        do {
            _ = try await client.uploadImage(sessionID: "bad", filename: "f.png", payload: Data())
            XCTFail("expected invalid id")
        } catch PixeldiveError.invalidResourceID {
            // expected
        }
    }

    func testEmptyDownloadAndSecondBatchIndex() async throws {
        let stub = StubGrpc(response: Data(hex: uploadHex), serverMessages: [])
        let client = PixeldiveGrpcClient(stream: stub, chunkSize: 8)
        let empty = try await client.downloadImage(sessionID: sessionID, imageID: imageID)
        XCTAssertEqual(empty.count, 0)
        _ = try await client.uploadImagesBatch(
            sessionID: sessionID,
            items: [
                UploadPart(filename: "a.png", payload: Data("hi".utf8)),
                UploadPart(filename: "b.png", payload: Data("ab".utf8)),
            ]
        )
        XCTAssertGreaterThanOrEqual(stub.clientMessages.count, 2)
        _ = try await client.uploadImage(sessionID: sessionID, filename: "f.png", payload: Data())
    }

    func testStatusMapping() {
        let error = GrpcStatusError(code: 16, message: "denied")
        XCTAssertEqual(error, GrpcStatusError(code: 16, message: "denied"))
        let mapped = PixeldiveError.fromGrpc(error)
        XCTAssertEqual(mapped, .transport("grpc-status 16: denied"))
    }

    func testNioCloseAndFailedCall() async {
        #if canImport(GRPC)
        let stream = NioGrpcStreaming(host: "127.0.0.1", port: 1)
        let client = PixeldiveGrpcClient(stream: stream)
        do {
            _ = try await client.uploadImage(
                sessionID: sessionID,
                filename: "f.png",
                payload: Data("hi".utf8)
            )
            XCTFail("expected transport failure")
        } catch {
            XCTAssertTrue(error is PixeldiveError || error is GrpcStatusError)
        }
        do {
            _ = try await client.downloadImage(sessionID: sessionID, imageID: imageID)
            XCTFail("expected transport failure")
        } catch {
            XCTAssertTrue(error is PixeldiveError || error is GrpcStatusError)
        }
        stream.close()
        stream.close()
        _ = PixeldiveGrpcClient.insecure(host: "127.0.0.1", port: 1, token: "tok")
        #endif
    }
}

private extension Data {
    init(hex: String) {
        var data = Data()
        var index = hex.startIndex
        while index < hex.endIndex {
            let next = hex.index(index, offsetBy: 2)
            data.append(UInt8(hex[index..<next], radix: 16)!)
            index = next
        }
        self = data
    }
}
