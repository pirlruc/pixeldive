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
}
