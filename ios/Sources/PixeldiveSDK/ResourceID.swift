import Foundation

/// Validate identifiers used in HTTP paths (Python SDK `resource_id`).
public enum ResourceID {
    /// Return a canonical UUID string, rejecting path-injection payloads.
    public static func parse(_ value: String) throws -> String {
        guard let parsed = UUID(uuidString: value) else {
            throw PixeldiveError.invalidResourceID(value)
        }
        return parsed.uuidString.lowercased()
    }

    /// Canonical lowercase UUID string.
    public static func parse(_ value: UUID) -> String {
        value.uuidString.lowercased()
    }
}
