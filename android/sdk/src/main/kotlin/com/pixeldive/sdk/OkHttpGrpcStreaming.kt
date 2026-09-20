package com.pixeldive.sdk

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Headers
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.Response
import java.util.concurrent.TimeUnit

/** OkHttp HTTP/2 prior-knowledge (h2c) transport for [PixeldiveGrpcClient]. */
class OkHttpGrpcStreaming(
    host: String,
    port: Int,
    private val http: OkHttpClient = h2cClient(),
) : GrpcStreaming {
    private val root: HttpUrl =
        HttpUrl.Builder().scheme("http").host(host).port(port).build()

    override suspend fun clientStreaming(
        path: String,
        messages: List<ByteArray>,
        token: String?,
    ): ByteArray {
        val frames = GrpcFrames.messages(execute(path, token, GrpcFrames.body(messages)))
        return firstMessage(frames)
    }

    override suspend fun serverStreaming(
        path: String,
        request: ByteArray,
        token: String?,
    ): List<ByteArray> = GrpcFrames.messages(execute(path, token, GrpcFrames.body(listOf(request))))

    private suspend fun execute(
        path: String,
        token: String?,
        body: RequestBody,
    ): ByteArray =
        withContext(Dispatchers.IO) {
            try {
                http.newCall(grpcRequest(path, token, body)).awaitResponse().use { finish(it) }
            } catch (exc: PixeldiveException) {
                throw exc
            } catch (exc: Exception) {
                throw PixeldiveException.Transport(exc.toString(), exc)
            }
        }

    private fun grpcRequest(
        path: String,
        token: String?,
        body: RequestBody,
    ): Request {
        val builder =
            Request.Builder()
                .url(url(path))
                .header("content-type", "application/grpc")
                .header("te", "trailers")
                .header("grpc-accept-encoding", "identity")
                .post(body)
        val trimmed = token?.trim().orEmpty()
        if (trimmed.isNotEmpty()) {
            builder.header("Authorization", "Bearer $trimmed")
        }
        return builder.build()
    }

    private fun url(path: String): HttpUrl {
        val builder = root.newBuilder()
        path.trim('/').split('/').forEach { builder.addPathSegment(it) }
        return builder.build()
    }
}

internal fun h2cClient(timeoutSeconds: Long = 60): OkHttpClient =
    OkHttpClient.Builder()
        .protocols(listOf(Protocol.H2_PRIOR_KNOWLEDGE))
        .connectTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .readTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .writeTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .followRedirects(false)
        .followSslRedirects(false)
        .build()

internal fun finish(response: Response): ByteArray {
    val bytes = response.body?.bytes() ?: ByteArray(0)
    if (!response.isSuccessful) {
        throw PixeldiveException.Transport("HTTP ${response.code}")
    }
    val status = grpcStatus(response.headers, response.trailers())
    if (status.first != 0) {
        throw PixeldiveException.GrpcStatus(status.first, status.second)
    }
    return bytes
}

internal fun firstMessage(frames: List<ByteArray>): ByteArray = frames.firstOrNull() ?: ByteArray(0)

internal fun grpcStatus(
    headers: Headers,
    trailers: Headers,
): Pair<Int, String> {
    val code =
        headers["grpc-status"]?.toIntOrNull()
            ?: trailers["grpc-status"]?.toIntOrNull()
            ?: 2
    val message = headers["grpc-message"] ?: trailers["grpc-message"] ?: ""
    return code to message
}
