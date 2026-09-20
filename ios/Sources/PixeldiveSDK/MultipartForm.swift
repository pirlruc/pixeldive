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
        try appendFileHeader(
            handle,
            boundary: boundary,
            field: fileField,
            filename: filename,
            contentType: contentType
        )
        try copyFile(source, into: handle)
        handle.write(Data("\r\n".utf8))
        try appendFields(handle, boundary: boundary, fields: fields)
        handle.write(Data("--\(boundary)--\r\n".utf8))
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
        appendFile(&body, boundary: boundary, field: field, part: part)
    }
    for (name, value) in fields.sorted(by: { $0.key < $1.key }) {
        appendField(&body, boundary: boundary, name: name, value: value)
    }
    appendCloser(&body, boundary: boundary)
    return MultipartForm(boundary: boundary, body: body)
}

private func newBoundary() -> String {
    "pixeldive-\(UUID().uuidString.lowercased())"
}

private func appendFile(
    _ body: inout Data,
    boundary: String,
    field: String,
    part: UploadPart
) {
    let safeField = MultipartSanitizer.token(field, fallback: "file")
    let safeName = MultipartSanitizer.filename(part.filename)
    let safeType = MultipartSanitizer.mediaType(part.contentType)
    appendAscii(&body, "--\(boundary)\r\n")
    appendAscii(
        &body,
        "Content-Disposition: form-data; name=\"\(safeField)\"; filename=\"\(safeName)\"\r\n"
    )
    appendAscii(&body, "Content-Type: \(safeType)\r\n\r\n")
    body.append(part.payload)
    appendAscii(&body, "\r\n")
}

private func appendField(_ body: inout Data, boundary: String, name: String, value: String) {
    let safeName = MultipartSanitizer.token(name, fallback: "field")
    appendAscii(&body, "--\(boundary)\r\n")
    appendAscii(&body, "Content-Disposition: form-data; name=\"\(safeName)\"\r\n\r\n")
    appendAscii(&body, value)
    appendAscii(&body, "\r\n")
}

private func appendCloser(_ body: inout Data, boundary: String) {
    appendAscii(&body, "--\(boundary)--\r\n")
}

private func appendAscii(_ body: inout Data, _ text: String) {
    body.append(Data(text.utf8))
}

private func appendFileHeader(
    _ handle: FileHandle,
    boundary: String,
    field: String,
    filename: String,
    contentType: String
) throws {
    let safeField = MultipartSanitizer.token(field, fallback: "file")
    let safeName = MultipartSanitizer.filename(filename)
    let safeType = MultipartSanitizer.mediaType(contentType)
    handle.write(Data("--\(boundary)\r\n".utf8))
    handle.write(
        Data(
            "Content-Disposition: form-data; name=\"\(safeField)\"; filename=\"\(safeName)\"\r\n".utf8
        )
    )
    handle.write(Data("Content-Type: \(safeType)\r\n\r\n".utf8))
}

private func appendFields(_ handle: FileHandle, boundary: String, fields: [String: String]) throws {
    for (name, value) in fields.sorted(by: { $0.key < $1.key }) {
        let safeName = MultipartSanitizer.token(name, fallback: "field")
        handle.write(Data("--\(boundary)\r\n".utf8))
        handle.write(Data("Content-Disposition: form-data; name=\"\(safeName)\"\r\n\r\n".utf8))
        handle.write(Data(value.utf8))
        handle.write(Data("\r\n".utf8))
    }
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
