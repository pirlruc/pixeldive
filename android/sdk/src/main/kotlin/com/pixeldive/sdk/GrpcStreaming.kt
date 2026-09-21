package com.pixeldive.sdk

/** Byte transport for gRPC image RPCs. Tests inject a stub so JVM CI can skip h2c. */
interface GrpcStreaming {
    /** Client-stream protobuf messages and return the unary response payload. */
    suspend fun clientStreaming(
        path: String,
        messages: List<ByteArray>,
        token: String?,
    ): ByteArray

    /** Unary request then server-stream protobuf payloads. */
    suspend fun serverStreaming(
        path: String,
        request: ByteArray,
        token: String?,
    ): List<ByteArray>

    /** Release the underlying HTTP/2 client. Default is a no-op for test stubs. */
    fun close() {}
}
