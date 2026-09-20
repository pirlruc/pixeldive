package com.pixeldive.sdk

/** Errors raised by [PixeldiveClient] without echoing secrets. */
sealed class PixeldiveException(
    message: String,
) : Exception(message) {
    /** A path id was not a UUID (blocks `../` injection into URLs). */
    class InvalidResourceId(val value: String) : PixeldiveException("Invalid resource id: $value")

    /** The service returned a non-success HTTP status. */
    class HttpStatus(val code: Int, val body: String) : PixeldiveException("HTTP $code: $body")

    /** JSON encoding or decoding failed. */
    class Decoding(detail: String) : PixeldiveException("Decoding failed: $detail")

    /** The OkHttp transport failed. */
    class Transport(detail: String) : PixeldiveException("Transport failed: $detail")
}

/** Validate identifiers used in HTTP paths (Python SDK `resource_id`). */
object ResourceId {
    /** Return a canonical UUID string, rejecting path-injection payloads. */
    fun parse(value: String): String =
        try {
            java.util.UUID.fromString(value).toString()
        } catch (_: IllegalArgumentException) {
            throw PixeldiveException.InvalidResourceId(value)
        }
}
