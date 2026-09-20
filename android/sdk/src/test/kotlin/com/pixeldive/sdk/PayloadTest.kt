package com.pixeldive.sdk

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class PayloadTest {
    @Test
    fun sampleMatchesBundledFixture() {
        val sample = DeviceSnapshot.samplePixel()
        val bundled = DeviceSnapshot.bundledSample()
        assertEquals(sample, bundled)
        assertEquals(sample.cameraCapabilities.cameras.size, sample.cameraCapabilities.cameraCount)
        assertEquals(JsonValue.Str("android"), sample.metadata["platform"])
        assertEquals("Google", sample.phoneInfo.manufacturer)
        assertEquals(35, sample.phoneInfo.sdkInt)
    }

    @Test
    fun sampleEncodesAndroidWireKeys() {
        val text = JsonCodec.json.encodeToString(SessionCreate.serializer(), DeviceSnapshot.samplePixel())
        assertTrue(text.contains("\"android_version\":\"15\""))
        assertTrue(text.contains("\"sdk_int\":35"))
        assertFalse(text.contains("storage_path"))
        assertTrue(text.contains("\"camera_count\":2"))
    }

    @Test
    fun currentSnapshotIsAndroidShaped() {
        val live = DeviceSnapshot.current(sessionName = "live")
        assertEquals("live", live.sessionName)
        assertEquals(live.cameraCapabilities.cameras.size, live.cameraCapabilities.cameraCount)
        assertEquals(JsonValue.Str("android"), live.metadata["platform"])
        assertFalse(live.phoneInfo.androidVersion.isEmpty())
        assertEquals(JsonValue.Str("runtime"), live.metadata["live_source"])
    }

    @Test
    fun jsonValueRoundTrip() {
        val original =
            mapOf(
                "flag" to JsonValue.Bool(true),
                "n" to JsonValue.IntNumber(3),
                "nested" to JsonValue.Obj(mapOf("k" to JsonValue.Str("v"))),
            )
        val wrapper = SessionUpdate(metadata = original)
        val text = JsonCodec.json.encodeToString(SessionUpdate.serializer(), wrapper)
        val decoded = JsonCodec.json.decodeFromString(SessionUpdate.serializer(), text)
        assertEquals(original, decoded.metadata)
    }

    @Test
    fun camera2Labels() {
        assertEquals("FRONT", Camera2Labels.lensFacing(Camera2Labels.LENS_FACING_FRONT))
        assertEquals("BACK", Camera2Labels.lensFacing(Camera2Labels.LENS_FACING_BACK))
        assertEquals("EXTERNAL", Camera2Labels.lensFacing(null))
        assertEquals("LEVEL_3", Camera2Labels.hardwareLevel(Camera2Labels.HARDWARE_LEVEL_3))
        assertEquals("FULL", Camera2Labels.hardwareLevel(Camera2Labels.HARDWARE_LEVEL_FULL))
        assertEquals("LEGACY", Camera2Labels.hardwareLevel(Camera2Labels.HARDWARE_LEVEL_LEGACY))
        assertEquals("LIMITED", Camera2Labels.hardwareLevel(null))
        assertEquals("EXTERNAL", Camera2Labels.hardwareLevel(Camera2Labels.HARDWARE_LEVEL_EXTERNAL))
        assertEquals("RAW", Camera2Labels.capability(Camera2Labels.CAPABILITY_RAW))
        assertEquals("MANUAL_SENSOR", Camera2Labels.capability(Camera2Labels.CAPABILITY_MANUAL_SENSOR))
        assertEquals(
            "MANUAL_POST_PROCESSING",
            Camera2Labels.capability(Camera2Labels.CAPABILITY_MANUAL_POST_PROCESSING),
        )
        assertEquals("CAPABILITY_9", Camera2Labels.capability(9))
        assertEquals(listOf("BACKWARD_COMPATIBLE"), Camera2Labels.capabilities(null))
        assertEquals("12x8", Camera2Labels.maxResolution(12, 8))
    }

    @Test
    fun resourceIdParse() {
        val value = ResourceId.parse("123e4567-e89b-12d3-a456-426614174000")
        assertEquals("123e4567-e89b-12d3-a456-426614174000", value)
        assertThrows<PixeldiveException.InvalidResourceId> { ResourceId.parse("../secret") }
        assertThrows<PixeldiveException.InvalidResourceId> { ResourceId.parse("not-a-uuid") }
    }

    @Test
    fun cameraCountMustMatch() {
        assertThrows<IllegalArgumentException> {
            CameraCapabilities(cameraCount = 1, cameras = emptyList())
        }
    }

    @Test
    fun cameraCountMustMatchOnDecode() {
        val text = """{"camera_count":1,"cameras":[]}"""
        assertThrows<Exception> {
            JsonCodec.json.decodeFromString(CameraCapabilities.serializer(), text)
        }
    }

    @Test
    fun jsonValueNullArrayFloat() {
        val original =
            mapOf(
                "empty" to JsonValue.Null,
                "nums" to JsonValue.Arr(listOf(JsonValue.FloatNumber(1.5), JsonValue.IntNumber(2))),
            )
        val wrapper = SessionUpdate(metadata = original)
        val text = JsonCodec.json.encodeToString(SessionUpdate.serializer(), wrapper)
        val decoded = JsonCodec.json.decodeFromString(SessionUpdate.serializer(), text)
        assertEquals(original, decoded.metadata)
    }

    @Test
    fun sanitizerAndPageQuery() {
        assertEquals("c___.png", sanitizeMultipartFilename("a/b\\c\r\n\".png"))
        assertEquals("upload.bin", sanitizeMultipartFilename(""))
        assertEquals("image/png", sanitizeMultipartType("image/png\r\nX: 1"))
        assertEquals("application/octet-stream", sanitizeMultipartType("nope"))
        val query = pageQuery(3, "next")
        assertEquals("3", query["limit"])
        assertEquals("next", query["cursor"])
        assertEquals("BACKWARD_COMPATIBLE", Camera2Labels.capability(Camera2Labels.CAPABILITY_BACKWARD_COMPATIBLE))
        assertEquals("EXTERNAL", Camera2Labels.lensFacing(Camera2Labels.LENS_FACING_EXTERNAL))
    }
}
