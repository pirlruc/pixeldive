package com.pixeldive.sdk

import kotlinx.coroutines.runBlocking
import okhttp3.Headers
import okhttp3.Protocol
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.Assertions.assertArrayEquals
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant
import java.util.UUID

class GrpcCodecTest {
    private val sessionId = "123e4567-e89b-12d3-a456-426614174000"
    private val imageId = "123e4567-e89b-12d3-a456-426614174001"

    @Test
    fun imageChunkMatchesPythonFixture() {
        val encoded =
            ImageProto.imageChunk(
                sessionId = sessionId,
                filename = "f.png",
                contentType = "image/png",
                data = "hi".toByteArray(),
            )
        assertEquals(
            "0a2431323365343536372d653839622d313264332d613435362d343236363134313734303030" +
                "1a05662e706e672209696d6167652f706e672a026869",
            encoded.toHex(),
        )
        assertEquals("2a026869", ImageProto.imageChunk(data = "hi".toByteArray()).toHex())
        val withMeta =
            ImageProto.imageChunk(
                sessionId = sessionId,
                filename = "f.png",
                contentType = "image/png",
                data = "hi".toByteArray(),
                metadata = "{}",
            )
        assertTrue(withMeta.toHex().contains("7b7d"))
    }

    @Test
    fun batchChunkOmitsDefaultIndex() {
        val first =
            ImageProto.batchChunk(
                BatchPiece(sessionId, 0, "a.png", "image/png", "hi".toByteArray(), first = true, end = true),
            )
        assertEquals(
            "0a2431323365343536372d653839622d313264332d613435362d343236363134313734303030" +
                "1a05612e706e672209696d6167652f706e672a0268693001",
            first.toHex(),
        )
        val later =
            ImageProto.batchChunk(
                BatchPiece(sessionId, 1, "b.png", "image/png", "ab".toByteArray(), first = false, end = false),
            )
        assertEquals("10012a026162", later.toHex())
        val second =
            ImageProto.batchChunk(
                BatchPiece(sessionId, 1, "b.png", "image/png", "ab".toByteArray(), first = true, end = true),
            )
        assertTrue(second.toHex().startsWith("0a24"))
        assertTrue(second.toHex().contains("1001"))
    }

    @Test
    fun downloadRequestAndChunks() {
        val request = ImageProto.downloadRequest(sessionId, imageId)
        assertEquals(
            "0a2431323365343536372d653839622d313264332d613435362d343236363134313734303030" +
                "122431323365343536372d653839622d313264332d613435362d343236363134313734303031",
            request.toHex(),
        )
        assertEquals(1, ImageProto.payloadChunks(ByteArray(0), 8).size)
        assertEquals(2, ImageProto.payloadChunks("hi".toByteArray(), 1).size)
        assertArrayEquals("h".toByteArray(), ImageProto.decodeChunkData(byteArrayOf(0x2a, 0x01, 0x68)))
    }

    @Test
    fun decodeUploadAndBatch() {
        val body = UPLOAD_RESP.hexToBytes()
        val image = ImageProto.decodeUpload(body)
        assertEquals(UUID.fromString(imageId), image.id)
        assertEquals(UUID.fromString(sessionId), image.sessionId)
        assertEquals("frame.png", image.filename)
        assertEquals(67, image.sizeBytes)
        assertEquals(Instant.parse("2026-09-20T12:00:00Z"), image.uploadedAt)
        val batch = ImageProto.decodeBatch(body)
        assertEquals(1, batch.size)
        assertThrows<PixeldiveException.Decoding> { ImageProto.decodeUpload(ByteArray(0)) }
        assertTrue(ImageProto.decodeBatch(ByteArray(0)).isEmpty())
        val idsOnly =
            ImageProto.decodeSessionImage(
                ProtoWire.stringField(1, imageId) + ProtoWire.stringField(2, sessionId),
            )
        assertEquals(Instant.EPOCH, idsOnly.uploadedAt)
        assertThrows<PixeldiveException.InvalidResourceId> {
            ImageProto.decodeSessionImage(byteArrayOf(0x3a, 0x00))
        }
    }

    @Test
    fun protoReaderWireTypesAndErrors() {
        val fixed64 = byteArrayOf(0x09, 1, 2, 3, 4, 5, 6, 7, 8)
        val reader64 = ProtoReader(fixed64)
        val next64 = reader64.next()!!
        assertEquals(1, next64.first)
        assertEquals(1, next64.second)
        assertEquals(8, next64.third.size)
        val fixed32 = byteArrayOf(0x0D, 1, 2, 3, 4)
        val next32 = ProtoReader(fixed32).next()!!
        assertEquals(1, next32.first)
        assertEquals(5, next32.second)
        assertThrows<PixeldiveException.Decoding> { ProtoReader(byteArrayOf(0x0B)).next() }
        assertThrows<PixeldiveException.Decoding> {
            ProtoReader(byteArrayOf(0x80.toByte())).readVarint()
        }
        assertThrows<PixeldiveException.Decoding> {
            ProtoReader(ByteArray(10) { 0x80.toByte() }).readVarint()
        }
        assertThrows<PixeldiveException.Decoding> { ProtoReader(byteArrayOf(0x0A, 0x04, 0x01)).next() }
        assertEquals(1, decodeVarint(byteArrayOf(0x01)))
        ProtoWire.boolField(6, false)
        ProtoWire.tag(1, 2)
        assertTrue(ProtoWire.varint(128).size > 1)
        ImageProto.batchChunk(
            BatchPiece("", 0, "", "", byteArrayOf(1), first = true, end = false),
        )
        assertEquals(null, ProtoReader(ByteArray(0)).next())
    }

    @Test
    fun grpcFramesRoundTripAndErrors() {
        val payload = "hi".toByteArray()
        val framed = GrpcFrames.encode(payload)
        assertEquals("00000000026869", framed.toHex())
        assertArrayEquals(payload, GrpcFrames.messages(framed).single())
        val two = GrpcFrames.encodeAll(listOf(byteArrayOf(0x68), byteArrayOf(0x69)))
        assertEquals(2, GrpcFrames.messages(two).size)
        assertThrows<PixeldiveException.Decoding> { GrpcFrames.messages(byteArrayOf(0x00, 0x00)) }
        assertThrows<PixeldiveException.Decoding> {
            GrpcFrames.messages(byteArrayOf(0x01, 0, 0, 0, 0))
        }
        assertThrows<PixeldiveException.Decoding> {
            GrpcFrames.messages(byteArrayOf(0x00, 0, 0, 0, 4, 1))
        }
        assertThrows<PixeldiveException.Decoding> {
            GrpcFrames.messages(
                byteArrayOf(0x00, 0xFF.toByte(), 0xFF.toByte(), 0xFF.toByte(), 0xFF.toByte()),
            )
        }
        assertEquals(0, GrpcFrames.messages(ByteArray(0)).size)
        GrpcFrames.body(listOf(payload)).contentType()
    }

    @Test
    fun grpcStatusHeadersAndTrailers() {
        val headers = Headers.headersOf("grpc-status", "0", "grpc-message", "ok")
        assertEquals(0 to "ok", grpcStatus(headers, Headers.headersOf()))
        val trailers = Headers.headersOf("grpc-status", "16", "grpc-message", "denied")
        assertEquals(16 to "denied", grpcStatus(Headers.headersOf(), trailers))
        assertEquals(2 to "", grpcStatus(Headers.headersOf(), Headers.headersOf()))
        val denied = Headers.headersOf("grpc-status", "7", "grpc-message", "denied")
        assertEquals(7 to "denied", grpcStatus(denied, Headers.headersOf()))
        val encoded = Headers.headersOf("grpc-status", "16", "grpc-message", "no%20access")
        assertEquals(16 to "no access", grpcStatus(encoded, Headers.headersOf()))
        assertEquals("ok", percentDecode("ok"))
        assertEquals("a%", percentDecode("a%"))
        assertEquals("a%ZZ", percentDecode("a%ZZ"))
        assertEquals(null, percentByte("ab", 0))
    }

    @Test
    fun grpcClientUploadDownloadAndBatch() {
        runBlocking {
            val stub = RecordingStream(UPLOAD_RESP.hexToBytes(), listOf(byteArrayOf(0x2a, 0x02, 0x68, 0x69)))
            val client = PixeldiveGrpcClient(stub, token = "secret", chunkSize = 1)
            val uploaded = client.uploadImage(sessionId, "f.png", "hi".toByteArray(), metadata = "{}")
            assertEquals("frame.png", uploaded.filename)
            assertEquals(GrpcPath.UPLOAD_IMAGE, stub.clientPath)
            assertEquals("secret", stub.token)
            assertEquals(2, stub.clientMessages.size)
            val downloaded = client.downloadImage(sessionId, imageId)
            assertArrayEquals("hi".toByteArray(), downloaded)
            assertEquals(GrpcPath.DOWNLOAD, stub.serverPath)
            stub.response = UPLOAD_RESP.hexToBytes()
            val batch =
                client.uploadImagesBatch(
                    sessionId,
                    listOf(Triple("a.png", "hi".toByteArray(), "image/png")),
                )
            assertEquals(1, batch.size)
            assertEquals(GrpcPath.UPLOAD_BATCH, stub.clientPath)
            assertThrows<PixeldiveException.InvalidResourceId> {
                runBlocking { client.uploadImage("bad", "f.png", ByteArray(0)) }
            }
            client.close()
        }
    }

    @Test
    fun grpcClientEmptyDownloadAndBatchIndex() {
        runBlocking {
            val stub = RecordingStream(UPLOAD_RESP.hexToBytes(), emptyList())
            val client = PixeldiveGrpcClient(stub, chunkSize = 8)
            assertEquals(0, client.downloadImage(sessionId, imageId).size)
            client.uploadImagesBatch(
                sessionId,
                listOf(
                    Triple("a.png", "hi".toByteArray(), "image/png"),
                    Triple("b.png", "ab".toByteArray(), "image/png"),
                ),
            )
            assertTrue(stub.clientMessages.size >= 2)
            client.uploadImage(sessionId, "f.png", ByteArray(0))
            PixeldiveGrpcClient(stub, chunkSize = 0).uploadImage(sessionId, "f.png", "x".toByteArray())
            client.close()
        }
    }

    @Test
    fun okHttpH2cStreaming() {
        runBlocking {
            val server = MockWebServer()
            server.protocols = listOf(Protocol.H2_PRIOR_KNOWLEDGE)
            server.enqueue(grpcOk(UPLOAD_RESP.hexToBytes()))
            server.enqueue(grpcOk(byteArrayOf(0x2a, 0x02, 0x68, 0x69)))
            server.enqueue(
                MockResponse().setResponseCode(500).setHeader("content-type", "application/grpc"),
            )
            server.enqueue(grpcOk(ByteArray(0), status = 16, grpcMessage = "nope"))
            server.start()
            try {
                val stream = OkHttpGrpcStreaming("127.0.0.1", server.port)
                val uploaded = stream.clientStreaming(GrpcPath.UPLOAD_IMAGE, listOf("hi".toByteArray()), "tok")
                assertEquals("frame.png", ImageProto.decodeUpload(uploaded).filename)
                val first = server.takeRequest()
                assertEquals("Bearer tok", first.getHeader("Authorization"))
                assertEquals("application/grpc", first.getHeader("content-type"))
                val downloaded = stream.serverStreaming(GrpcPath.DOWNLOAD, "req".toByteArray(), null)
                assertArrayEquals("hi".toByteArray(), ImageProto.decodeChunkData(downloaded.single()))
                assertThrows<PixeldiveException.Transport> {
                    runBlocking { stream.clientStreaming(GrpcPath.UPLOAD_IMAGE, listOf(ByteArray(0)), null) }
                }
                assertThrows<PixeldiveException.GrpcStatus> {
                    runBlocking { stream.clientStreaming(GrpcPath.UPLOAD_IMAGE, listOf(ByteArray(0)), null) }
                }
                val port = server.port
                PixeldiveGrpcClient.insecure("127.0.0.1", port).close()
                stream.close()
                server.shutdown()
                val closed = OkHttpGrpcStreaming("127.0.0.1", port, h2cClient(1))
                assertThrows<PixeldiveException.Transport> {
                    runBlocking { closed.clientStreaming(GrpcPath.UPLOAD_IMAGE, emptyList(), null) }
                }
                closed.close()
                OkHttpGrpcStreaming("127.0.0.1", port, h2cClient(5), ownsHttp = false).close()
                h2cClient(5)
            } finally {
                runCatching { server.shutdown() }
            }
        }
    }

    @Test
    fun decodeSkipsUnknownFields() {
        val ids =
            ProtoWire.stringField(1, imageId) + ProtoWire.stringField(2, sessionId) +
                ProtoWire.varintField(9, 1) + ProtoWire.bytesField(8, byteArrayOf(1)) +
                ProtoWire.varintField(6, 1)
        val image = ImageProto.decodeSessionImage(ids)
        assertEquals(imageId, image.id.toString())
        val wrapped = ProtoWire.varintField(1, 0) + ProtoWire.bytesField(1, ids)
        assertEquals(imageId, ImageProto.decodeUpload(wrapped).id.toString())
        assertEquals(1, ImageProto.decodeBatch(ProtoWire.bytesField(3, ids) + ProtoWire.bytesField(1, ids)).size)
        val chunk = ProtoWire.varintField(5, 1) + ProtoWire.bytesField(5, byteArrayOf(9))
        assertArrayEquals(byteArrayOf(9), ImageProto.decodeChunkData(chunk))
        val timestamp = ProtoWire.bytesField(1, ByteArray(0)) + ProtoWire.varintField(1, 0)
        val withTs = ids + ProtoWire.bytesField(7, timestamp)
        assertEquals(Instant.EPOCH, ImageProto.decodeSessionImage(withTs).uploadedAt)
        val skipSizeWire =
            ids + byteArrayOf(0x29, 1, 2, 3, 4, 5, 6, 7, 8) + ProtoWire.varintField(5, 4)
        assertEquals(4, ImageProto.decodeSessionImage(skipSizeWire).sizeBytes)
        assertThrows<PixeldiveException.Decoding> {
            ProtoReader(
                byteArrayOf(0x0A, 0xFF.toByte(), 0xFF.toByte(), 0xFF.toByte(), 0xFF.toByte(), 0x0F),
            ).next()
        }
    }

    @Test
    fun finishWithoutBodyAndHeaderStatus() {
        val headers = Headers.headersOf("grpc-status", "7", "grpc-message", "denied")
        assertEquals(7 to "denied", grpcStatus(headers, Headers.headersOf()))
        val grpc = PixeldiveException.GrpcStatus(7, "denied")
        assertTrue(grpc.message!!.contains("7"))
        val fallback =
            grpcStatus(Headers.headersOf("grpc-status", "nope"), Headers.headersOf("grpc-status", "0"))
        assertEquals(0, fallback.first)
        val mixed =
            grpcStatus(
                Headers.headersOf("grpc-status", "0"),
                Headers.headersOf("grpc-message", "from-trailers"),
            )
        assertEquals("from-trailers", mixed.second)
        assertEquals(0, firstMessage(emptyList()).size)
        assertEquals(1, firstMessage(listOf(byteArrayOf(1))).size)
    }

    private fun grpcOk(
        payload: ByteArray,
        status: Int = 0,
        grpcMessage: String? = null,
    ): MockResponse {
        val pairs = mutableListOf("grpc-status", status.toString())
        if (grpcMessage != null) {
            pairs.add("grpc-message")
            pairs.add(grpcMessage)
        }
        return MockResponse()
            .setHeader("content-type", "application/grpc")
            .setTrailers(Headers.headersOf(*pairs.toTypedArray()))
            .setBody(okio.Buffer().write(GrpcFrames.encode(payload)))
    }

    private class RecordingStream(
        var response: ByteArray,
        var serverMessages: List<ByteArray>,
    ) : GrpcStreaming {
        var clientPath: String? = null
        var serverPath: String? = null
        var token: String? = null
        var clientMessages: List<ByteArray> = emptyList()

        override suspend fun clientStreaming(
            path: String,
            messages: List<ByteArray>,
            token: String?,
        ): ByteArray {
            clientPath = path
            clientMessages = messages
            this.token = token
            return response
        }

        override suspend fun serverStreaming(
            path: String,
            request: ByteArray,
            token: String?,
        ): List<ByteArray> {
            serverPath = path
            this.token = token
            return serverMessages
        }
    }

    companion object {
        private const val UPLOAD_RESP =
            "0a6c0a2431323365343536372d653839622d313264332d613435362d343236363134313734303031" +
                "122431323365343536372d653839622d313264332d613435362d343236363134313734303030" +
                "1a096672616d652e706e672209696d6167652f706e6728433a0608c095bfd506"
    }
}

private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }

private fun String.hexToBytes(): ByteArray {
    val clean = replace(" ", "")
    return ByteArray(clean.length / 2) { index ->
        clean.substring(index * 2, index * 2 + 2).toInt(16).toByte()
    }
}
