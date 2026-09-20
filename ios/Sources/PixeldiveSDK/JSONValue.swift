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
        if container.decodeNil() {
            self = .null
            return
        }
        if let value = try container.decodeIfPresent(Bool.self) {
            self = .bool(value)
            return
        }
        if let value = try container.decodeIfPresent(Int.self) {
            self = .int(value)
            return
        }
        if let value = try container.decodeIfPresent(Double.self) {
            self = .double(value)
            return
        }
        if let value = try container.decodeIfPresent(String.self) {
            self = .string(value)
            return
        }
        if let value = try container.decodeIfPresent([String: JSONValue].self) {
            self = .object(value)
            return
        }
        if let value = try container.decodeIfPresent([JSONValue].self) {
            self = .array(value)
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
