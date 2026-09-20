package com.pixeldive.sdk

/**
 * Supplies a [SessionCreate] payload. The Compose demo implements this with
 * `Build`, `ActivityManager`, and Camera2; JVM tests use [JvmDeviceProbe].
 */
fun interface DeviceProbe {
    fun snapshot(sessionName: String): SessionCreate
}

/** Android-shaped session payloads collected on-device or from the sample Pixel. */
object DeviceSnapshot {
    /** Bundled Pixel-like payload used by tests and the demo when live APIs are unavailable. */
    fun samplePixel(sessionName: String = "android-demo-capture"): SessionCreate =
        SessionCreate(
            sessionName = sessionName,
            phoneInfo =
                PhoneInfo(
                    manufacturer = "Google",
                    model = "Pixel 9 Pro",
                    brand = "google",
                    device = "caiman",
                    board = "caiman",
                    androidVersion = "15",
                    sdkInt = 35,
                ),
            phoneCapabilities =
                PhoneCapabilities(
                    totalRamMb = 16384,
                    availableRamMb = 8192,
                    cpuAbi = "arm64-v8a",
                    cpuCores = 8,
                    screenWidthPx = 1280,
                    screenHeightPx = 2856,
                    screenDensityDpi = 480,
                    isLowRamDevice = false,
                ),
            cameraCapabilities =
                CameraCapabilities(
                    listOf(
                        CameraInfo(
                            cameraId = "0",
                            lensFacing = "BACK",
                            hardwareLevel = "LEVEL_3",
                            sensorOrientation = 90,
                            maxResolution = "4080x3072",
                            hasFlash = true,
                            hasOpticalStabilization = true,
                            supportedCapabilities = listOf("BACKWARD_COMPATIBLE", "RAW"),
                        ),
                        CameraInfo(
                            cameraId = "1",
                            lensFacing = "FRONT",
                            hardwareLevel = "LIMITED",
                            sensorOrientation = 270,
                            maxResolution = "4080x3072",
                            hasFlash = false,
                            hasOpticalStabilization = false,
                            supportedCapabilities = listOf("BACKWARD_COMPATIBLE"),
                        ),
                    ),
                ),
            metadata =
                JsonValue.strings(
                    mapOf(
                        "source" to "pixeldive-android-sdk",
                        "platform" to "android",
                        "system_name" to "Android",
                        "android_version" to "15",
                    ),
                ),
        )

    /** Decode the bundled fixture (same object as [samplePixel]). */
    fun bundledSample(): SessionCreate {
        val stream =
            DeviceSnapshot::class.java.getResourceAsStream("/sample_android_session.json")
                ?: throw PixeldiveException.Decoding("missing sample_android_session.json")
        val text = stream.bufferedReader().use { it.readText() }
        return try {
            JsonCodec.json.decodeFromString(SessionCreate.serializer(), text)
        } catch (exc: Exception) {
            throw PixeldiveException.Decoding(exc.message ?: exc.toString())
        }
    }

    /** Live device mapping via [probe]; JVM default overlays Runtime onto the sample. */
    fun current(
        sessionName: String = "android-demo-capture",
        probe: DeviceProbe = JvmDeviceProbe,
    ): SessionCreate = probe.snapshot(sessionName)
}

/** Process/Runtime fallback when Camera2 and `Build` are not on the classpath. */
object JvmDeviceProbe : DeviceProbe {
    override fun snapshot(sessionName: String): SessionCreate {
        val runtime = Runtime.getRuntime()
        val totalMb = (runtime.totalMemory() / 1_048_576L).toInt().coerceAtLeast(1)
        val freeMb = (runtime.freeMemory() / 1_048_576L).toInt().coerceAtLeast(1)
        val sample = DeviceSnapshot.samplePixel(sessionName)
        return sample.copy(
            phoneInfo =
                sample.phoneInfo.copy(
                    model = System.getProperty("os.name") ?: sample.phoneInfo.model,
                    androidVersion = System.getProperty("os.version") ?: sample.phoneInfo.androidVersion,
                ),
            phoneCapabilities =
                sample.phoneCapabilities.copy(
                    cpuCores = runtime.availableProcessors(),
                    totalRamMb = totalMb,
                    availableRamMb = freeMb,
                    isLowRamDevice = totalMb < 2048,
                ),
            metadata =
                sample.metadata +
                    JsonValue.strings(
                        mapOf(
                            "live_source" to "runtime",
                            "os_name" to (System.getProperty("os.name") ?: "unknown"),
                        ),
                    ),
        )
    }
}
