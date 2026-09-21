package com.pixeldive.sdk

internal object ProtoWire {
    fun tag(
        field: Int,
        wire: Int,
    ): ByteArray = varint((field shl 3 or wire).toLong())

    fun varint(value: Long): ByteArray {
        val out = ArrayList<Byte>(10)
        var current = value
        while (true) {
            if (current and 0x7FL.inv() == 0L) {
                out.add(current.toByte())
                return out.toByteArray()
            }
            out.add(((current and 0x7F) or 0x80).toByte())
            current = current ushr 7
        }
    }

    fun stringField(
        field: Int,
        value: String,
    ): ByteArray = bytesField(field, value.toByteArray(Charsets.UTF_8))

    fun bytesField(
        field: Int,
        value: ByteArray,
    ): ByteArray = tag(field, 2) + varint(value.size.toLong()) + value

    fun varintField(
        field: Int,
        value: Long,
    ): ByteArray = tag(field, 0) + varint(value)

    fun boolField(
        field: Int,
        value: Boolean,
    ): ByteArray = if (value) varintField(field, 1) else ByteArray(0)
}

internal class ProtoReader(
    private val bytes: ByteArray,
) {
    var offset = 0
        private set

    fun next(): Triple<Int, Int, ByteArray>? {
        if (offset >= bytes.size) {
            return null
        }
        val key = readVarint()
        val field = (key ushr 3).toInt()
        val wire = (key and 0x7).toInt()
        return Triple(field, wire, readWire(wire))
    }

    fun readVarint(): Long {
        var result = 0L
        var shift = 0
        while (true) {
            if (offset >= bytes.size) {
                throw PixeldiveException.Decoding("truncated protobuf varint")
            }
            val byte = bytes[offset].toInt() and 0xFF
            offset += 1
            result = result or ((byte and 0x7F).toLong() shl shift)
            if (byte and 0x80 == 0) {
                return result
            }
            shift += 7
            if (shift > 63) {
                throw PixeldiveException.Decoding("protobuf varint overflow")
            }
        }
    }

    private fun readWire(wire: Int): ByteArray =
        when (wire) {
            0 -> {
                val start = offset
                readVarint()
                bytes.copyOfRange(start, offset)
            }
            1 -> read(8)
            2 -> read(readVarint().toInt())
            5 -> read(4)
            else -> throw PixeldiveException.Decoding("unsupported protobuf wire type $wire")
        }

    private fun read(count: Int): ByteArray {
        val end = offset + count
        if (count < 0 || end > bytes.size) {
            throw PixeldiveException.Decoding("truncated protobuf field")
        }
        val slice = bytes.copyOfRange(offset, end)
        offset = end
        return slice
    }
}

internal fun decodeVarint(data: ByteArray): Long = ProtoReader(data).readVarint()
