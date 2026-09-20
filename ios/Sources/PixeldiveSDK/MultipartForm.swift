import Foundation

struct MultipartForm: Sendable {
    let boundary: String
    let body: Data
    let fileURL: URL?

    var contentType: String { "multipart/form-data; boundary=\(boundary)" }

    init(boundary: String, body: Data, fileURL: URL? = nil) {
        self.boundary = boundary
        self.body = body
        self.fileURL = fileURL
    }

    static func make(
        fileField: String,
        filename: String,
        payload: Data,
        contentType: String,
        fields: [String: String]
    ) -> MultipartForm {
        let part = UploadPart(filename: filename, payload: payload, contentType: contentType)
        return assemble(files: [(fileField, part)], fields: fields)
    }

    static func makeBatch(
        items: [UploadPart],
        fields: [String: String]
    ) -> MultipartForm {
        assemble(files: items.map { ("files", $0) }, fields: fields)
    }

    static func write(
        to dest: URL,
        fileField: String,
        filename: String,
        source: URL,
        contentType: String,
        fields: [String: String]
    ) throws -> MultipartForm {
        let boundary = newBoundary()
        FileManager.default.createFile(atPath: dest.path, contents: nil)
        let handle = try FileHandle(forWritingTo: dest)
        defer { try? handle.close() }
        handle.write(filePreamble(boundary, field: fileField, filename: filename, contentType: contentType))
        try copyFile(source, into: handle)
        handle.write(Data("\r\n".utf8))
        for (name, value) in fields.sorted(by: { $0.key < $1.key }) {
            handle.write(fieldChunk(boundary, name: name, value: value))
        }
        handle.write(closer(boundary))
        return MultipartForm(boundary: boundary, body: Data(), fileURL: dest)
    }
}

private func assemble(
    files: [(String, UploadPart)],
    fields: [String: String]
) -> MultipartForm {
    let boundary = newBoundary()
    var body = Data()
    let extra = files.reduce(0) { $0 + $1.1.payload.count } + 512
    body.reserveCapacity(extra)
    for (field, part) in files {
        body.append(
            filePreamble(boundary, field: field, filename: part.filename, contentType: part.contentType)
        )
        body.append(part.payload)
        appendAscii(&body, "\r\n")
    }
    for (name, value) in fields.sorted(by: { $0.key < $1.key }) {
        body.append(fieldChunk(boundary, name: name, value: value))
    }
    body.append(closer(boundary))
    return MultipartForm(boundary: boundary, body: body)
}

private func newBoundary() -> String {
    "pixeldive-\(UUID().uuidString.lowercased())"
}

private func filePreamble(
    _ boundary: String,
    field: String,
    filename: String,
    contentType: String
) -> Data {
    let safeField = MultipartSanitizer.token(field, fallback: "file")
    let safeName = MultipartSanitizer.filename(filename)
    let safeType = MultipartSanitizer.mediaType(contentType)
    var data = Data()
    appendAscii(&data, "--\(boundary)\r\n")
    appendAscii(
        &data,
        "Content-Disposition: form-data; name=\"\(safeField)\"; filename=\"\(safeName)\"\r\n"
    )
    appendAscii(&data, "Content-Type: \(safeType)\r\n\r\n")
    return data
}

private func fieldChunk(_ boundary: String, name: String, value: String) -> Data {
    let safeName = MultipartSanitizer.token(name, fallback: "field")
    var data = Data()
    appendAscii(&data, "--\(boundary)\r\n")
    appendAscii(&data, "Content-Disposition: form-data; name=\"\(safeName)\"\r\n\r\n")
    appendAscii(&data, value)
    appendAscii(&data, "\r\n")
    return data
}

private func closer(_ boundary: String) -> Data {
    Data("--\(boundary)--\r\n".utf8)
}

private func appendAscii(_ body: inout Data, _ text: String) {
    body.append(Data(text.utf8))
}

private func copyFile(_ source: URL, into handle: FileHandle) throws {
    let reader = try FileHandle(forReadingFrom: source)
    defer { try? reader.close() }
    while true {
        let chunk = reader.readData(ofLength: 64 * 1024)
        if chunk.isEmpty {
            return
        }
        handle.write(chunk)
    }
}

enum MultipartSanitizer {
    static func filename(_ raw: String) -> String {
        let base = raw.split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? raw
        var cleaned = ""
        for scalar in base.unicodeScalars {
            if scalar == "\n" || scalar == "\r" || scalar == "\"" || scalar == "\\" || scalar == ";"
                || scalar == ":" || scalar == "\0" {
                cleaned.append("_")
            } else {
                cleaned.append(Character(scalar))
            }
        }
        return cleaned.isEmpty ? "upload.bin" : cleaned
    }

    static func token(_ raw: String, fallback: String) -> String {
        let cleaned = raw.filter { $0.isLetter || $0.isNumber || $0 == "_" || $0 == "-" }
        return cleaned.isEmpty ? fallback : cleaned
    }

    static func mediaType(_ raw: String) -> String {
        var first = ""
        for scalar in raw.unicodeScalars {
            if scalar == "\n" || scalar == "\r" || scalar == ";" {
                break
            }
            first.append(Character(scalar))
        }
        let cleaned = first.filter { $0.isLetter || $0.isNumber || $0 == "/" || $0 == "+" || $0 == "-" || $0 == "." }
        return cleaned.contains("/") ? cleaned : "application/octet-stream"
    }
}
