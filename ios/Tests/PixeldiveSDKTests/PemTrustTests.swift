import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
#if canImport(Security)
import Security
#endif
@testable import PixeldiveSDK
import XCTest

final class PemTrustTests: XCTestCase {
    func testPemParsingAndClientInit() throws {
        let ders = try derCertificates(in: fixtureCaPEM)
        XCTAssertEqual(ders.count, 1)
        XCTAssertEqual(pemBodies(fixtureCaPEM + "\n" + fixtureCaPEM).count, 2)
        XCTAssertTrue(pemBodies("-----END CERTIFICATE-----").isEmpty)
        XCTAssertNil(normalizedPEM("  "))
        XCTAssertThrowsError(try derCertificates(in: "nope"))
        XCTAssertThrowsError(try derCertificates(in: "-----BEGIN CERTIFICATE-----\n!!!!\n-----END CERTIFICATE-----"))
        let base = URL(string: "http://127.0.0.1:9")!
        _ = try PixeldiveClient(baseURL: base, caPEM: fixtureCaPEM)
        XCTAssertThrowsError(try PixeldiveClient(baseURL: base, caPEM: "nope"))
    }

    func testTrustEvaluationUsesAnchors() throws {
        #if canImport(Security)
        let anchors = try secAnchors(try derCertificates(in: fixtureCaPEM))
        let policy = SecPolicyCreateBasicX509()
        var trust: SecTrust?
        XCTAssertEqual(SecTrustCreateWithCertificates(anchors[0], policy, &trust), errSecSuccess)
        let created = try XCTUnwrap(trust)
        XCTAssertTrue(evaluateServerTrust(created, anchors: anchors))
        XCTAssertNotNil(credentialIfTrusted(created, anchors: anchors))
        XCTAssertFalse(evaluateServerTrust(created, anchors: []))
        XCTAssertNil(credentialIfTrusted(created, anchors: []))
        let space = URLProtectionSpace(
            host: "localhost",
            port: 443,
            protocol: "https",
            realm: nil,
            authenticationMethod: NSURLAuthenticationMethodServerTrust
        )
        XCTAssertEqual(trustDecision(space, anchors: anchors).disposition, .performDefaultHandling)
        XCTAssertEqual(trustDecision(space, anchors: []).disposition, .performDefaultHandling)
        XCTAssertNil(serverTrust(space))
        #endif
    }
}

let fixtureCaPEM = """
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
