package com.pixeldive.sdk

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.time.Instant
import java.util.UUID

/** Android `Build.*` identity collected by capture clients (wire names unchanged). */
@Serializable
data class PhoneInfo(
    val manufacturer: String,
    val model: String,
    val brand: String,
    val device: String,
    val board: String,
    @SerialName("android_version") val androidVersion: String,
    @SerialName("sdk_int") val sdkInt: Int,
)

/** RAM, CPU, and display metrics (ActivityManager / DisplayMetrics). */
@Serializable
data class PhoneCapabilities(
    @SerialName("total_ram_mb") val totalRamMb: Int,
    @SerialName("available_ram_mb") val availableRamMb: Int,
    @SerialName("cpu_abi") val cpuAbi: String,
    @SerialName("cpu_cores") val cpuCores: Int,
    @SerialName("screen_width_px") val screenWidthPx: Int,
    @SerialName("screen_height_px") val screenHeightPx: Int,
    @SerialName("screen_density_dpi") val screenDensityDpi: Int,
    @SerialName("is_low_ram_device") val isLowRamDevice: Boolean,
)

/** One Camera2-shaped camera row. */
@Serializable
data class CameraInfo(
    @SerialName("camera_id") val cameraId: String,
    @SerialName("lens_facing") val lensFacing: String,
    @SerialName("hardware_level") val hardwareLevel: String,
    @SerialName("sensor_orientation") val sensorOrientation: Int,
    @SerialName("max_resolution") val maxResolution: String,
    @SerialName("has_flash") val hasFlash: Boolean,
    @SerialName("has_optical_stabilization") val hasOpticalStabilization: Boolean,
    @SerialName("supported_capabilities") val supportedCapabilities: List<String>,
)

/** Camera enumeration. `cameraCount` must equal `cameras.size`. */
@Serializable
data class CameraCapabilities(
    @SerialName("camera_count") val cameraCount: Int,
    val cameras: List<CameraInfo>,
) {
    init {
        require(cameraCount == cameras.size) { "camera_count must equal cameras.size" }
        require(cameraCount >= 0) { "camera_count must be >= 0" }
    }

    constructor(cameras: List<CameraInfo>) : this(cameras.size, cameras)
}

/** POST `/api/v1/sessions` body. */
@Serializable
data class SessionCreate(
    @SerialName("session_name") val sessionName: String,
    @SerialName("phone_info") val phoneInfo: PhoneInfo,
    @SerialName("phone_capabilities") val phoneCapabilities: PhoneCapabilities,
    @SerialName("camera_capabilities") val cameraCapabilities: CameraCapabilities,
    val metadata: Map<String, JsonValue> = emptyMap(),
)

/** PUT `/api/v1/sessions/{id}` body. All fields optional. */
@Serializable
data class SessionUpdate(
    @SerialName("session_name") val sessionName: String? = null,
    val status: String? = null,
    val metadata: Map<String, JsonValue>? = null,
    @SerialName("merge_metadata") val mergeMetadata: Boolean = false,
)

/** Public session representation (no storage paths). */
@Serializable
data class SessionRead(
    @Serializable(with = UuidSerializer::class) val id: UUID,
    @SerialName("session_name") val sessionName: String,
    val status: String,
    @SerialName("created_at") @Serializable(with = InstantSerializer::class) val createdAt: Instant,
    @SerialName("updated_at") @Serializable(with = InstantSerializer::class) val updatedAt: Instant,
    @SerialName("phone_info") val phoneInfo: PhoneInfo,
    @SerialName("phone_capabilities") val phoneCapabilities: PhoneCapabilities,
    @SerialName("camera_capabilities") val cameraCapabilities: CameraCapabilities,
    val metadata: Map<String, JsonValue> = emptyMap(),
)

/** Paginated session list. */
@Serializable
data class SessionPage(
    val items: List<SessionRead>,
    @SerialName("next_cursor") val nextCursor: String? = null,
)

/** Public image metadata (no `storage_path`). */
@Serializable
data class SessionImage(
    @Serializable(with = UuidSerializer::class) val id: UUID,
    @SerialName("session_id") @Serializable(with = UuidSerializer::class) val sessionId: UUID,
    val filename: String,
    @SerialName("content_type") val contentType: String,
    @SerialName("size_bytes") val sizeBytes: Int,
    @SerialName("uploaded_at") @Serializable(with = InstantSerializer::class) val uploadedAt: Instant,
    val metadata: Map<String, JsonValue> = emptyMap(),
)

/** Paginated image list. */
@Serializable
data class ImagePage(
    val items: List<SessionImage>,
    @SerialName("next_cursor") val nextCursor: String? = null,
)

/** Liveness or readiness probe payload. */
@Serializable
data class HealthStatus(
    val status: String,
)
