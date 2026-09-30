package com.pixeldive.sdk

/**
 * Camera2 integer constants mapped to the Android-shaped JSON labels.
 * Values match `android.hardware.camera2.CameraCharacteristics` so the JVM
 * library can unit-test the mapping without the Android SDK.
 */
object Camera2Labels {
    /** Camera2 `LENS_FACING_FRONT`. */
    const val LENS_FACING_FRONT = 0

    /** Camera2 `LENS_FACING_BACK`. */
    const val LENS_FACING_BACK = 1

    /** Camera2 `LENS_FACING_EXTERNAL`. */
    const val LENS_FACING_EXTERNAL = 2

    /** Camera2 `INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED`. */
    const val HARDWARE_LEVEL_LIMITED = 0

    /** Camera2 `INFO_SUPPORTED_HARDWARE_LEVEL_FULL`. */
    const val HARDWARE_LEVEL_FULL = 1

    /** Camera2 `INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY`. */
    const val HARDWARE_LEVEL_LEGACY = 2

    /** Camera2 `INFO_SUPPORTED_HARDWARE_LEVEL_3`. */
    const val HARDWARE_LEVEL_3 = 3

    /** Camera2 `INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL`. */
    const val HARDWARE_LEVEL_EXTERNAL = 4

    /** Camera2 `REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE`. */
    const val CAPABILITY_BACKWARD_COMPATIBLE = 0

    /** Camera2 `REQUEST_AVAILABLE_CAPABILITIES_MANUAL_SENSOR`. */
    const val CAPABILITY_MANUAL_SENSOR = 1

    /** Camera2 `REQUEST_AVAILABLE_CAPABILITIES_MANUAL_POST_PROCESSING`. */
    const val CAPABILITY_MANUAL_POST_PROCESSING = 2

    /** Camera2 `REQUEST_AVAILABLE_CAPABILITIES_RAW`. */
    const val CAPABILITY_RAW = 3

    /** Map a Camera2 `LENS_FACING_*` int to `FRONT`, `BACK`, or `EXTERNAL`. */
    fun lensFacing(value: Int?): String =
        when (value) {
            LENS_FACING_FRONT -> "FRONT"
            LENS_FACING_BACK -> "BACK"
            LENS_FACING_EXTERNAL -> "EXTERNAL"
            else -> "EXTERNAL"
        }

    /** Map a Camera2 `INFO_SUPPORTED_HARDWARE_LEVEL_*` int to the wire label. */
    fun hardwareLevel(value: Int?): String =
        when (value) {
            HARDWARE_LEVEL_LIMITED -> "LIMITED"
            HARDWARE_LEVEL_FULL -> "FULL"
            HARDWARE_LEVEL_LEGACY -> "LEGACY"
            HARDWARE_LEVEL_3 -> "LEVEL_3"
            HARDWARE_LEVEL_EXTERNAL -> "EXTERNAL"
            else -> "LIMITED"
        }

    /** Map one Camera2 `REQUEST_AVAILABLE_CAPABILITIES_*` int to a wire label. */
    fun capability(value: Int): String =
        when (value) {
            CAPABILITY_BACKWARD_COMPATIBLE -> "BACKWARD_COMPATIBLE"
            CAPABILITY_MANUAL_SENSOR -> "MANUAL_SENSOR"
            CAPABILITY_MANUAL_POST_PROCESSING -> "MANUAL_POST_PROCESSING"
            CAPABILITY_RAW -> "RAW"
            else -> "CAPABILITY_$value"
        }

    /** Map a capability int array. Null becomes `BACKWARD_COMPATIBLE`. */
    fun capabilities(values: IntArray?): List<String> = values?.map(::capability) ?: listOf("BACKWARD_COMPATIBLE")

    /** Format Camera2 sensor width and height as `WIDTHxHEIGHT`. */
    fun maxResolution(
        width: Int,
        height: Int,
    ): String = "${width}x$height"
}
