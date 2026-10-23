import Foundation

func decodeStruct(_ body: Data) throws -> [String: JSONValue] {
    var reader = ProtoReader(bytes: body)
    var fields: [String: JSONValue] = [:]
    while let next = try reader.next() {
        if let entry = try structEntry(next) {
            fields[entry.0] = entry.1
        }
    }
    return fields
}

func structEntry(_ field: ProtoField) throws -> (String, JSONValue)? {
    guard field.number == 1, field.wire == 2 else {
        return nil
    }
    return try decodeMapEntry(field.value)
}

func decodeMapEntry(_ body: Data) throws -> (String, JSONValue)? {
    var reader = ProtoReader(bytes: body)
    var key: String?
    var value = JSONValue.null
    while let next = try reader.next() {
        if next.number == 1, next.wire == 2 {
            key = String(data: next.value, encoding: .utf8) ?? ""
        } else if next.number == 2, next.wire == 2 {
            value = try decodeValue(next.value)
        }
    }
    guard let key else {
        return nil
    }
    return (key, value)
}

func decodeValue(_ body: Data) throws -> JSONValue {
    var reader = ProtoReader(bytes: body)
    guard let next = try reader.next() else {
        return .null
    }
    return try valueKind(next)
}

func valueKind(_ field: ProtoField) throws -> JSONValue {
    switch field.number {
    case 1:
        return .null
    case 2:
        return field.wire == 1 ? jsonNumber(field.value) : .null
    case 3:
        return .string(String(data: field.value, encoding: .utf8) ?? "")
    case 4:
        return .bool(try decodeVarint(field.value) != 0)
    case 5:
        return .object(try decodeStruct(field.value))
    case 6:
        return .array(try decodeList(field.value))
    default:
        return .null
    }
}

func decodeList(_ body: Data) throws -> [JSONValue] {
    var reader = ProtoReader(bytes: body)
    var values: [JSONValue] = []
    while let next = try reader.next() {
        if next.number == 1, next.wire == 2 {
            values.append(try decodeValue(next.value))
        }
    }
    return values
}

func jsonNumber(_ data: Data) -> JSONValue {
    let number = decodeDouble(data)
    if let integral = integralInt(number) {
        return .int(integral)
    }
    return .double(number)
}

func decodeDouble(_ data: Data) -> Double {
    var bits: UInt64 = 0
    for (index, byte) in data.prefix(8).enumerated() {
        bits |= UInt64(byte) << (index * 8)
    }
    return Double(bitPattern: bits)
}

func integralInt(_ number: Double) -> Int? {
    guard number.isFinite else {
        return nil
    }
    let integral = number.rounded()
    guard integral == number else {
        return nil
    }
    return Int(exactly: integral)
}
