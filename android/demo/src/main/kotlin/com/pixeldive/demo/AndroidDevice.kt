package com.pixeldive.demo

import android.app.ActivityManager
import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.os.Build
import android.util.Size
import com.pixeldive.sdk.Camera2Labels
import com.pixeldive.sdk.CameraCapabilities
import com.pixeldive.sdk.CameraInfo
import com.pixeldive.sdk.DeviceProbe
import com.pixeldive.sdk.DeviceSnapshot
import com.pixeldive.sdk.JsonValue
import com.pixeldive.sdk.PhoneCapabilities
import com.pixeldive.sdk.PhoneInfo
import com.pixeldive.sdk.SessionCreate

/** Maps `Build`, ActivityManager, DisplayMetrics, and Camera2 into Android wire keys. */
class AndroidDeviceProbe(
    private val context: Context,
) : DeviceProbe {
    override fun snapshot(sessionName: String): SessionCreate {
        val mem = ActivityManager.MemoryInfo()
        val activity = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        activity.getMemoryInfo(mem)
        val totalMb = (mem.totalMem / 1_048_576L).toInt()
        val availMb = (mem.availMem / 1_048_576L).toInt()
        val metrics = context.resources.displayMetrics
        val abi = Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown"
        return SessionCreate(
            sessionName = sessionName,
            phoneInfo =
                PhoneInfo(
                    manufacturer = Build.MANUFACTURER,
                    model = Build.MODEL,
                    brand = Build.BRAND,
                    device = Build.DEVICE,
                    board = Build.BOARD,
                    androidVersion = Build.VERSION.RELEASE,
                    sdkInt = Build.VERSION.SDK_INT,
                ),
            phoneCapabilities =
                PhoneCapabilities(
                    totalRamMb = totalMb,
                    availableRamMb = availMb,
                    cpuAbi = abi,
                    cpuCores = Runtime.getRuntime().availableProcessors(),
                    screenWidthPx = metrics.widthPixels,
                    screenHeightPx = metrics.heightPixels,
                    screenDensityDpi = metrics.densityDpi,
                    isLowRamDevice = activity.isLowRamDevice,
                ),
            cameraCapabilities = CameraCapabilities(liveCameras()),
            metadata =
                JsonValue.strings(
                    mapOf(
                        "source" to "pixeldive-android-sdk",
                        "platform" to "android",
                        "system_name" to "Android",
                        "android_version" to Build.VERSION.RELEASE,
                    ),
                ),
        )
    }

    private fun liveCameras(): List<CameraInfo> {
        val cameras =
            try {
                val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
                manager.cameraIdList.map { id -> cameraInfo(manager, id) }
            } catch (_: Exception) {
                emptyList()
            }
        return cameras.ifEmpty { DeviceSnapshot.samplePixel().cameraCapabilities.cameras }
    }

    private fun cameraInfo(
        manager: CameraManager,
        id: String,
    ): CameraInfo {
        val chars = manager.getCameraCharacteristics(id)
        val facing = chars.get(CameraCharacteristics.LENS_FACING)
        val level = chars.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)
        val orientation = chars.get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 90
        val flash = chars.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
        val ois =
            chars.get(CameraCharacteristics.LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION)
                ?.isNotEmpty() == true
        val caps = chars.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)
        val size = largestSize(chars)
        return CameraInfo(
            cameraId = id,
            lensFacing = Camera2Labels.lensFacing(facing),
            hardwareLevel = Camera2Labels.hardwareLevel(level),
            sensorOrientation = orientation,
            maxResolution = Camera2Labels.maxResolution(size.width, size.height),
            hasFlash = flash,
            hasOpticalStabilization = ois,
            supportedCapabilities = Camera2Labels.capabilities(caps),
        )
    }

    private fun largestSize(chars: CameraCharacteristics): Size {
        val map = chars.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
        val sizes = map?.getOutputSizes(android.graphics.ImageFormat.JPEG).orEmpty()
        return sizes.maxByOrNull { it.width.toLong() * it.height.toLong() } ?: Size(0, 0)
    }
}
