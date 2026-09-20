package com.pixeldive.sdk

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.DeserializationStrategy
import kotlinx.serialization.SerializationStrategy
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

internal class HttpTransport(
    baseUrl: String,
    private val token: String?,
    private val http: OkHttpClient,
) {
    private val base: HttpUrl = baseUrl.trimEnd('/').toHttpUrl()

    suspend fun <T> json(
        deserializer: DeserializationStrategy<T>,
        method: String,
        path: String,
        payload: ByteArray? = null,
        query: Map<String, String> = emptyMap(),
    ): T {
        val body = payload?.toRequestBody("application/json".toMediaType())
        return decode(deserializer, send(method, path, body, query))
    }

    suspend fun empty(
        method: String,
        path: String,
    ) {
        send(method, path, body = null)
    }

    suspend fun <T> upload(
        deserializer: DeserializationStrategy<T>,
        path: String,
        body: MultipartBody,
    ): T = decode(deserializer, send("POST", path, body))

    suspend fun download(path: String): ByteArray = send("GET", path, body = null)

    private suspend fun send(
        method: String,
        path: String,
        body: RequestBody?,
        query: Map<String, String> = emptyMap(),
    ): ByteArray {
        val builder = Request.Builder().url(url(path, query))
        val trimmed = token?.trim().orEmpty()
        if (trimmed.isNotEmpty()) {
            builder.header("Authorization", "Bearer $trimmed")
        }
        when (method) {
            "GET" -> builder.get()
            "DELETE" -> builder.delete()
            else -> builder.method(method, body ?: ByteArray(0).toRequestBody(null))
        }
        return execute(builder.build())
    }

    private fun url(
        path: String,
        query: Map<String, String>,
    ): HttpUrl {
        // Keep any prefix on the configured base (httpx/iOS concatenate; OkHttp resolve() would drop it).
        val builder = base.newBuilder()
        path.trim('/').split('/').forEach { builder.addPathSegment(it) }
        query.forEach { (key, value) -> builder.addQueryParameter(key, value) }
        return builder.build()
    }

    private suspend fun execute(request: Request): ByteArray =
        withContext(Dispatchers.IO) {
            val call = http.newCall(request)
            try {
                awaitResponse(call).use { response ->
                    val bytes = checkNotNull(response.body).bytes()
                    if (response.code !in 200..299) {
                        throw PixeldiveException.HttpStatus(response.code, clippedUtf8(bytes))
                    }
                    bytes
                }
            } catch (exc: PixeldiveException) {
                throw exc
            } catch (exc: Exception) {
                throw PixeldiveException.Transport(exc.toString(), exc)
            }
        }

    private suspend fun awaitResponse(call: Call): Response =
        suspendCancellableCoroutine { continuation ->
            continuation.invokeOnCancellation { call.cancel() }
            call.enqueue(
                object : Callback {
                    override fun onFailure(
                        call: Call,
                        e: IOException,
                    ) {
                        continuation.resumeWithException(e)
                    }

                    override fun onResponse(
                        call: Call,
                        response: Response,
                    ) {
                        continuation.resume(response) { _, value, _ -> value.close() }
                    }
                },
            )
        }

    private fun <T> decode(
        deserializer: DeserializationStrategy<T>,
        bytes: ByteArray,
    ): T =
        try {
            JsonCodec.json.decodeFromString(deserializer, bytes.toString(Charsets.UTF_8))
        } catch (exc: Exception) {
            throw PixeldiveException.Decoding(exc.toString(), exc)
        }
}

internal fun <T> encodeJson(
    serializer: SerializationStrategy<T>,
    value: T,
): ByteArray = JsonCodec.json.encodeToString(serializer, value).toByteArray(Charsets.UTF_8)

internal fun pageQuery(
    limit: Int,
    cursor: String?,
): Map<String, String> {
    val query = mutableMapOf("limit" to limit.toString())
    if (!cursor.isNullOrEmpty()) {
        query["cursor"] = cursor
    }
    return query
}

internal fun defaultHttp(timeoutSeconds: Long = 60): OkHttpClient =
    OkHttpClient.Builder()
        .connectTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .readTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .writeTimeout(timeoutSeconds, TimeUnit.SECONDS)
        .followRedirects(false)
        .followSslRedirects(false)
        .build()

private val FILENAME_BREAKERS = setOf('"', '\\', ';', ':', '\r', '\n', '\u0000')
private val MEDIA_TYPE_EXTRA = setOf('/', '+', '-', '.')
private const val ERROR_BODY_LIMIT = 2048

/** Strip path separators and header-breaking characters from multipart filenames. */
internal fun sanitizeMultipartFilename(filename: String): String {
    val base = filename.substringAfterLast('/').substringAfterLast('\\')
    val cleaned = base.map { char -> if (char in FILENAME_BREAKERS) '_' else char }.joinToString("")
    return cleaned.ifBlank { "upload.bin" }
}

/** Allow only RFC 6838 type/subtype tokens in multipart Content-Type. */
internal fun sanitizeMultipartType(type: String): String {
    val firstLine = type.substringBefore('\r').substringBefore('\n').substringBefore(';')
    val cleaned = firstLine.filter { it.isLetterOrDigit() || it in MEDIA_TYPE_EXTRA }
    return if (cleaned.contains('/')) cleaned else "application/octet-stream"
}

internal fun clippedUtf8(bytes: ByteArray): String {
    val slice = if (bytes.size > ERROR_BODY_LIMIT) bytes.copyOf(ERROR_BODY_LIMIT) else bytes
    return slice.toString(Charsets.UTF_8)
}

internal fun metadataFields(metadata: String?): Map<String, String> {
    return if (metadata != null) mapOf("metadata" to metadata) else emptyMap()
}

internal fun appendFields(
    builder: MultipartBody.Builder,
    fields: Map<String, String>,
) {
    fields.toSortedMap().forEach { (name, value) -> builder.addFormDataPart(name, value) }
}

internal fun multipart(
    fileField: String,
    filename: String,
    body: RequestBody,
    fields: Map<String, String>,
): MultipartBody {
    val builder = MultipartBody.Builder().setType(MultipartBody.FORM)
    builder.addFormDataPart(fileField, sanitizeMultipartFilename(filename), body)
    appendFields(builder, fields)
    return builder.build()
}

internal fun multipart(
    fileField: String,
    filename: String,
    payload: ByteArray,
    contentType: String,
    fields: Map<String, String>,
): MultipartBody =
    multipart(
        fileField,
        filename,
        payload.toRequestBody(sanitizeMultipartType(contentType).toMediaType()),
        fields,
    )

internal fun multipartBatch(
    items: List<Triple<String, ByteArray, String>>,
    fields: Map<String, String>,
): MultipartBody {
    val builder = MultipartBody.Builder().setType(MultipartBody.FORM)
    items.forEach { (filename, payload, contentType) ->
        builder.addFormDataPart(
            "files",
            sanitizeMultipartFilename(filename),
            payload.toRequestBody(sanitizeMultipartType(contentType).toMediaType()),
        )
    }
    appendFields(builder, fields)
    return builder.build()
}
