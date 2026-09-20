import Foundation

/// JSON values stored on session/image `metadata` objects.
public enum JSONValue: Sendable, Equatable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null
}

extension JSONValue: Codable {
    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let value = decodeJSON(container) {
            self = value
            return
        }
        throw DecodingError.dataCorruptedError(in: container, debugDescription: "unsupported JSON")
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case let .string(value):
            try container.encode(value)
        case let .int(value):
            try container.encode(value)
        case let .double(value):
            try container.encode(value)
        case let .bool(value):
            try container.encode(value)
        case let .object(value):
            try container.encode(value)
        case let .array(value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        }
    }
}

extension JSONValue {
    /// String map used by sample payloads and demo metadata.
    public static func strings(_ values: [String: String]) -> [String: JSONValue] {
        values.mapValues(JSONValue.string)
    }
}

private func decodeJSON(_ container: SingleValueDecodingContainer) -> JSONValue? {
    if container.decodeNil() {
        return .null
    }
    if let value = try? container.decode(Bool.self) {
        return .bool(value)
    }
    if let value = try? container.decode(Int.self) {
        return .int(value)
    }
    if let value = try? container.decode(Double.self) {
        return .double(value)
    }
    if let value = try? container.decode(String.self) {
        return .string(value)
    }
    if let value = try? container.decode([String: JSONValue].self) {
        return .object(value)
    }
    if let value = try? container.decode([JSONValue].self) {
        return .array(value)
    }
    return nil
}
