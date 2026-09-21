import Foundation

enum GrpcPath {
    static let uploadImage = "/pixeldive.session.v1.SessionService/UploadImage"
    static let uploadBatch = "/pixeldive.session.v1.SessionService/UploadImagesBatch"
    static let download = "/pixeldive.session.v1.SessionService/DownloadImage"
}

struct BatchPiece {
    var sessionID: String
    var index: Int
    var filename: String
    var contentType: String
    var data: Data
    var first: Bool
    var end: Bool
}

enum ImageProto {
    static func imageChunk(
        sessionID: String = "",
        filename: String = "",
        contentType: String = "",
        data: Data,
        metadata: String = ""
    ) -> Data {
        var message = Data()
        if !sessionID.isEmpty {
            message.append(ProtoWire.stringField(1, sessionID))
        }
        if !filename.isEmpty {
            message.append(ProtoWire.stringField(3, filename))
        }
        if !contentType.isEmpty {
            message.append(ProtoWire.stringField(4, contentType))
        }
        message.append(ProtoWire.bytesField(5, data))
        if !metadata.isEmpty {
            message.append(ProtoWire.stringField(6, metadata))
        }
        return message
    }

    static func batchChunk(_ piece: BatchPiece) -> Data {
        var message = Data()
        if piece.first, !piece.sessionID.isEmpty {
            message.append(ProtoWire.stringField(1, piece.sessionID))
        }
        if piece.index != 0 {
            message.append(ProtoWire.varintField(2, UInt64(piece.index)))
        }
        if piece.first, !piece.filename.isEmpty {
            message.append(ProtoWire.stringField(3, piece.filename))
        }
        if piece.first, !piece.contentType.isEmpty {
            message.append(ProtoWire.stringField(4, piece.contentType))
        }
        message.append(ProtoWire.bytesField(5, piece.data))
        if piece.end {
            message.append(ProtoWire.boolField(6, true))
        }
        return message
    }

    static func downloadRequest(sessionID: String, imageID: String) -> Data {
        var message = Data()
        message.append(ProtoWire.stringField(1, sessionID))
        message.append(ProtoWire.stringField(2, imageID))
        return message
    }

    static func payloadChunks(_ payload: Data, size: Int) -> [Data] {
        let window = max(size, 1)
        if payload.isEmpty {
            return [Data()]
        }
        var pieces: [Data] = []
        var offset = 0
        while offset < payload.count {
            let end = min(offset + window, payload.count)
            pieces.append(payload.subdata(in: offset..<end))
            offset = end
        }
        return pieces
    }

    static func decodeUpload(_ body: Data) throws -> SessionImage {
        var reader = ProtoReader(bytes: body)
        while let next = try reader.next() {
            if next.number == 1, next.wire == 2 {
                return try decodeSessionImage(next.value)
            }
        }
        throw PixeldiveError.decoding("gRPC upload response missing image")
    }

    static func decodeBatch(_ body: Data) throws -> [SessionImage] {
        var reader = ProtoReader(bytes: body)
        var images: [SessionImage] = []
        while let next = try reader.next() {
            if next.number == 1, next.wire == 2 {
                images.append(try decodeSessionImage(next.value))
            }
        }
        return images
    }

    static func decodeChunkData(_ body: Data) throws -> Data {
        var reader = ProtoReader(bytes: body)
        var payload = Data()
        while let next = try reader.next() {
            if next.number == 5, next.wire == 2 {
                payload = next.value
            }
        }
        return payload
    }

    static func decodeSessionImage(_ body: Data) throws -> SessionImage {
        var reader = ProtoReader(bytes: body)
        var id = ""
        var sessionID = ""
        var filename = ""
        var contentType = ""
        var sizeBytes: Int64 = 0
        var uploaded = Date(timeIntervalSince1970: 0)
        while let next = try reader.next() {
            switch (next.number, next.wire) {
            case (1, 2):
                id = string(next.value)
            case (2, 2):
                sessionID = string(next.value)
            case (3, 2):
                filename = string(next.value)
            case (4, 2):
                contentType = string(next.value)
            case (5, 0):
                sizeBytes = Int64(try decodeVarint(next.value))
            case (7, 2):
                uploaded = try decodeTimestamp(next.value)
            default:
                continue
            }
        }
        return SessionImage(
            id: try parseUUID(id),
            sessionId: try parseUUID(sessionID),
            filename: filename,
            contentType: contentType,
            sizeBytes: Int(sizeBytes),
            uploadedAt: uploaded,
            metadata: [:]
        )
    }
}

private func string(_ data: Data) -> String {
    String(data: data, encoding: .utf8) ?? ""
}

private func parseUUID(_ raw: String) throws -> UUID {
    let parsed = try ResourceID.parse(raw)
    guard let uuid = UUID(uuidString: parsed) else {
        throw PixeldiveError.invalidResourceID(raw)
    }
    return uuid
}

private func decodeTimestamp(_ body: Data) throws -> Date {
    var reader = ProtoReader(bytes: body)
    var seconds: Int64 = 0
    while let next = try reader.next() {
        if next.number == 1, next.wire == 0 {
            seconds = Int64(try decodeVarint(next.value))
        }
    }
    return Date(timeIntervalSince1970: TimeInterval(seconds))
}
