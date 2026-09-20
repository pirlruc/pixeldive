import Foundation

struct MultipartForm: Sendable {
    let boundary: String
    let body: Data
    var contentType: String { "multipart/form-data; boundary=\(boundary)" }

    static func make(
        fileField: String,
        filename: String,
        payload: Data,
        contentType: String,
        fields: [String: String]
    ) -> MultipartForm {
        let boundary = "pixeldive-\(UUID().uuidString.lowercased())"
        var body = Data()
        appendFile(&body, boundary: boundary, field: fileField, filename: filename, payload: payload, type: contentType)
        for (name, value) in fields.sorted(by: { $0.key < $1.key }) {
            appendField(&body, boundary: boundary, name: name, value: value)
        }
        appendCloser(&body, boundary: boundary)
        return MultipartForm(boundary: boundary, body: body)
    }

    static func makeBatch(
        items: [(filename: String, payload: Data, contentType: String)],
        fields: [String: String]
    ) -> MultipartForm {
        let boundary = "pixeldive-\(UUID().uuidString.lowercased())"
        var body = Data()
        for item in items {
            appendFile(
                &body,
                boundary: boundary,
                field: "files",
                filename: item.filename,
                payload: item.payload,
                type: item.contentType
            )
        }
        for (name, value) in fields.sorted(by: { $0.key < $1.key }) {
            appendField(&body, boundary: boundary, name: name, value: value)
        }
        appendCloser(&body, boundary: boundary)
        return MultipartForm(boundary: boundary, body: body)
    }
}

private func appendFile(
    _ body: inout Data,
    boundary: String,
    field: String,
    filename: String,
    payload: Data,
    type: String
) {
    let safeField = MultipartSanitizer.token(field, fallback: "file")
    let safeName = MultipartSanitizer.filename(filename)
    let safeType = MultipartSanitizer.mediaType(type)
    appendAscii(&body, "--\(boundary)\r\n")
    appendAscii(
        &body,
        "Content-Disposition: form-data; name=\"\(safeField)\"; filename=\"\(safeName)\"\r\n"
    )
    appendAscii(&body, "Content-Type: \(safeType)\r\n\r\n")
    body.append(payload)
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

enum MultipartSanitizer {
    static func filename(_ raw: String) -> String {
        let base = raw.split(whereSeparator: { $0 == "/" || $0 == "\\" }).last.map(String.init) ?? raw
        var cleaned = ""
        for scalar in base.unicodeScalars {
            if scalar == "\n" || scalar == "\r" || scalar == "\"" || scalar == "\\" || scalar == ";"
                || scalar == ":"
            {
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
            if scalar == "\n" || scalar == "\r" {
                break
            }
            first.append(Character(scalar))
        }
        let cleaned = first.filter { $0.isLetter || $0.isNumber || $0 == "/" || $0 == "+" || $0 == "-" || $0 == "." }
        return cleaned.contains("/") ? cleaned : "application/octet-stream"
    }
}
