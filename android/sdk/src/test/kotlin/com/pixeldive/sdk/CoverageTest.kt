package com.pixeldive.sdk

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant
import java.util.UUID

class CoverageTest {
    private val sessionId = UUID.fromString("123e4567-e89b-12d3-a456-426614174000")
    private val imageId = UUID.fromString("123e4567-e89b-12d3-a456-426614174001")
    private val stamp = Instant.parse("2026-09-20T12:00:00Z")

    @Test
    fun dataClassesEqualsCopyAndSerializers() {
        val sample = DeviceSnapshot.samplePixel()
        assertEquals(sample, sample.copy())
        assertEquals(sample.hashCode(), sample.copy().hashCode())
        assertNotEquals(sample, sample.copy(sessionName = "other"))
        assertNotEquals(sample, "nope")
        assertTrue(sample.toString().contains("android-demo-capture"))

        val phone = sample.phoneInfo
        assertEquals(phone, phone.copy())
        assertNotEquals(phone, phone.copy(model = "other"))

        val caps = sample.phoneCapabilities
        assertEquals(caps, caps.copy())
        assertNotEquals(caps, caps.copy(cpuCores = 1))

        val camera = sample.cameraCapabilities.cameras.first()
        assertEquals(camera, camera.copy())
        assertNotEquals(camera, camera.copy(cameraId = "x"))

        val health = HealthStatus("ok")
        assertEquals(health, health.copy(status = "ok"))
        assertNotEquals(health, HealthStatus("down"))

        val update =
            SessionUpdate(sessionName = "n", status = "CREATED", metadata = emptyMap(), mergeMetadata = true)
        assertEquals(update, update.copy())
        assertNotEquals(update, SessionUpdate())
        assertNotEquals(update, update.copy(mergeMetadata = false))

        val image =
            SessionImage(imageId, sessionId, "frame.png", "image/png", 8, stamp, emptyMap())
        assertEquals(image, image.copy())
        assertNotEquals(image, image.copy(filename = "other.png"))

        val page = SessionPage(listOf(sessionRead(sample)), "next")
        assertEquals(page, page.copy())
        assertNotEquals(page, page.copy(nextCursor = null))

        val images = ImagePage(listOf(image), null)
        assertEquals(images, images.copy())
        assertNotEquals(images, images.copy(nextCursor = "n"))

        val encoded = JsonCodec.json.encodeToString(SessionRead.serializer(), sessionRead(sample))
        val decoded = JsonCodec.json.decodeFromString(SessionRead.serializer(), encoded)
        assertEquals(sample.sessionName, decoded.sessionName)
        val encodedImage = JsonCodec.json.encodeToString(SessionImage.serializer(), image)
        assertTrue(encodedImage.contains("frame.png"))
    }

    @Test
    fun cameraCountNegativeAndHelpers() {
        assertThrows<IllegalArgumentException> {
            CameraCapabilities(cameraCount = -1, cameras = emptyList())
        }
        val body =
            multipartBatch(
                listOf(Triple("a.png", TestPng.BYTES, "image/png")),
                mapOf("metadata" to "{}"),
            )
        assertEquals(MultipartBody.FORM, body.type)
        assertTrue(defaultHttp(5).connectTimeoutMillis > 0)
        pageQuery(1, null)
        pageQuery(1, "")
        assertEquals(mapOf("metadata" to "{}"), metadataFields("{}"))
        assertTrue(metadataFields(null).isEmpty())
        val fromBody =
            multipart(
                "file",
                "a.png",
                TestPng.BYTES.toRequestBody("image/png".toMediaType()),
                emptyMap(),
            )
        assertEquals(MultipartBody.FORM, fromBody.type)
    }

    @Test
    fun exceptionTypes() {
        val invalid = PixeldiveException.InvalidResourceId("x")
        val status = PixeldiveException.HttpStatus(500, "nope")
        val decoding = PixeldiveException.Decoding("bad", IllegalStateException("root"))
        val transport = PixeldiveException.Transport("down", IllegalStateException("root"))
        assertTrue(invalid.message!!.contains("x"))
        assertTrue(status.message!!.contains("500"))
        assertTrue(decoding.cause is IllegalStateException)
        assertTrue(transport.cause is IllegalStateException)
        JsonCodec.json.encodeToString(UuidSerializer, sessionId)
        JsonCodec.json.encodeToString(InstantSerializer, stamp)
        DeviceSnapshot.current()
        PixeldiveException.Decoding("bad")
        PixeldiveException.Transport("down")
    }

    private fun sessionRead(sample: SessionCreate): SessionRead =
        SessionRead(
            id = sessionId,
            sessionName = sample.sessionName,
            status = "CREATED",
            createdAt = stamp,
            updatedAt = stamp,
            phoneInfo = sample.phoneInfo,
            phoneCapabilities = sample.phoneCapabilities,
            cameraCapabilities = sample.cameraCapabilities,
            metadata = sample.metadata,
        )
}
