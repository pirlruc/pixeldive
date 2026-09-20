package com.pixeldive.sdk

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.DeserializationStrategy
import kotlinx.serialization.SerializationStrategy
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

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
    ): ByteArray =
        withContext(Dispatchers.IO) {
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
            execute(builder.build())
        }

    private fun url(
        path: String,
        query: Map<String, String>,
    ): HttpUrl {
        val relative = if (path.startsWith("/")) path else "/$path"
        val resolved = base.resolve(relative) ?: throw PixeldiveException.Transport("invalid request URL")
        if (query.isEmpty()) {
            return resolved
        }
        val builder = resolved.newBuilder()
        query.forEach { (key, value) -> builder.addQueryParameter(key, value) }
        return builder.build()
    }

    private fun execute(request: Request): ByteArray {
        try {
            http.newCall(request).execute().use { response ->
                val bytes = response.body?.bytes() ?: ByteArray(0)
                if (response.code >= 400) {
                    throw PixeldiveException.HttpStatus(response.code, bytes.toString(Charsets.UTF_8))
                }
                return bytes
            }
        } catch (exc: PixeldiveException) {
            throw exc
        } catch (exc: Exception) {
            throw PixeldiveException.Transport(exc.message ?: exc.toString())
        }
    }

    private fun <T> decode(
        deserializer: DeserializationStrategy<T>,
        bytes: ByteArray,
    ): T =
        try {
            JsonCodec.json.decodeFromString(deserializer, bytes.toString(Charsets.UTF_8))
        } catch (exc: PixeldiveException) {
            throw exc
        } catch (exc: Exception) {
            throw PixeldiveException.Decoding(exc.message ?: exc.toString())
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
        .build()

internal fun multipart(
    fileField: String,
    filename: String,
    payload: ByteArray,
    contentType: String,
    fields: Map<String, String>,
): MultipartBody {
    val builder = MultipartBody.Builder().setType(MultipartBody.FORM)
    builder.addFormDataPart(
        fileField,
        filename,
        payload.toRequestBody(contentType.toMediaType()),
    )
    fields.toSortedMap().forEach { (name, value) -> builder.addFormDataPart(name, value) }
    return builder.build()
}

internal fun multipartBatch(
    items: List<Triple<String, ByteArray, String>>,
    fields: Map<String, String>,
): MultipartBody {
    val builder = MultipartBody.Builder().setType(MultipartBody.FORM)
    items.forEach { (filename, payload, contentType) ->
        builder.addFormDataPart(
            "files",
            filename,
            payload.toRequestBody(contentType.toMediaType()),
        )
    }
    fields.toSortedMap().forEach { (name, value) -> builder.addFormDataPart(name, value) }
    return builder.build()
}
