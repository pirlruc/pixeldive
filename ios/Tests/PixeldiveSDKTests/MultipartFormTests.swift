import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import PixeldiveSDK
import XCTest

final class MultipartFormTests: XCTestCase {
    func testMetadataFieldsAndDiskMultipart() throws {
        XCTAssertEqual(metadataFields(nil), [:])
        XCTAssertEqual(metadataFields("{}"), ["metadata": "{}"])
        let source = FileManager.default.temporaryDirectory.appendingPathComponent("src.png")
        let dest = FileManager.default.temporaryDirectory.appendingPathComponent("out.mime")
        try TestPNG.bytes.write(to: source)
        defer {
            try? FileManager.default.removeItem(at: source)
            try? FileManager.default.removeItem(at: dest)
        }
        let form = try MultipartForm.write(
            to: dest,
            filename: "src.png",
            source: source,
            contentType: "image/png",
            fields: ["metadata": "{}"]
        )
        XCTAssertEqual(form.body.count, 0)
        XCTAssertNotNil(form.fileURL)
        let written = try Data(contentsOf: dest)
        XCTAssertTrue(written.contains(TestPNG.bytes))
        XCTAssertTrue(written.contains(Data("name=\"metadata\"".utf8)))
    }
}
