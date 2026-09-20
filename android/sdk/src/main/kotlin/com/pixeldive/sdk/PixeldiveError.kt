package com.pixeldive.sdk

/** Errors raised by [PixeldiveClient] without echoing secrets. */
sealed class PixeldiveException(
    message: String,
    cause: Throwable? = null,
) : Exception(message, cause) {
    /** A path id was not a UUID (blocks `../` injection into URLs). */
    class InvalidResourceId(val value: String) : PixeldiveException("Invalid resource id: $value")

    /** The service returned a non-success HTTP status. */
    class HttpStatus(val code: Int, val body: String) : PixeldiveException("HTTP $code: $body")

    /** JSON encoding or decoding failed. */
    class Decoding(detail: String, cause: Throwable? = null) :
        PixeldiveException("Decoding failed: $detail", cause)

    /** The OkHttp transport failed. */
    class Transport(detail: String, cause: Throwable? = null) :
        PixeldiveException("Transport failed: $detail", cause)
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
