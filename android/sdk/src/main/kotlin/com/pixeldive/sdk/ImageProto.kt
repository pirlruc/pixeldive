package com.pixeldive.sdk

import java.time.Instant
import java.util.UUID

internal object GrpcPath {
    const val UPLOAD_IMAGE = "/pixeldive.session.v1.SessionService/UploadImage"
    const val UPLOAD_BATCH = "/pixeldive.session.v1.SessionService/UploadImagesBatch"
    const val DOWNLOAD = "/pixeldive.session.v1.SessionService/DownloadImage"
}

internal data class BatchPiece(
    val sessionId: String,
    val index: Int,
    val filename: String,
    val contentType: String,
    val data: ByteArray,
    val first: Boolean,
    val end: Boolean,
)

internal object ImageProto {
    fun imageChunk(
        sessionId: String = "",
        filename: String = "",
        contentType: String = "",
        data: ByteArray,
        metadata: String = "",
    ): ByteArray {
        val parts = ArrayList<ByteArray>()
        if (sessionId.isNotEmpty()) parts.add(ProtoWire.stringField(1, sessionId))
        if (filename.isNotEmpty()) parts.add(ProtoWire.stringField(3, filename))
        if (contentType.isNotEmpty()) parts.add(ProtoWire.stringField(4, contentType))
        parts.add(ProtoWire.bytesField(5, data))
        if (metadata.isNotEmpty()) parts.add(ProtoWire.stringField(6, metadata))
        return concat(parts)
    }

    fun batchChunk(piece: BatchPiece): ByteArray {
        val parts = ArrayList<ByteArray>()
        if (piece.first && piece.sessionId.isNotEmpty()) {
            parts.add(ProtoWire.stringField(1, piece.sessionId))
        }
        if (piece.index != 0) {
            parts.add(ProtoWire.varintField(2, piece.index.toLong()))
        }
        if (piece.first && piece.filename.isNotEmpty()) {
            parts.add(ProtoWire.stringField(3, piece.filename))
        }
        if (piece.first && piece.contentType.isNotEmpty()) {
            parts.add(ProtoWire.stringField(4, piece.contentType))
        }
        parts.add(ProtoWire.bytesField(5, piece.data))
        if (piece.end) {
            parts.add(ProtoWire.boolField(6, true))
        }
        return concat(parts)
    }

    fun downloadRequest(
        sessionId: String,
        imageId: String,
    ): ByteArray = ProtoWire.stringField(1, sessionId) + ProtoWire.stringField(2, imageId)

    fun payloadChunks(
        payload: ByteArray,
        size: Int,
    ): List<ByteArray> {
        val window = size.coerceAtLeast(1)
        if (payload.isEmpty()) {
            return listOf(ByteArray(0))
        }
        val pieces = ArrayList<ByteArray>()
        var offset = 0
        while (offset < payload.size) {
            val end = (offset + window).coerceAtMost(payload.size)
            pieces.add(payload.copyOfRange(offset, end))
            offset = end
        }
        return pieces
    }

    fun decodeUpload(body: ByteArray): SessionImage =
        fieldOneImages(body).firstOrNull()
            ?: throw PixeldiveException.Decoding("gRPC upload response missing image")

    fun decodeBatch(body: ByteArray): List<SessionImage> = fieldOneImages(body)

    private fun fieldOneImages(body: ByteArray): List<SessionImage> {
        val reader = ProtoReader(body)
        val images = ArrayList<SessionImage>()
        while (true) {
            val next = reader.next() ?: break
            if (next.first == 1 && next.second == 2) {
                images.add(decodeSessionImage(next.third))
            }
        }
        return images
    }

    fun decodeChunkData(body: ByteArray): ByteArray {
        val reader = ProtoReader(body)
        var payload = ByteArray(0)
        while (true) {
            val next = reader.next() ?: break
            if (next.first == 5 && next.second == 2) {
                payload = next.third
            }
        }
        return payload
    }

    fun decodeSessionImage(body: ByteArray): SessionImage {
        val fields = ImageFields()
        val reader = ProtoReader(body)
        while (true) {
            val next = reader.next() ?: break
            fields.accept(next)
        }
        return fields.toImage()
    }
}

private class ImageFields {
    var id = ""
    var sessionId = ""
    var filename = ""
    var contentType = ""
    var sizeBytes = 0L
    var uploaded = Instant.EPOCH

    fun accept(next: Triple<Int, Int, ByteArray>) {
        val (field, wire, value) = next
        if (wire == 2) {
            acceptBytes(field, value)
            return
        }
        if (field == 5 && wire == 0) {
            sizeBytes = decodeVarint(value)
        }
    }

    private fun acceptBytes(
        field: Int,
        value: ByteArray,
    ) {
        when (field) {
            1 -> id = utf8(value)
            2 -> sessionId = utf8(value)
            3 -> filename = utf8(value)
            4 -> contentType = utf8(value)
            7 -> uploaded = decodeTimestamp(value)
        }
    }

    fun toImage(): SessionImage =
        SessionImage(
            id = UUID.fromString(ResourceId.parse(id)),
            sessionId = UUID.fromString(ResourceId.parse(sessionId)),
            filename = filename,
            contentType = contentType,
            sizeBytes = sizeBytes.toInt(),
            uploadedAt = uploaded,
            metadata = emptyMap(),
        )
}

private fun decodeTimestamp(body: ByteArray): Instant {
    val reader = ProtoReader(body)
    var seconds = 0L
    while (true) {
        val next = reader.next() ?: break
        if (next.first == 1 && next.second == 0) {
            seconds = decodeVarint(next.third)
        }
    }
    return Instant.ofEpochSecond(seconds)
}

private fun utf8(data: ByteArray): String = data.toString(Charsets.UTF_8)

private fun concat(parts: List<ByteArray>): ByteArray {
    val out = ByteArray(parts.sumOf { it.size })
    var offset = 0
    parts.forEach { part ->
        System.arraycopy(part, 0, out, offset, part.size)
        offset += part.size
    }
    return out
}
