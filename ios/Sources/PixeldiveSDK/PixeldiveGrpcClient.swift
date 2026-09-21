import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Client-streaming image uploads and server-streaming downloads (mirrors Python `GrpcClient`).
public struct PixeldiveGrpcClient: Sendable {
    let stream: any GrpcStreaming
    let token: String?
    let chunkSize: Int

    /// Bind a streaming transport, optional bearer token, and chunk window.
    public init(
        stream: any GrpcStreaming,
        token: String? = nil,
        chunkSize: Int = 256 * 1024
    ) {
        self.stream = stream
        self.token = token
        self.chunkSize = max(chunkSize, 1)
    }

    /// Close the streaming transport (NIO channel / event-loop group).
    public func close() {
        stream.close()
    }

    /// Client-stream `UploadImage` from an in-memory frame without a second full copy
    /// of the JPEG/PNG into a multipart body.
    public func uploadImage(
        sessionID: String,
        filename: String,
        payload: Data,
        contentType: String = "image/png",
        metadata: String? = nil
    ) async throws -> SessionImage {
        let parsed = try ResourceID.parse(sessionID)
        let messages = singleMessages(
            sessionID: parsed,
            filename: filename,
            payload: payload,
            contentType: contentType,
            metadata: metadata
        )
        let body = try await stream.clientStreaming(
            path: GrpcPath.uploadImage,
            messages: messages,
            token: token
        )
        return try ImageProto.decodeUpload(body)
    }

    /// Client-stream `UploadImagesBatch`.
    public func uploadImagesBatch(
        sessionID: String,
        items: [UploadPart]
    ) async throws -> [SessionImage] {
        let parsed = try ResourceID.parse(sessionID)
        var messages: [Data] = []
        for (index, item) in items.enumerated() {
            messages.append(contentsOf: batchMessages(sessionID: parsed, index: index, item: item))
        }
        let body = try await stream.clientStreaming(
            path: GrpcPath.uploadBatch,
            messages: messages,
            token: token
        )
        return try ImageProto.decodeBatch(body)
    }

    /// Server-stream `DownloadImage`.
    public func downloadImage(sessionID: String, imageID: String) async throws -> Data {
        let parsedSession = try ResourceID.parse(sessionID)
        let parsedImage = try ResourceID.parse(imageID)
        let request = ImageProto.downloadRequest(sessionID: parsedSession, imageID: parsedImage)
        let messages = try await stream.serverStreaming(
            path: GrpcPath.download,
            request: request,
            token: token
        )
        var payload = Data()
        for message in messages {
            payload.append(try ImageProto.decodeChunkData(message))
        }
        return payload
    }

    private func singleMessages(
        sessionID: String,
        filename: String,
        payload: Data,
        contentType: String,
        metadata: String?
    ) -> [Data] {
        let pieces = ImageProto.payloadChunks(payload, size: chunkSize)
        return pieces.enumerated().map { index, piece in
            ImageProto.imageChunk(
                sessionID: index == 0 ? sessionID : "",
                filename: index == 0 ? filename : "",
                contentType: index == 0 ? contentType : "",
                data: piece,
                metadata: index == 0 ? (metadata ?? "") : ""
            )
        }
    }

    private func batchMessages(sessionID: String, index: Int, item: UploadPart) -> [Data] {
        let pieces = ImageProto.payloadChunks(item.payload, size: chunkSize)
        return pieces.enumerated().map { offset, piece in
            ImageProto.batchChunk(
                BatchPiece(
                    sessionID: sessionID,
                    index: index,
                    filename: item.filename,
                    contentType: item.contentType,
                    data: piece,
                    first: offset == 0,
                    end: offset + 1 == pieces.count
                )
            )
        }
    }
}
