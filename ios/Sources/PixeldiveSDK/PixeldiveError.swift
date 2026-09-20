import Foundation

/// Errors raised by ``PixeldiveClient`` without echoing secrets.
public enum PixeldiveError: Error, Sendable, Equatable {
    /// A path id was not a UUID (blocks `../` injection into URLs).
    case invalidResourceID(String)
    /// The service returned a non-success HTTP status.
    case httpStatus(Int, body: String)
    /// JSON encoding or decoding failed.
    case decoding(String)
    /// The URLSession transport failed.
    case transport(String)
}

extension PixeldiveError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case let .invalidResourceID(value):
            return "Invalid resource id: \(value)"
        case let .httpStatus(code, body):
            return "HTTP \(code): \(body)"
        case let .decoding(detail):
            return "Decoding failed: \(detail)"
        case let .transport(detail):
            return "Transport failed: \(detail)"
        }
    }
}
