#if canImport(GRPC)
import Foundation
import GRPC
import NIOCore

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

private final class PayloadBox: @unchecked Sendable {
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

    /// Open an insecure client connection to ``host``:``port``.
    public init(host: String, port: Int, timeoutMillis: Int64 = 20_000) {
        group = PlatformSupport.makeEventLoopGroup(loopCount: 1)
        connection = ClientConnection.insecure(group: group).connect(host: host, port: port)
        timeout = .milliseconds(timeoutMillis)
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
        let call: ClientStreamingCall<GrpcBytes, GrpcBytes> = connection.makeClientStreamingCall(
            path: path,
            callOptions: grpcOptions(token, timeout)
        )
        try await call.sendMessages(messages.map { GrpcBytes($0) }).get()
        try await call.sendEnd().get()
        try check(try await call.status.get())
        return try await call.response.get().data
    }

    public func serverStreaming(path: String, request: Data, token: String?) async throws -> [Data] {
        let box = PayloadBox()
        let call: ServerStreamingCall<GrpcBytes, GrpcBytes> = connection.makeServerStreamingCall(
            path: path,
            request: GrpcBytes(request),
            callOptions: grpcOptions(token, timeout)
        ) { message in
            box.append(message.data)
        }
        try check(try await call.status.get())
        return box.snapshot()
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

private func check(_ status: GRPCStatus) throws {
    if status.code == .ok {
        return
    }
    throw PixeldiveError.fromGrpc(
        GrpcStatusError(code: status.code.rawValue, message: status.message ?? "")
    )
}

public extension PixeldiveGrpcClient {
    /// Insecure h2c client for local/dev grpc.aio (`127.0.0.1:50051`).
    static func insecure(host: String, port: Int = 50051, token: String? = nil) -> PixeldiveGrpcClient {
        PixeldiveGrpcClient(stream: NioGrpcStreaming(host: host, port: port), token: token)
    }
}
#endif
