package com.pixeldive.sdk

import okhttp3.OkHttpClient
import java.io.ByteArrayInputStream
import java.security.KeyStore
import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.util.Base64
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.TrustManagerFactory
import javax.net.ssl.X509TrustManager

internal fun httpClient(
    http: OkHttpClient,
    caPem: String?,
): OkHttpClient {
    val builder = http.newBuilder().followRedirects(false).followSslRedirects(false)
    return applyTrust(builder, caPem).build()
}

internal fun applyTrust(
    builder: OkHttpClient.Builder,
    caPem: String?,
): OkHttpClient.Builder {
    val pem = caPem?.trim().orEmpty()
    if (pem.isEmpty()) {
        return builder
    }
    val trust = MergedTrustManager(listOf(platformTrustManager(), trustManagerFor(pemCertificates(pem))))
    val context = SSLContext.getInstance("TLS")
    context.init(null, arrayOf<TrustManager>(trust), SecureRandom())
    builder.sslSocketFactory(context.socketFactory, trust)
    return builder
}

internal fun pemCertificates(pem: String): List<X509Certificate> {
    val bodies = pemBodies(pem)
    if (bodies.isEmpty()) {
        throw PixeldiveException.Decoding("PEM CA bundle is empty")
    }
    val factory = CertificateFactory.getInstance("X.509")
    return bodies.map { readCertificate(factory, it) }
}

internal fun pemBodies(pem: String): List<String> {
    val bodies = ArrayList<String>()
    val current = StringBuilder()
    var inside = false
    pem.lineSequence().forEach { line ->
        inside = collectPemLine(line.trim(), inside, current, bodies)
    }
    return bodies
}

private fun collectPemLine(
    line: String,
    inside: Boolean,
    current: StringBuilder,
    bodies: MutableList<String>,
): Boolean {
    if (line.contains("BEGIN CERTIFICATE")) {
        current.clear()
        return true
    }
    if (line.contains("END CERTIFICATE")) {
        if (inside) {
            bodies.add(current.toString())
        }
        current.clear()
        return false
    }
    if (inside) {
        current.append(line)
    }
    return inside
}

private fun readCertificate(
    factory: CertificateFactory,
    body: String,
): X509Certificate {
    try {
        val der = Base64.getMimeDecoder().decode(body)
        val cert = factory.generateCertificate(ByteArrayInputStream(der))
        if (cert is X509Certificate) {
            return cert
        }
    } catch (exc: IllegalArgumentException) {
        throw PixeldiveException.Decoding("PEM CA is not valid base64", exc)
    } catch (exc: CertificateException) {
        throw PixeldiveException.Decoding("PEM CA is not an X.509 certificate", exc)
    }
    throw PixeldiveException.Decoding("PEM CA is not an X.509 certificate")
}

internal fun platformTrustManager(): X509TrustManager = trustManagers(null).first()

internal fun trustManagerFor(certificates: List<X509Certificate>): X509TrustManager {
    val store = KeyStore.getInstance(KeyStore.getDefaultType())
    store.load(null, null)
    certificates.forEachIndexed { index, certificate ->
        store.setCertificateEntry("pem-$index", certificate)
    }
    return trustManagers(store).first()
}

private fun trustManagers(store: KeyStore?): List<X509TrustManager> {
    val factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm())
    factory.init(store)
    return factory.trustManagers.filterIsInstance<X509TrustManager>()
}

internal class MergedTrustManager(
    private val managers: List<X509TrustManager>,
) : X509TrustManager {
    override fun checkClientTrusted(
        chain: Array<X509Certificate>,
        authType: String,
    ) {
        check(chain, authType, server = false)
    }

    override fun checkServerTrusted(
        chain: Array<X509Certificate>,
        authType: String,
    ) {
        check(chain, authType, server = true)
    }

    override fun getAcceptedIssuers(): Array<X509Certificate> {
        val issuers = managers.flatMap { it.acceptedIssuers.toList() }
        return issuers.toTypedArray()
    }

    private fun check(
        chain: Array<X509Certificate>,
        authType: String,
        server: Boolean,
    ) {
        var last: CertificateException? = null
        for (manager in managers) {
            try {
                checkOne(manager, chain, authType, server)
                return
            } catch (exc: CertificateException) {
                last = exc
            }
        }
        throw last ?: CertificateException("certificate chain is not trusted")
    }

    private fun checkOne(
        manager: X509TrustManager,
        chain: Array<X509Certificate>,
        authType: String,
        server: Boolean,
    ) {
        if (server) {
            manager.checkServerTrusted(chain, authType)
        } else {
            manager.checkClientTrusted(chain, authType)
        }
    }
}
