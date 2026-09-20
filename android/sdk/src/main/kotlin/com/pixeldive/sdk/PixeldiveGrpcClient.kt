package com.pixeldive.sdk

/** Client-streaming image uploads and server-streaming downloads (mirrors Python `GrpcClient`). */
class PixeldiveGrpcClient(
    private val stream: GrpcStreaming,
    private val token: String? = null,
    chunkSize: Int = 256 * 1024,
) {
    private val chunkSize = chunkSize.coerceAtLeast(1)

    /** Client-stream `UploadImage` from an in-memory camera frame. */
    suspend fun uploadImage(
        sessionId: String,
        filename: String,
        payload: ByteArray,
        contentType: String = "image/png",
        metadata: String? = null,
    ): SessionImage {
        val parsed = ResourceId.parse(sessionId)
        val body =
            stream.clientStreaming(
                GrpcPath.UPLOAD_IMAGE,
                singleMessages(parsed, filename, payload, contentType, metadata),
                token,
            )
        return ImageProto.decodeUpload(body)
    }

    /** Client-stream `UploadImagesBatch`. */
    suspend fun uploadImagesBatch(
        sessionId: String,
        items: List<Triple<String, ByteArray, String>>,
    ): List<SessionImage> {
        val parsed = ResourceId.parse(sessionId)
        val messages = ArrayList<ByteArray>()
        items.forEachIndexed { index, item ->
            messages.addAll(batchMessages(parsed, index, item))
        }
        val body = stream.clientStreaming(GrpcPath.UPLOAD_BATCH, messages, token)
        return ImageProto.decodeBatch(body)
    }

    /** Server-stream `DownloadImage`. */
    suspend fun downloadImage(
        sessionId: String,
        imageId: String,
    ): ByteArray {
        val request =
            ImageProto.downloadRequest(ResourceId.parse(sessionId), ResourceId.parse(imageId))
        val messages = stream.serverStreaming(GrpcPath.DOWNLOAD, request, token)
        val chunks = messages.map { ImageProto.decodeChunkData(it) }
        val payload = ByteArray(chunks.sumOf { it.size })
        var offset = 0
        chunks.forEach { chunk ->
            System.arraycopy(chunk, 0, payload, offset, chunk.size)
            offset += chunk.size
        }
        return payload
    }

    private fun singleMessages(
        sessionId: String,
        filename: String,
        payload: ByteArray,
        contentType: String,
        metadata: String?,
    ): List<ByteArray> {
        val pieces = ImageProto.payloadChunks(payload, chunkSize)
        return pieces.mapIndexed { index, piece ->
            ImageProto.imageChunk(
                sessionId = if (index == 0) sessionId else "",
                filename = if (index == 0) filename else "",
                contentType = if (index == 0) contentType else "",
                data = piece,
                metadata = if (index == 0) metadata.orEmpty() else "",
            )
        }
    }

    private fun batchMessages(
        sessionId: String,
        index: Int,
        item: Triple<String, ByteArray, String>,
    ): List<ByteArray> {
        val pieces = ImageProto.payloadChunks(item.second, chunkSize)
        return pieces.mapIndexed { offset, piece ->
            ImageProto.batchChunk(
                BatchPiece(
                    sessionId = sessionId,
                    index = index,
                    filename = item.first,
                    contentType = item.third,
                    data = piece,
                    first = offset == 0,
                    end = offset + 1 == pieces.size,
                ),
            )
        }
    }

    companion object {
        /** Insecure h2c client for local/dev grpc.aio (`127.0.0.1:50051`). */
        fun insecure(
            host: String,
            port: Int = 50051,
            token: String? = null,
        ): PixeldiveGrpcClient = PixeldiveGrpcClient(OkHttpGrpcStreaming(host, port), token)
    }
}
