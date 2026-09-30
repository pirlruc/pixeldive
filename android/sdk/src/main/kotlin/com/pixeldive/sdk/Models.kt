package com.pixeldive.sdk

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.time.Instant
import java.util.UUID

/** Android `Build.*` identity collected by capture clients (wire names unchanged). */
@Serializable
data class PhoneInfo(
    /** Android `Build.MANUFACTURER`. */
    val manufacturer: String,
    /** Android `Build.MODEL`. */
    val model: String,
    /** Android `Build.BRAND`. */
    val brand: String,
    /** Android `Build.DEVICE`. */
    val device: String,
    /** Android `Build.BOARD`. */
    val board: String,
    /** Android `Build.VERSION.RELEASE`. iOS sends its OS version string. */
    @SerialName("android_version") val androidVersion: String,
    /** Android `Build.VERSION.SDK_INT`. iOS sends its major version. */
    @SerialName("sdk_int") val sdkInt: Int,
)

/** RAM, CPU, and display metrics (ActivityManager / DisplayMetrics). */
@Serializable
data class PhoneCapabilities(
    /** Total RAM in mebibytes. */
    @SerialName("total_ram_mb") val totalRamMb: Int,
    /** Available RAM in mebibytes. */
    @SerialName("available_ram_mb") val availableRamMb: Int,
    /** Primary ABI from `Build.SUPPORTED_ABIS`. */
    @SerialName("cpu_abi") val cpuAbi: String,
    /** `Runtime.availableProcessors()`. */
    @SerialName("cpu_cores") val cpuCores: Int,
    /** Display width in pixels. */
    @SerialName("screen_width_px") val screenWidthPx: Int,
    /** Display height in pixels. */
    @SerialName("screen_height_px") val screenHeightPx: Int,
    /** Display density in dpi. */
    @SerialName("screen_density_dpi") val screenDensityDpi: Int,
    /** `ActivityManager.isLowRamDevice()`. */
    @SerialName("is_low_ram_device") val isLowRamDevice: Boolean,
)

/** One Camera2-shaped camera row. */
@Serializable
data class CameraInfo(
    /** Camera2 camera id. */
    @SerialName("camera_id") val cameraId: String,
    /** `FRONT`, `BACK`, or `EXTERNAL`. */
    @SerialName("lens_facing") val lensFacing: String,
    /** Camera2 hardware level label. */
    @SerialName("hardware_level") val hardwareLevel: String,
    /** Sensor orientation in degrees. */
    @SerialName("sensor_orientation") val sensorOrientation: Int,
    /** Largest still size, `WIDTHxHEIGHT`. */
    @SerialName("max_resolution") val maxResolution: String,
    /** Whether the camera has a flash unit. */
    @SerialName("has_flash") val hasFlash: Boolean,
    /** Whether optical image stabilization is available. */
    @SerialName("has_optical_stabilization") val hasOpticalStabilization: Boolean,
    /** Camera2 capability labels. */
    @SerialName("supported_capabilities") val supportedCapabilities: List<String>,
)

/** Camera enumeration. `cameraCount` must equal `cameras.size`. */
@Serializable
data class CameraCapabilities(
    /** Must equal [cameras].size. */
    @SerialName("camera_count") val cameraCount: Int,
    /** One row per discovered camera. */
    val cameras: List<CameraInfo>,
) {
    init {
        require(cameraCount >= 0) { "camera_count must be >= 0" }
        require(cameraCount == cameras.size) { "camera_count must equal cameras.size" }
    }

    constructor(cameras: List<CameraInfo>) : this(cameras.size, cameras)
}

/** POST `/api/v1/sessions` body. */
@Serializable
data class SessionCreate(
    /** Caller-chosen session name. */
    @SerialName("session_name") val sessionName: String,
    /** Device identity. */
    @SerialName("phone_info") val phoneInfo: PhoneInfo,
    /** RAM, CPU, and display metrics. */
    @SerialName("phone_capabilities") val phoneCapabilities: PhoneCapabilities,
    /** Camera enumeration. */
    @SerialName("camera_capabilities") val cameraCapabilities: CameraCapabilities,
    /** Free-form session metadata. */
    val metadata: Map<String, JsonValue> = emptyMap(),
)

/** PUT `/api/v1/sessions/{id}` body. All fields optional. */
@Serializable
data class SessionUpdate(
    /** New session name, or null to leave it unchanged. */
    @SerialName("session_name") val sessionName: String? = null,
    /** New status, or null to leave it unchanged. */
    val status: String? = null,
    /** Replacement or patch metadata. Null leaves metadata unchanged. */
    val metadata: Map<String, JsonValue>? = null,
    /** When true, [metadata] is merged. When false, it replaces the map. */
    @SerialName("merge_metadata") val mergeMetadata: Boolean = false,
)

/** Public session representation (no storage paths). */
@Serializable
data class SessionRead(
    /** Session id. */
    @Serializable(with = UuidSerializer::class) val id: UUID,
    /** Session name. */
    @SerialName("session_name") val sessionName: String,
    /** Session status. */
    val status: String,
    /** Creation time. */
    @SerialName("created_at") @Serializable(with = InstantSerializer::class) val createdAt: Instant,
    /** Last update time. */
    @SerialName("updated_at") @Serializable(with = InstantSerializer::class) val updatedAt: Instant,
    /** Device identity captured at create time. */
    @SerialName("phone_info") val phoneInfo: PhoneInfo,
    /** Device capabilities captured at create time. */
    @SerialName("phone_capabilities") val phoneCapabilities: PhoneCapabilities,
    /** Camera capabilities captured at create time. */
    @SerialName("camera_capabilities") val cameraCapabilities: CameraCapabilities,
    /** Session metadata. Storage paths are not included. */
    val metadata: Map<String, JsonValue> = emptyMap(),
)

/** Paginated session list. */
@Serializable
data class SessionPage(
    /** Sessions in this page. */
    val items: List<SessionRead>,
    /** Cursor for the next page, or null when this is the last page. */
    @SerialName("next_cursor") val nextCursor: String? = null,
)

/** Public image metadata (no `storage_path`). */
@Serializable
data class SessionImage(
    /** Image id. */
    @Serializable(with = UuidSerializer::class) val id: UUID,
    /** Owning session id. */
    @SerialName("session_id") @Serializable(with = UuidSerializer::class) val sessionId: UUID,
    /** Original filename. */
    val filename: String,
    /** Stored media type. */
    @SerialName("content_type") val contentType: String,
    /** Stored size in bytes. */
    @SerialName("size_bytes") val sizeBytes: Int,
    /** Upload time. */
    @SerialName("uploaded_at") @Serializable(with = InstantSerializer::class) val uploadedAt: Instant,
    /** Image metadata. `storage_path` is not included. */
    val metadata: Map<String, JsonValue> = emptyMap(),
)

/** Paginated image list. */
@Serializable
data class ImagePage(
    /** Images in this page. */
    val items: List<SessionImage>,
    /** Cursor for the next page, or null when this is the last page. */
    @SerialName("next_cursor") val nextCursor: String? = null,
)

/** Liveness or readiness probe payload. */
@Serializable
data class HealthStatus(
    /** Probe result, typically `ok`. */
    val status: String,
)
