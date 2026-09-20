package com.pixeldive.sdk

/**
 * Camera2 integer constants mapped to the Android-shaped JSON labels.
 * Values match `android.hardware.camera2.CameraCharacteristics` so the JVM
 * library can unit-test the mapping without the Android SDK.
 */
object Camera2Labels {
    const val LENS_FACING_FRONT = 0
    const val LENS_FACING_BACK = 1
    const val LENS_FACING_EXTERNAL = 2

    const val HARDWARE_LEVEL_LIMITED = 0
    const val HARDWARE_LEVEL_FULL = 1
    const val HARDWARE_LEVEL_LEGACY = 2
    const val HARDWARE_LEVEL_3 = 3
    const val HARDWARE_LEVEL_EXTERNAL = 4

    const val CAPABILITY_BACKWARD_COMPATIBLE = 0
    const val CAPABILITY_MANUAL_SENSOR = 1
    const val CAPABILITY_MANUAL_POST_PROCESSING = 2
    const val CAPABILITY_RAW = 3

    fun lensFacing(value: Int?): String =
        when (value) {
            LENS_FACING_FRONT -> "FRONT"
            LENS_FACING_BACK -> "BACK"
            LENS_FACING_EXTERNAL -> "EXTERNAL"
            else -> "EXTERNAL"
        }

    fun hardwareLevel(value: Int?): String =
        when (value) {
            HARDWARE_LEVEL_LIMITED -> "LIMITED"
            HARDWARE_LEVEL_FULL -> "FULL"
            HARDWARE_LEVEL_LEGACY -> "LEGACY"
            HARDWARE_LEVEL_3 -> "LEVEL_3"
            HARDWARE_LEVEL_EXTERNAL -> "EXTERNAL"
            else -> "LIMITED"
        }

    fun capability(value: Int): String =
        when (value) {
            CAPABILITY_BACKWARD_COMPATIBLE -> "BACKWARD_COMPATIBLE"
            CAPABILITY_MANUAL_SENSOR -> "MANUAL_SENSOR"
            CAPABILITY_MANUAL_POST_PROCESSING -> "MANUAL_POST_PROCESSING"
            CAPABILITY_RAW -> "RAW"
            else -> "CAPABILITY_$value"
        }

    fun capabilities(values: IntArray?): List<String> = values?.map(::capability) ?: listOf("BACKWARD_COMPATIBLE")

    fun maxResolution(
        width: Int,
        height: Int,
    ): String = "${width}x$height"
}
