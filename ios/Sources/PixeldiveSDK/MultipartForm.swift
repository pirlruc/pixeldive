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
    appendAscii(&body, "--\(boundary)\r\n")
    appendAscii(
        &body,
        "Content-Disposition: form-data; name=\"\(field)\"; filename=\"\(filename)\"\r\n"
    )
    appendAscii(&body, "Content-Type: \(type)\r\n\r\n")
    body.append(payload)
    appendAscii(&body, "\r\n")
}

private func appendField(_ body: inout Data, boundary: String, name: String, value: String) {
    appendAscii(&body, "--\(boundary)\r\n")
    appendAscii(&body, "Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n")
    appendAscii(&body, value)
    appendAscii(&body, "\r\n")
}

private func appendCloser(_ body: inout Data, boundary: String) {
    appendAscii(&body, "--\(boundary)--\r\n")
}

private func appendAscii(_ body: inout Data, _ text: String) {
    body.append(Data(text.utf8))
}
