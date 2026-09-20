import Foundation
@testable import PixeldiveSDK
import XCTest

final class ResourceIDTests: XCTestCase {
    func testParseAcceptsUUID() throws {
        let value = try ResourceID.parse("123e4567-e89b-12d3-a456-426614174000")
        XCTAssertEqual(value, "123e4567-e89b-12d3-a456-426614174000")
    }

    func testParseRejectsTraversal() {
        XCTAssertThrowsError(try ResourceID.parse("../secret")) { error in
            guard case PixeldiveError.invalidResourceID = error else {
                return XCTFail("expected invalidResourceID")
            }
        }
    }

    func testParseRejectsPlainString() {
        XCTAssertThrowsError(try ResourceID.parse("not-a-uuid"))
    }
}

final class PayloadTests: XCTestCase {
    func testSampleMatchesBundledFixture() throws {
        let sample = DeviceSnapshot.sampleiPhone()
        let bundled = try DeviceSnapshot.bundledSample()
        XCTAssertEqual(sample, bundled)
        XCTAssertEqual(sample.cameraCapabilities.cameraCount, sample.cameraCapabilities.cameras.count)
        XCTAssertEqual(sample.metadata["platform"], .string("ios"))
        XCTAssertEqual(sample.phoneInfo.manufacturer, "Apple")
        XCTAssertEqual(sample.phoneInfo.sdkInt, 18)
    }

    func testSampleEncodesAndroidWireKeys() throws {
        let data = try JSONCodec.makeEncoder().encode(DeviceSnapshot.sampleiPhone())
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let phone = try XCTUnwrap(object["phone_info"] as? [String: Any])
        XCTAssertEqual(phone["android_version"] as? String, "18.6")
        XCTAssertEqual(phone["sdk_int"] as? Int, 18)
        XCTAssertNil(object["storage_path"])
        let cameras = try XCTUnwrap(object["camera_capabilities"] as? [String: Any])
        XCTAssertEqual(cameras["camera_count"] as? Int, 2)
    }

    func testCurrentSnapshotIsAndroidShaped() {
        let live = DeviceSnapshot.current(sessionName: "live")
        XCTAssertEqual(live.sessionName, "live")
        XCTAssertEqual(live.cameraCapabilities.cameraCount, live.cameraCapabilities.cameras.count)
        XCTAssertEqual(live.metadata["platform"], .string("ios"))
        XCTAssertFalse(live.phoneInfo.androidVersion.isEmpty)
        #if !os(iOS)
        XCTAssertEqual(live.cameraCapabilities.cameras.count, 0)
        #endif
    }

    func testJSONValueRoundTrip() throws {
        let original: [String: JSONValue] = [
            "flag": .bool(true),
            "n": .int(3),
            "nested": .object(["k": .string("v")]),
        ]
        let data = try JSONCodec.makeEncoder().encode(original)
        let decoded = try JSONCodec.makeDecoder().decode([String: JSONValue].self, from: data)
        XCTAssertEqual(decoded, original)
    }

    func testMajorVersion() {
        XCTAssertEqual(majorVersion("18.6.1"), 18)
        XCTAssertEqual(majorVersion("bad"), 0)
    }

    func testCameraCountMustMatchOnDecode() throws {
        let json = Data(#"{"camera_count":1,"cameras":[]}"#.utf8)
        XCTAssertThrowsError(try JSONCodec.makeDecoder().decode(CameraCapabilities.self, from: json))
    }

    func testJSONValueNullArrayDouble() throws {
        let original: [String: JSONValue] = [
            "empty": .null,
            "nums": .array([.double(1.5), .int(2)]),
        ]
        let data = try JSONCodec.makeEncoder().encode(original)
        let decoded = try JSONCodec.makeDecoder().decode([String: JSONValue].self, from: data)
        XCTAssertEqual(decoded, original)
    }

    func testISO8601Dates() {
        XCTAssertNotNil(JSONCodec.parseISO8601("2026-09-20T12:00:00Z"))
        XCTAssertNotNil(JSONCodec.parseISO8601("2026-09-20T12:00:00.000000Z"))
        XCTAssertNil(JSONCodec.parseISO8601("not-a-date"))
    }

    func testHardwareMachineAndErrors() {
        XCTAssertFalse(hardwareMachine().isEmpty)
        XCTAssertEqual(
            PixeldiveError.invalidResourceID("x").localizedDescription,
            "Invalid resource id: x"
        )
        XCTAssertEqual(
            PixeldiveError.httpStatus(302, body: "go").localizedDescription,
            "HTTP 302: go"
        )
        XCTAssertTrue(PixeldiveError.decoding("bad").localizedDescription.contains("Decoding"))
        XCTAssertTrue(PixeldiveError.transport("down").localizedDescription.contains("Transport"))
    }

    func testResourceIDFromUUID() {
        let value = UUID(uuidString: "123e4567-e89b-12d3-a456-426614174000")!
        XCTAssertEqual(ResourceID.parse(value), "123e4567-e89b-12d3-a456-426614174000")
    }

    func testMultipartSanitizer() {
        XCTAssertEqual(MultipartSanitizer.filename("dir/evil\r\n\".png"), "evil___.png")
        XCTAssertEqual(MultipartSanitizer.filename("a\rb\nc"), "a_b_c")
        XCTAssertEqual(MultipartSanitizer.filename(""), "upload.bin")
        XCTAssertEqual(MultipartSanitizer.token("file;name", fallback: "file"), "filename")
        XCTAssertEqual(MultipartSanitizer.token("@@@", fallback: "file"), "file")
        XCTAssertEqual(MultipartSanitizer.mediaType("image/png\r\nX: 1"), "image/png")
        XCTAssertEqual(MultipartSanitizer.mediaType("image/png; charset=utf-8"), "image/png")
        XCTAssertEqual(MultipartSanitizer.mediaType("nope"), "application/octet-stream")
        XCTAssertEqual(MultipartSanitizer.filename("a\0.png"), "a_.png")
        XCTAssertEqual(MultipartSanitizer.mediaType(""), "application/octet-stream")
    }

    func testDecodeDateRejectsGarbage() {
        struct Dated: Decodable { var createdAt: Date }
        XCTAssertThrowsError(
            try JSONCodec.makeDecoder().decode(Dated.self, from: Data(#"{"created_at":"nope"}"#.utf8))
        )
    }
}
