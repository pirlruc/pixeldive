package com.pixeldive.sdk

import kotlinx.coroutines.runBlocking
import okhttp3.Headers
import okhttp3.Protocol
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.nio.file.Files
import java.nio.file.Path
import java.security.KeyStore
import java.security.SecureRandom
import java.security.cert.CertificateException
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext

class TlsTrustTest {
    private val sessionId = "123e4567-e89b-12d3-a456-426614174000"

    @Test
    fun pemParsingRejectsGarbage() {
        assertEquals(1, pemCertificates(OTHER_PEM).size)
        assertEquals(2, pemCertificates("$OTHER_PEM\n$OTHER_PEM").size)
        assertTrue(pemBodies("-----END CERTIFICATE-----").isEmpty())
        assertThrows<PixeldiveException.Decoding> { pemCertificates("nope") }
        assertThrows<PixeldiveException.Decoding> { pemCertificates(BAD_BASE64) }
        httpClient(defaultHttp(), null).dispatcher.executorService.shutdown()
        httpClient(defaultHttp(), "   ").dispatcher.executorService.shutdown()
        tlsGrpcClient(null).dispatcher.executorService.shutdown()
        tlsGrpcClient(OTHER_PEM).dispatcher.executorService.shutdown()
        assertThrows<PixeldiveException.Decoding> { PixeldiveGrpcClient.tls("localhost", 1, caPem = "nope") }
        PixeldiveGrpcClient.insecure("127.0.0.1", 1).close()
    }

    @Test
    fun httpBaseUrlWorksWithCustomCa() {
        val server = MockWebServer()
        server.enqueue(ok())
        server.start()
        try {
            runBlocking {
                val client = PixeldiveClient(server.url("/").toString(), caPem = OTHER_PEM)
                assertEquals("ok", client.health().status)
            }
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun httpsTrustsPemCaWithoutDisablingVerification() {
        val tls = localTls()
        val serverCerts = pemCertificates(tls.pem)
        val merged = MergedTrustManager(listOf(platformTrustManager(), trustManagerFor(serverCerts)))
        merged.checkServerTrusted(serverCerts.toTypedArray(), "RSA")
        merged.checkClientTrusted(serverCerts.toTypedArray(), "RSA")
        assertTrue(merged.acceptedIssuers.isNotEmpty())
        assertThrows<CertificateException> {
            merged.checkServerTrusted(pemCertificates(OTHER_PEM).toTypedArray(), "RSA")
        }
        val server = MockWebServer()
        server.useHttps(tls.context.socketFactory, false)
        server.enqueue(ok())
        server.start()
        try {
            val base = server.url("/").toString()
            runBlocking {
                assertEquals("ok", PixeldiveClient(base, caPem = tls.pem).health().status)
                assertThrows<PixeldiveException.Transport> {
                    runBlocking { PixeldiveClient(base).health() }
                }
                assertThrows<PixeldiveException.Transport> {
                    runBlocking { PixeldiveClient(base, caPem = OTHER_PEM).health() }
                }
            }
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun grpcTlsUsesHttpsAndInsecureRemains() {
        val tls = localTls()
        val server = MockWebServer()
        server.protocols = listOf(Protocol.HTTP_2, Protocol.HTTP_1_1)
        server.useHttps(tls.context.socketFactory, false)
        server.enqueue(grpcOk(UPLOAD.hexToBytes()))
        server.start()
        try {
            runBlocking {
                val client = PixeldiveGrpcClient.tls("localhost", server.port, token = "tok", caPem = tls.pem)
                val image = client.uploadImage(sessionId, "f.png", "hi".toByteArray())
                assertEquals("frame.png", image.filename)
                val recorded = server.takeRequest()
                assertEquals("https", recorded.requestUrl!!.scheme)
                assertEquals("Bearer tok", recorded.getHeader("Authorization"))
                client.close()
                assertThrows<PixeldiveException.Transport> {
                    runBlocking {
                        PixeldiveGrpcClient.tls("localhost", server.port).uploadImage(
                            sessionId,
                            "f.png",
                            byteArrayOf(1),
                        )
                    }
                }
            }
            PixeldiveGrpcClient.insecure("127.0.0.1", server.port).close()
        } finally {
            server.shutdown()
        }
    }

    private fun ok(): MockResponse = MockResponse().setBody("""{"status":"ok"}""")

    private fun grpcOk(payload: ByteArray): MockResponse =
        MockResponse()
            .setHeader("content-type", "application/grpc")
            .setTrailers(Headers.headersOf("grpc-status", "0"))
            .setBody(okio.Buffer().write(GrpcFrames.encode(payload)))

    private fun localTls(): MintedTls {
        val dir = Files.createTempDirectory("pixeldive-tls")
        try {
            return mint(dir)
        } finally {
            dir.toFile().deleteRecursively()
        }
    }

    private fun mint(dir: Path): MintedTls {
        val store = dir.resolve("server.p12")
        val pemFile = dir.resolve("ca.pem")
        val keytool = Path.of(System.getProperty("java.home"), "bin", "keytool").toString()
        keytool(
            keytool,
            "-genkeypair",
            "-alias",
            "localhost",
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "2",
            "-storetype",
            "PKCS12",
            "-keystore",
            store.toString(),
            "-storepass",
            "changeit",
            "-keypass",
            "changeit",
            "-dname",
            "CN=localhost",
            "-ext",
            "SAN=dns:localhost,ip:127.0.0.1",
        )
        keytool(
            keytool,
            "-exportcert",
            "-rfc",
            "-alias",
            "localhost",
            "-keystore",
            store.toString(),
            "-storepass",
            "changeit",
            "-file",
            pemFile.toString(),
        )
        val password = "changeit".toCharArray()
        val keyStore = KeyStore.getInstance("PKCS12")
        Files.newInputStream(store).use { keyStore.load(it, password) }
        val keys = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
        keys.init(keyStore, password)
        val context = SSLContext.getInstance("TLS")
        context.init(keys.keyManagers, null, SecureRandom())
        return MintedTls(context, Files.readString(pemFile))
    }

    private fun keytool(vararg args: String) {
        val process = ProcessBuilder(args.toList()).redirectErrorStream(true).start()
        val output = process.inputStream.readBytes().decodeToString()
        check(process.waitFor() == 0) { output }
    }
}

private class MintedTls(
    val context: SSLContext,
    val pem: String,
)

private fun String.hexToBytes(): ByteArray =
    ByteArray(length / 2) { index ->
        substring(index * 2, index * 2 + 2).toInt(16).toByte()
    }

private const val UPLOAD =
    "0a6c0a2431323365343536372d653839622d313264332d613435362d343236363134313734303031" +
        "122431323365343536372d653839622d313264332d613435362d343236363134313734303030" +
        "1a096672616d652e706e672209696d6167652f706e6728433a0608c095bfd506"

private const val BAD_BASE64 = "-----BEGIN CERTIFICATE-----\n!!!!\n-----END CERTIFICATE-----"

private const val OTHER_PEM = """
-----BEGIN CERTIFICATE-----
MIIDEzCCAfugAwIBAgIUVRcDRFIQRrcD+oL6j6c1pWHIDeowDQYJKoZIhvcNAQEL
BQAwGTEXMBUGA1UEAwwOcGl4ZWxkaXZlLXRlc3QwHhcNMjYxMDIzMTk1MDMxWhcN
MzYxMDIwMTk1MDMxWjAZMRcwFQYDVQQDDA5waXhlbGRpdmUtdGVzdDCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBAKRzFDW1uTRqxu0puSYPLHniqLEny73k
90IgwLDC+y0oHYh7UC57C1DPOIo+ERlfMt93SHuqRYIyRcchYSFXrbcEAOTA7E1S
IMocjR5l6M6pfy0muMQ4HQZsiFk4QSrUG3+0g2qO26vooIFmIXzbCs7PzLWxOU3a
E3pUZIXwmbz5qOGxsHipee5NoHSohqgmlEIG35UcdYDVp1k5tzl1i9RxePlnuYv2
UUDsYE7OeGvjt/OlhOfIJq2pYv3HDjmZ0DFvIm1n7j+z3J5hwSg5CUAwYJ77Jb+V
OqfUgDEKGoxvBUVL0kiHoznMlpbcAg37dH95VTbT7j4XOkoGZRpZWpUCAwEAAaNT
MFEwHQYDVR0OBBYEFB0Tik06G62pIdgIAdexb8S654q/MB8GA1UdIwQYMBaAFB0T
ik06G62pIdgIAdexb8S654q/MA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggEBAAALBNfkA3/WkG3eIpvuAlMipDDN+IGtKija0eO7s/PcZqUl6xoBWk3U
XvAQ5Royn/kCUjpTtNQumf60Pfq62U8i+rt2smdOQhyk67EW2fe2z6ttJSNeqbgv
M8HAQBvRlTaXzDfs+r5VhJsCoDiQAaenH1IkJSCDC76H/ndQfwB7EEZzhM7D2+4Q
LulFxCIM1wBkQNw18CJiAlpBdWIYZQ8XTtZnoRxtKGhBOvBH30gyaqTRvoSe3Noi
UaB1ztnKiLyI8q/FOaXMt0rKfs2/GZ/6DernYkgm4koIVCijpiK0pMMQ9v1i2xSM
vnwjgFjPGA/2hVSKt7c3S92HNW7a6dA=
-----END CERTIFICATE-----
"""
