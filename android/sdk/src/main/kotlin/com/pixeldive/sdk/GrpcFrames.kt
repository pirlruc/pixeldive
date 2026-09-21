package com.pixeldive.sdk

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody
import okio.BufferedSink

internal object GrpcFrames {
    fun encode(message: ByteArray): ByteArray {
        val out = ByteArray(5 + message.size)
        val size = message.size
        out[1] = (size ushr 24).toByte()
        out[2] = (size ushr 16).toByte()
        out[3] = (size ushr 8).toByte()
        out[4] = size.toByte()
        System.arraycopy(message, 0, out, 5, message.size)
        return out
    }

    fun encodeAll(messages: List<ByteArray>): ByteArray {
        val framed = messages.map { encode(it) }
        val out = ByteArray(framed.sumOf { it.size })
        var offset = 0
        framed.forEach { part ->
            System.arraycopy(part, 0, out, offset, part.size)
            offset += part.size
        }
        return out
    }

    fun messages(bytes: ByteArray): List<ByteArray> {
        val out = ArrayList<ByteArray>()
        var offset = 0
        while (offset < bytes.size) {
            if (bytes.size - offset < 5) {
                throw PixeldiveException.Decoding("truncated gRPC frame header")
            }
            if (bytes[offset].toInt() and 1 != 0) {
                throw PixeldiveException.Decoding("compressed gRPC frames are not supported")
            }
            val length = lengthOf(bytes, offset)
            val start = offset + 5
            val end = start + length
            if (end > bytes.size) {
                throw PixeldiveException.Decoding("truncated gRPC frame")
            }
            out.add(bytes.copyOfRange(start, end))
            offset = end
        }
        return out
    }

    fun body(messages: List<ByteArray>): RequestBody =
        object : RequestBody() {
            override fun contentType() = "application/grpc".toMediaType()

            override fun writeTo(sink: BufferedSink) {
                sink.write(encodeAll(messages))
            }
        }

    private fun lengthOf(
        bytes: ByteArray,
        offset: Int,
    ): Int {
        val length =
            (bytes[offset + 1].toInt() and 0xFF shl 24) or
                (bytes[offset + 2].toInt() and 0xFF shl 16) or
                (bytes[offset + 3].toInt() and 0xFF shl 8) or
                (bytes[offset + 4].toInt() and 0xFF)
        if (length < 0) {
            throw PixeldiveException.Decoding("gRPC frame larger than 2 GiB")
        }
        return length
    }
}
