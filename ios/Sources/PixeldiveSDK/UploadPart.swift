import Foundation

/// One file in a multipart batch upload.
public struct UploadPart: Sendable {
    public var filename: String
    public var payload: Data
    public var contentType: String

    /// Bind filename, bytes, and declared media type.
    public init(filename: String, payload: Data, contentType: String = "image/png") {
        self.filename = filename
        self.payload = payload
        self.contentType = contentType
    }
}
