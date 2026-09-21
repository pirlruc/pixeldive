import Foundation

enum ProtoWire {
    static func tag(_ field: Int, wire: UInt8) -> Data {
        varint(UInt64(field << 3 | Int(wire)))
    }

    static func varint(_ value: UInt64) -> Data {
        var data = Data()
        var current = value
        repeat {
            var byte = UInt8(current & 0x7F)
            current >>= 7
            if current != 0 {
                byte |= 0x80
            }
            data.append(byte)
        } while current != 0
        return data
    }

    static func stringField(_ field: Int, _ value: String) -> Data {
        bytesField(field, Data(value.utf8))
    }

    static func bytesField(_ field: Int, _ value: Data) -> Data {
        var data = tag(field, wire: 2)
        data.append(varint(UInt64(value.count)))
        data.append(value)
        return data
    }

    static func varintField(_ field: Int, _ value: UInt64) -> Data {
        var data = tag(field, wire: 0)
        data.append(varint(value))
        return data
    }

    static func boolField(_ field: Int, _ value: Bool) -> Data {
        value ? varintField(field, 1) : Data()
    }
}

struct ProtoField {
    var number: Int
    var wire: UInt8
    var value: Data
}

struct ProtoReader {
    let bytes: Data
    var offset = 0

    mutating func next() throws -> ProtoField? {
        if offset >= bytes.count {
            return nil
        }
        let key = try readVarint()
        let field = Int(key >> 3)
        let wire = UInt8(key & 0x7)
        switch wire {
        case 0:
            let start = offset
            _ = try readVarint()
            return ProtoField(number: field, wire: wire, value: bytes.subdata(in: start..<offset))
        case 1:
            return ProtoField(number: field, wire: wire, value: try read(8))
        case 2:
            let length = Int(try readVarint())
            return ProtoField(number: field, wire: wire, value: try read(length))
        case 5:
            return ProtoField(number: field, wire: wire, value: try read(4))
        default:
            throw PixeldiveError.decoding("unsupported protobuf wire type \(wire)")
        }
    }

    mutating func readVarint() throws -> UInt64 {
        var result: UInt64 = 0
        var shift = 0
        while true {
            if offset >= bytes.count {
                throw PixeldiveError.decoding("truncated protobuf varint")
            }
            let byte = bytes[offset]
            offset += 1
            result |= UInt64(byte & 0x7F) << shift
            if byte & 0x80 == 0 {
                return result
            }
            shift += 7
            if shift > 63 {
                throw PixeldiveError.decoding("protobuf varint overflow")
            }
        }
    }

    mutating func read(_ count: Int) throws -> Data {
        let end = offset + count
        if count < 0 || end > bytes.count {
            throw PixeldiveError.decoding("truncated protobuf field")
        }
        let slice = bytes.subdata(in: offset..<end)
        offset = end
        return slice
    }
}

func decodeVarint(_ data: Data) throws -> UInt64 {
    var reader = ProtoReader(bytes: data)
    return try reader.readVarint()
}
