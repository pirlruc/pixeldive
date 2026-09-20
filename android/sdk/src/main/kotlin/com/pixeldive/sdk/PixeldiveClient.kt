package com.pixeldive.sdk

import okhttp3.OkHttpClient
import java.io.File

/** Thin OkHttp client for pixeldive `/api/v1` (REST; mirrors Python `RestClient`). */
class PixeldiveClient(
    baseUrl: String,
    token: String? = null,
    http: OkHttpClient = defaultHttp(),
) {
    private val transport = HttpTransport(baseUrl, token, http)

    /** GET `/health`. */
    suspend fun health(): HealthStatus = transport.json(HealthStatus.serializer(), "GET", "/health")

    /** GET `/ready`. */
    suspend fun ready(): HealthStatus = transport.json(HealthStatus.serializer(), "GET", "/ready")

    /** POST `/api/v1/sessions`. */
    suspend fun createSession(payload: SessionCreate): SessionRead =
        transport.json(
            SessionRead.serializer(),
            "POST",
            "/api/v1/sessions",
            encodeJson(SessionCreate.serializer(), payload),
        )

    /** GET `/api/v1/sessions`. */
    suspend fun listSessions(
        limit: Int = 50,
        cursor: String? = null,
    ): SessionPage =
        transport.json(
            SessionPage.serializer(),
            "GET",
            "/api/v1/sessions",
            query = pageQuery(limit, cursor),
        )

    /** GET `/api/v1/sessions/{id}`. */
    suspend fun getSession(id: String): SessionRead {
        val sessionId = ResourceId.parse(id)
        return transport.json(SessionRead.serializer(), "GET", "/api/v1/sessions/$sessionId")
    }

    /** PUT `/api/v1/sessions/{id}`. */
    suspend fun updateSession(
        id: String,
        payload: SessionUpdate,
    ): SessionRead {
        val sessionId = ResourceId.parse(id)
        return transport.json(
            SessionRead.serializer(),
            "PUT",
            "/api/v1/sessions/$sessionId",
            encodeJson(SessionUpdate.serializer(), payload),
        )
    }

    /** DELETE `/api/v1/sessions/{id}`. */
    suspend fun deleteSession(id: String) {
        val sessionId = ResourceId.parse(id)
        transport.empty("DELETE", "/api/v1/sessions/$sessionId")
    }

    /** POST multipart `/api/v1/sessions/{id}/images`. */
    suspend fun uploadImage(
        sessionId: String,
        filename: String,
        payload: ByteArray,
        contentType: String = "image/png",
        metadata: String? = null,
    ): SessionImage {
        val parsed = ResourceId.parse(sessionId)
        val fields = if (metadata != null) mapOf("metadata" to metadata) else emptyMap()
        val form = multipart("file", filename, payload, contentType, fields)
        return transport.upload(SessionImage.serializer(), "/api/v1/sessions/$parsed/images", form)
    }

    /** POST multipart `/api/v1/sessions/{id}/images/batch`. */
    suspend fun uploadImagesBatch(
        sessionId: String,
        items: List<Triple<String, ByteArray, String>>,
        metadata: String? = null,
    ): List<SessionImage> {
        val parsed = ResourceId.parse(sessionId)
        val fields = if (metadata != null) mapOf("metadata" to metadata) else emptyMap()
        val form = multipartBatch(items, fields)
        return transport.upload(
            kotlinx.serialization.builtins.ListSerializer(SessionImage.serializer()),
            "/api/v1/sessions/$parsed/images/batch",
            form,
        )
    }

    /** GET `/api/v1/sessions/{id}/images`. */
    suspend fun listImages(
        sessionId: String,
        limit: Int = 50,
        cursor: String? = null,
    ): ImagePage {
        val parsed = ResourceId.parse(sessionId)
        return transport.json(
            ImagePage.serializer(),
            "GET",
            "/api/v1/sessions/$parsed/images",
            query = pageQuery(limit, cursor),
        )
    }

    /** GET `/api/v1/sessions/{id}/images/{image_id}` as in-memory bytes. */
    suspend fun downloadImage(
        sessionId: String,
        imageId: String,
    ): ByteArray {
        val parsedSession = ResourceId.parse(sessionId)
        val parsedImage = ResourceId.parse(imageId)
        return transport.download("/api/v1/sessions/$parsedSession/images/$parsedImage")
    }

    /** POST multipart from a file without requiring the caller to buffer first. */
    suspend fun uploadImage(
        sessionId: String,
        file: File,
        filename: String? = null,
        contentType: String = "image/png",
        metadata: String? = null,
    ): SessionImage =
        uploadImage(
            sessionId = sessionId,
            filename = filename ?: file.name,
            payload = file.readBytes(),
            contentType = contentType,
            metadata = metadata,
        )
}
