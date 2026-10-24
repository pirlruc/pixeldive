#if canImport(GRPC)
import Foundation
import GRPC
import NIOCore
import NIOSSL

struct GrpcBytes: GRPCPayload, Sendable {
    var data: Data

    init(_ data: Data) {
        self.data = data
    }

    init(serializedByteBuffer buffer: inout ByteBuffer) throws {
        data = Data(buffer.readBytes(length: buffer.readableBytes) ?? [])
    }

    func serialize(into buffer: inout ByteBuffer) throws {
        buffer.writeBytes(data)
    }
}

func roundTripGrpcBytes(_ data: Data) throws -> Data {
    var buffer = ByteBufferAllocator().buffer(capacity: max(data.count, 1))
    try GrpcBytes(data).serialize(into: &buffer)
    return try GrpcBytes(serializedByteBuffer: &buffer).data
}

final class PayloadBox: @unchecked Sendable {
    private let lock = NSLock()
    private var items: [Data] = []

    func append(_ data: Data) {
        lock.lock()
        items.append(data)
        lock.unlock()
    }

    func snapshot() -> [Data] {
        lock.lock()
        defer { lock.unlock() }
        return items
    }
}

/// NIO HTTP/2 h2c transport for ``PixeldiveGrpcClient`` (grpc.aio prior knowledge).
public final class NioGrpcStreaming: GrpcStreaming, @unchecked Sendable {
    private let group: EventLoopGroup
    private let connection: ClientConnection
    private let timeout: TimeAmount
    private let lock = NSLock()
    private var stopped = false

    private init(group: EventLoopGroup, connection: ClientConnection, timeoutMillis: Int64) {
        self.group = group
        self.connection = connection
        timeout = .milliseconds(timeoutMillis)
    }

    /// Open an insecure client connection to ``host``:``port``.
    public convenience init(host: String, port: Int, timeoutMillis: Int64 = 20_000) {
        let group = PlatformSupport.makeEventLoopGroup(loopCount: 1)
        let connection = ClientConnection.insecure(group: group).connect(host: host, port: port)
        self.init(group: group, connection: connection, timeoutMillis: timeoutMillis)
    }

    /// Open HTTP/2 with TLS and ALPN. `caPEM` is an optional extra PEM CA.
    /// Certificate verification stays enabled.
    public convenience init(
        tlsHost host: String,
        port: Int,
        caPEM: String? = nil,
        timeoutMillis: Int64 = 20_000
    ) throws {
        let group = PlatformSupport.makeEventLoopGroup(loopCount: 1)
        let tls: GRPCTLSConfiguration
        do {
            tls = try grpcTLS(caPEM)
        } catch {
            try? group.syncShutdownGracefully()
            throw error
        }
        let connection = ClientConnection.usingTLS(with: tls, on: group).connect(host: host, port: port)
        self.init(group: group, connection: connection, timeoutMillis: timeoutMillis)
    }

    /// Close the channel and event-loop group.
    public func close() {
        lock.lock()
        let already = stopped
        stopped = true
        lock.unlock()
        if already {
            return
        }
        _ = connection.close()
        try? group.syncShutdownGracefully()
    }

    deinit {
        close()
    }

    public func clientStreaming(path: String, messages: [Data], token: String?) async throws -> Data {
        try await grpcCall {
            let call: ClientStreamingCall<GrpcBytes, GrpcBytes> = connection.makeClientStreamingCall(
                path: path,
                callOptions: grpcOptions(token, timeout)
            )
            try await call.sendMessages(messages.map { GrpcBytes($0) }).get()
            try await call.sendEnd().get()
            try checkGrpcStatus(try await call.status.get())
            return try await call.response.get().data
        }
    }

    public func serverStreaming(path: String, request: Data, token: String?) async throws -> [Data] {
        try await grpcCall {
            let box = PayloadBox()
            let call: ServerStreamingCall<GrpcBytes, GrpcBytes> = connection.makeServerStreamingCall(
                path: path,
                request: GrpcBytes(request),
                callOptions: grpcOptions(token, timeout)
            ) { message in
                box.append(message.data)
            }
            try checkGrpcStatus(try await call.status.get())
            return box.snapshot()
        }
    }

    private func grpcCall<T>(_ body: () async throws -> T) async throws -> T {
        do {
            return try await body()
        } catch let error as PixeldiveError {
            throw error
        } catch {
            throw PixeldiveError.transport(String(describing: error))
        }
    }
}

private func grpcOptions(_ token: String?, _ timeout: TimeAmount) -> CallOptions {
    var options = CallOptions()
    options.timeLimit = .timeout(timeout)
    let trimmed = token?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    if !trimmed.isEmpty {
        options.customMetadata.add(name: "authorization", value: "Bearer \(trimmed)")
    }
    return options
}

func checkGrpcStatus(_ status: GRPCStatus) throws {
    if status.code == .ok {
        return
    }
    throw PixeldiveError.fromGrpc(
        GrpcStatusError(code: status.code.rawValue, message: status.message ?? "")
    )
}

func grpcTLS(_ caPEM: String?) throws -> GRPCTLSConfiguration {
    guard let pem = normalizedPEM(caPEM) else {
        return .makeClientConfigurationBackedByNIOSSL()
    }
    let certs = try nioCertificates(pem)
    var configuration = TLSConfiguration.makeClientConfiguration()
    configuration.minimumTLSVersion = .tlsv12
    configuration.certificateVerification = .fullVerification
    configuration.trustRoots = .default
    configuration.additionalTrustRoots = [.certificates(certs)]
    return .makeClientConfigurationBackedByNIOSSL(configuration: configuration)
}

func nioCertificates(_ pem: String) throws -> [NIOSSLCertificate] {
    let certs = try loadNIOCertificates(pem)
    if certs.isEmpty {
        throw PixeldiveError.decoding("PEM CA bundle is empty")
    }
    return certs
}

func loadNIOCertificates(_ pem: String) throws -> [NIOSSLCertificate] {
    do {
        return try NIOSSLCertificate.fromPEMBytes(Array(pem.utf8))
    } catch {
        throw PixeldiveError.decoding("PEM CA is not a certificate")
    }
}

public extension PixeldiveGrpcClient {
    /// Open HTTP/2 with TLS and ALPN.
    ///
    /// `caPEM` is an optional PEM CA trusted in addition to the platform roots.
    /// Certificate verification stays enabled. ``insecure(host:port:token:)`` remains the h2c helper.
    static func tls(
        host: String,
        port: Int = 443,
        token: String? = nil,
        caPEM: String? = nil
    ) throws -> PixeldiveGrpcClient {
        PixeldiveGrpcClient(
            stream: try NioGrpcStreaming(tlsHost: host, port: port, caPEM: caPEM),
            token: token
        )
    }

    /// Insecure h2c client for local/dev grpc.aio (`127.0.0.1:50051`).
    static func insecure(host: String, port: Int = 50051, token: String? = nil) -> PixeldiveGrpcClient {
        PixeldiveGrpcClient(stream: NioGrpcStreaming(host: host, port: port), token: token)
    }
}
#endif
