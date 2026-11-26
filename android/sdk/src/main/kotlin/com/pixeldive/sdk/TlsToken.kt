package com.pixeldive.sdk

import okhttp3.HttpUrl.Companion.toHttpUrl

internal fun requireTlsForToken(
    baseUrl: String,
    token: String?,
) {
    val trimmed = token?.trim().orEmpty()
    if (trimmed.isEmpty()) {
        return
    }
    val url = baseUrl.trimEnd('/').toHttpUrl()
    if (url.scheme == "https") {
        return
    }
    if (url.host == "localhost" || url.host == "127.0.0.1" || url.host == "::1") {
        return
    }
    throw IllegalArgumentException("a token requires TLS unless the host is loopback")
}

internal fun requireLoopbackForInsecureToken(
    host: String,
    token: String?,
) {
    val trimmed = token?.trim().orEmpty()
    if (trimmed.isEmpty()) {
        return
    }
    if (host == "localhost" || host == "127.0.0.1" || host == "::1") {
        return
    }
    throw IllegalArgumentException("a token requires TLS unless the host is loopback")
}
