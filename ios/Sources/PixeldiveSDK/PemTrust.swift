import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

#if canImport(Security)
import Security
#endif

func normalizedPEM(_ pem: String?) -> String? {
    let trimmed = pem?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    if trimmed.isEmpty {
        return nil
    }
    return trimmed
}

func derCertificates(in pem: String) throws -> [Data] {
    let bodies = pemBodies(pem)
    if bodies.isEmpty {
        throw PixeldiveError.decoding("PEM CA bundle is empty")
    }
    return try bodies.map(decodePemBody)
}

func decodePemBody(_ body: String) throws -> Data {
    let filtered = body.filter { !$0.isWhitespace }
    guard let der = Data(base64Encoded: filtered), !der.isEmpty else {
        throw PixeldiveError.decoding("PEM CA is not valid base64")
    }
    return der
}

func pemBodies(_ pem: String) -> [String] {
    var bodies: [String] = []
    var current: [String] = []
    var inside = false
    for line in pem.split(whereSeparator: \.isNewline) {
        let text = line.trimmingCharacters(in: .whitespaces)
        inside = collectPemLine(text, inside: inside, current: &current, bodies: &bodies)
    }
    return bodies
}

func collectPemLine(
    _ line: String,
    inside: Bool,
    current: inout [String],
    bodies: inout [String]
) -> Bool {
    if line.contains("BEGIN CERTIFICATE") {
        current = []
        return true
    }
    if line.contains("END CERTIFICATE") {
        if inside {
            bodies.append(current.joined())
        }
        return false
    }
    if inside {
        current.append(line)
    }
    return inside
}

func sessionTrusting(
    _ ders: [Data],
    existing: URLSession?,
    timeout: TimeInterval
) throws -> URLSession {
    #if canImport(Security)
    return trustingSession(existing: existing, timeout: timeout, anchors: try secAnchors(ders))
    #else
    if ders.isEmpty {
        throw PixeldiveError.decoding("PEM CA bundle is empty")
    }
    return redirectSafeSession(existing: existing, timeout: timeout)
    #endif
}

#if canImport(Security)
func secAnchors(_ ders: [Data]) throws -> [SecCertificate] {
    if ders.isEmpty {
        throw PixeldiveError.decoding("PEM CA bundle is empty")
    }
    return try ders.map(secAnchor)
}

func secAnchor(_ der: Data) throws -> SecCertificate {
    guard let certificate = SecCertificateCreateWithData(nil, der as CFData) else {
        throw PixeldiveError.decoding("PEM CA is not an X.509 certificate")
    }
    return certificate
}

func evaluateServerTrust(_ trust: SecTrust, anchors: [SecCertificate]) -> Bool {
    SecTrustSetAnchorCertificates(trust, anchors as CFArray)
    SecTrustSetAnchorCertificatesOnly(trust, false)
    return SecTrustEvaluateWithError(trust, nil)
}

func credentialIfTrusted(_ trust: SecTrust, anchors: [SecCertificate]) -> URLCredential? {
    guard evaluateServerTrust(trust, anchors: anchors) else {
        return nil
    }
    return URLCredential(trust: trust)
}
#endif
