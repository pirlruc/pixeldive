import Foundation

/// Byte transport for gRPC image RPCs. Tests inject a stub so Linux CI does not
/// need NIO HTTP/2 (h2c). Production on Apple uses ``NioGrpcStreaming``.
public protocol GrpcStreaming: Sendable {
    /// Client-stream protobuf messages and return the unary response payload.
    func clientStreaming(path: String, messages: [Data], token: String?) async throws -> Data
    /// Unary request then server-stream protobuf payloads.
    func serverStreaming(path: String, request: Data, token: String?) async throws -> [Data]
    /// Release the underlying channel. Default is a no-op for test stubs.
    func close()
}

public extension GrpcStreaming {
    /// Default no-op so test stubs do not manage a channel.
    func close() {}
}

/// gRPC status from trailers or the NIO status future.
public struct GrpcStatusError: Error, Sendable, Equatable {
    /// Status code from `grpc-status` (0 is OK).
    public var code: Int
    /// Optional `grpc-message`.
    public var message: String

    /// Bind a numeric status and message.
    public init(code: Int, message: String) {
        self.code = code
        self.message = message
    }
}

extension PixeldiveError {
    static func fromGrpc(_ error: GrpcStatusError) -> PixeldiveError {
        .transport("grpc-status \(error.code): \(error.message)")
    }
}
