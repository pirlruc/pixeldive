package com.pixeldive.sdk

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.util.UUID

class ClientTest {
    private val sessionId = UUID.fromString("123e4567-e89b-12d3-a456-426614174000")
    private val imageId = UUID.fromString("123e4567-e89b-12d3-a456-426614174001")
    private lateinit var server: MockWebServer

    @BeforeEach
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @AfterEach
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun healthReadyAndSessionRoundTrip() =
        runBlocking {
            server.enqueue(json(mapOf("status" to "ok")))
            server.enqueue(json(mapOf("status" to "ok")))
            server.enqueue(json(sessionJson()))
            server.enqueue(json(mapOf("items" to listOf(sessionJson()), "next_cursor" to null)))
            server.enqueue(json(sessionJson()))
            server.enqueue(json(sessionJson()))
            server.enqueue(MockResponse().setResponseCode(204))
            val client = client()
            assertEquals("ok", client.health().status)
            assertEquals("ok", client.ready().status)
            val created = client.createSession(DeviceSnapshot.samplePixel())
            assertEquals(sessionId, created.id)
            val listed = client.listSessions(limit = 10)
            assertEquals(sessionId, listed.items.first().id)
            client.getSession(sessionId.toString())
            client.updateSession(
                sessionId.toString(),
                SessionUpdate(metadata = mapOf("k" to JsonValue.Str("v")), mergeMetadata = true),
            )
            client.deleteSession(sessionId.toString())
            assertEquals(
                listOf("GET", "GET", "POST", "GET", "GET", "PUT", "DELETE"),
                (0 until server.requestCount).map { server.takeRequest().method },
            )
        }

    @Test
    fun createBodyUsesAndroidWireKeys() =
        runBlocking {
            server.enqueue(json(sessionJson()))
            client().createSession(DeviceSnapshot.samplePixel())
            val body = server.takeRequest().body.readUtf8()
            assertTrue(body.contains("\"sdk_int\":35"))
            assertTrue(body.contains("\"android_version\":\"15\""))
            assertTrue(body.contains("\"platform\":\"android\""))
            assertFalse(body.contains("storage_path"))
        }

    @Test
    fun uploadListDownload() =
        runBlocking {
            val png = TestPng.BYTES
            server.enqueue(json(imageJson()))
            server.enqueue(json(mapOf("items" to listOf(imageJson()), "next_cursor" to null)))
            server.enqueue(
                MockResponse()
                    .setHeader("Content-Type", "image/png")
                    .setBody(okio.Buffer().write(png)),
            )
            val client = client()
            val uploaded =
                client.uploadImage(
                    sessionId.toString(),
                    "frame.png",
                    png,
                    metadata = "{\"iso\":64}",
                )
            assertEquals(imageId, uploaded.id)
            assertNull(uploaded::class.java.declaredFields.find { it.name == "storagePath" })
            assertEquals(1, client.listImages(sessionId.toString()).items.size)
            assertTrue(client.downloadImage(sessionId.toString(), imageId.toString()).contentEquals(png))
            val upload = server.takeRequest()
            assertEquals("POST", upload.method)
            val contentType = upload.getHeader("Content-Type").orEmpty()
            assertTrue(contentType.startsWith("multipart/form-data"))
            val body = upload.body.readUtf8()
            assertTrue(body.contains("filename=\"frame.png\"") || body.contains("frame.png"))
        }

    @Test
    fun uploadBatchAndFile() =
        runBlocking {
            server.enqueue(json(listOf(imageJson())))
            server.enqueue(json(imageJson()))
            val client = client()
            val batch =
                client.uploadImagesBatch(
                    sessionId.toString(),
                    listOf(Triple("a.png", TestPng.BYTES, "image/png")),
                )
            assertEquals(1, batch.size)
            val temp = kotlin.io.path.createTempFile(suffix = ".png").toFile()
            temp.writeBytes(TestPng.BYTES)
            try {
                client.uploadImage(sessionId.toString(), temp)
            } finally {
                temp.delete()
            }
        }

    @Test
    fun httpErrorAndAuthHeader() {
        server.enqueue(MockResponse().setResponseCode(404).setBody("{\"detail\":\"gone\"}"))
        val client = client(token = "secret-token")
        val error =
            assertThrows<PixeldiveException.HttpStatus> {
                runBlocking { client.health() }
            }
        assertEquals(404, error.code)
        assertTrue(error.body.contains("gone"))
        assertEquals("Bearer secret-token", server.takeRequest().getHeader("Authorization"))
    }

    @Test
    fun rejectsNonUuidSession() {
        val client = client()
        assertThrows<PixeldiveException.InvalidResourceId> {
            runBlocking { client.getSession("../etc/passwd") }
        }
    }

    private fun client(token: String? = null): PixeldiveClient =
        PixeldiveClient(baseUrl = server.url("/").toString(), token = token)

    private fun json(body: Any): MockResponse {
        val text = JsonCodec.json.encodeToString(kotlinx.serialization.json.JsonElement.serializer(), toElement(body))
        return MockResponse().setHeader("Content-Type", "application/json").setBody(text)
    }

    private fun toElement(value: Any?): kotlinx.serialization.json.JsonElement =
        when (value) {
            null -> kotlinx.serialization.json.JsonNull
            is kotlinx.serialization.json.JsonElement -> value
            is String -> kotlinx.serialization.json.JsonPrimitive(value)
            is Int -> kotlinx.serialization.json.JsonPrimitive(value)
            is Boolean -> kotlinx.serialization.json.JsonPrimitive(value)
            is Map<*, *> ->
                kotlinx.serialization.json.JsonObject(
                    value.entries.associate { (k, v) -> k.toString() to toElement(v) },
                )
            is List<*> -> kotlinx.serialization.json.JsonArray(value.map { toElement(it) })
            else -> kotlinx.serialization.json.JsonPrimitive(value.toString())
        }

    private fun sessionJson(): Map<String, Any?> =
        mapOf(
            "id" to sessionId.toString(),
            "session_name" to "android-demo-capture",
            "status" to "CREATED",
            "created_at" to "2026-09-20T12:00:00.000000Z",
            "updated_at" to "2026-09-20T12:00:00.000000Z",
            "phone_info" to
                mapOf(
                    "manufacturer" to "Google",
                    "model" to "Pixel 9 Pro",
                    "brand" to "google",
                    "device" to "caiman",
                    "board" to "caiman",
                    "android_version" to "15",
                    "sdk_int" to 35,
                ),
            "phone_capabilities" to
                mapOf(
                    "total_ram_mb" to 16384,
                    "available_ram_mb" to 8192,
                    "cpu_abi" to "arm64-v8a",
                    "cpu_cores" to 8,
                    "screen_width_px" to 1280,
                    "screen_height_px" to 2856,
                    "screen_density_dpi" to 480,
                    "is_low_ram_device" to false,
                ),
            "camera_capabilities" to mapOf("camera_count" to 0, "cameras" to emptyList<Any>()),
            "metadata" to mapOf("source" to "pixeldive-android-sdk"),
        )

    private fun imageJson(): Map<String, Any?> =
        mapOf(
            "id" to imageId.toString(),
            "session_id" to sessionId.toString(),
            "filename" to "frame.png",
            "content_type" to "image/png",
            "size_bytes" to TestPng.BYTES.size,
            "uploaded_at" to "2026-09-20T12:00:00.000000Z",
            "metadata" to mapOf("iso" to 64),
        )
}

object TestPng {
    val BYTES =
        byteArrayOf(
            0x89.toByte(), 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
            0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15.toByte(), 0xC4.toByte(), 0x89.toByte(), 0x00, 0x00, 0x00,
            0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C.toByte(), 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4.toByte(), 0x00, 0x00, 0x00, 0x00, 0x49,
            0x45, 0x4E, 0x44, 0xAE.toByte(), 0x42, 0x60, 0x82.toByte(),
        )
}
