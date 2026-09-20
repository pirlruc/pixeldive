import Foundation
@testable import PixeldiveSDK
import XCTest

final class ProtoTests: XCTestCase {
    private let sessionID = "123e4567-e89b-12d3-a456-426614174000"
    private let imageID = "123e4567-e89b-12d3-a456-426614174001"

    func testImageChunkMatchesPythonFixture() {
        let encoded = ImageProto.imageChunk(
            sessionID: sessionID,
            filename: "f.png",
            contentType: "image/png",
            data: Data("hi".utf8)
        )
        XCTAssertEqual(encoded.hex, Self.imageChunkHex)
        XCTAssertEqual(ImageProto.imageChunk(data: Data("hi".utf8)).hex, "2a026869")
        let withMeta = ImageProto.imageChunk(
            sessionID: sessionID,
            filename: "f.png",
            contentType: "image/png",
            data: Data("hi".utf8),
            metadata: "{}"
        )
        XCTAssertTrue(withMeta.hex.contains("7b7d"))
    }

    func testBatchChunkOmitsDefaultIndex() {
        let first = ImageProto.batchChunk(
            BatchPiece(
                sessionID: sessionID,
                index: 0,
                filename: "a.png",
                contentType: "image/png",
                data: Data("hi".utf8),
                first: true,
                end: true
            )
        )
        XCTAssertEqual(first.hex, Self.batch0Hex)
        let later = ImageProto.batchChunk(
            BatchPiece(
                sessionID: sessionID,
                index: 1,
                filename: "b.png",
                contentType: "image/png",
                data: Data("ab".utf8),
                first: false,
                end: false
            )
        )
        XCTAssertEqual(later.hex, "10012a026162")
        let second = ImageProto.batchChunk(
            BatchPiece(
                sessionID: sessionID,
                index: 1,
                filename: "b.png",
                contentType: "image/png",
                data: Data("ab".utf8),
                first: true,
                end: true
            )
        )
        XCTAssertTrue(second.hex.contains("1001"))
        XCTAssertEqual(ProtoWire.boolField(6, false).count, 0)
    }

    func testDownloadRequestAndChunks() {
        let request = ImageProto.downloadRequest(sessionID: sessionID, imageID: imageID)
        XCTAssertEqual(request.hex, Self.downloadHex)
        XCTAssertEqual(ImageProto.payloadChunks(Data(), size: 8).count, 1)
        XCTAssertEqual(ImageProto.payloadChunks(Data("hi".utf8), size: 1).count, 2)
        XCTAssertEqual(
            try ImageProto.decodeChunkData(Data([0x2A, 0x01, 0x68])),
            Data("h".utf8)
        )
    }

    func testDecodeUploadAndBatch() throws {
        let body = Data(hex: Self.uploadHex)
        let image = try ImageProto.decodeUpload(body)
        XCTAssertEqual(image.id.uuidString.lowercased(), imageID)
        XCTAssertEqual(image.filename, "frame.png")
        XCTAssertEqual(image.sizeBytes, 67)
        XCTAssertEqual(image.uploadedAt.timeIntervalSince1970, 1_789_905_600, accuracy: 0.001)
        XCTAssertEqual(try ImageProto.decodeBatch(body).count, 1)
        XCTAssertThrowsError(try ImageProto.decodeUpload(Data()))
        XCTAssertEqual(try ImageProto.decodeBatch(Data()).count, 0)
        let ids = try ImageProto.decodeSessionImage(
            ProtoWire.stringField(1, imageID) + ProtoWire.stringField(2, sessionID)
        )
        XCTAssertEqual(ids.uploadedAt.timeIntervalSince1970, 0, accuracy: 0.001)
    }

    func testProtoReaderWireTypesAndErrors() throws {
        var reader64 = ProtoReader(bytes: Data([0x09, 1, 2, 3, 4, 5, 6, 7, 8]))
        let next64 = try XCTUnwrap(reader64.next())
        XCTAssertEqual(next64.0, 1)
        XCTAssertEqual(next64.1, 1)
        XCTAssertEqual(next64.2.count, 8)
        var reader32 = ProtoReader(bytes: Data([0x0D, 1, 2, 3, 4]))
        let next32 = try XCTUnwrap(reader32.next())
        XCTAssertEqual(next32.1, 5)
        var bad = ProtoReader(bytes: Data([0x0B]))
        XCTAssertThrowsError(try bad.next())
        var trunc = ProtoReader(bytes: Data([0x08]))
        XCTAssertThrowsError(try trunc.readVarint())
        var overflow = ProtoReader(bytes: Data(repeating: 0x80, count: 10))
        XCTAssertThrowsError(try overflow.readVarint())
        var short = ProtoReader(bytes: Data([0x0A, 0x04, 0x01]))
        XCTAssertThrowsError(try short.next())
        XCTAssertEqual(try decodeVarint(Data([0x01])), 1)
        var empty = ProtoReader(bytes: Data())
        XCTAssertNil(try empty.next())
        let extra = ProtoWire.stringField(1, imageID)
            + ProtoWire.stringField(2, sessionID)
            + ProtoWire.bytesField(8, Data())
            + Data([0x3A, 0x00])
        XCTAssertEqual(try ImageProto.decodeSessionImage(extra).filename, "")
        XCTAssertEqual(try ImageProto.decodeChunkData(Data([0x08, 0x01])).count, 0)
    }

    private static let imageChunkHex =
        "0a2431323365343536372d653839622d313264332d613435362d343236363134313734303030"
        + "1a05662e706e672209696d6167652f706e672a026869"
    private static let batch0Hex =
        "0a2431323365343536372d653839622d313264332d613435362d343236363134313734303030"
        + "1a05612e706e672209696d6167652f706e672a0268693001"
    private static let downloadHex =
        "0a2431323365343536372d653839622d313264332d613435362d343236363134313734303030"
        + "122431323365343536372d653839622d313264332d613435362d343236363134313734303031"
    private static let uploadHex =
        "0a6c0a2431323365343536372d653839622d313264332d613435362d343236363134313734303031"
        + "122431323365343536372d653839622d313264332d613435362d343236363134313734303030"
        + "1a096672616d652e706e672209696d6167652f706e6728433a0608c095bfd506"
}

private extension Data {
    var hex: String { map { String(format: "%02x", $0) }.joined() }

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
