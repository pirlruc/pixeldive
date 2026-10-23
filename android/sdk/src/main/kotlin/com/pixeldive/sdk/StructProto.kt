package com.pixeldive.sdk

internal fun decodeStruct(body: ByteArray): Map<String, JsonValue> {
    val reader = ProtoReader(body)
    val fields = LinkedHashMap<String, JsonValue>()
    while (true) {
        val next = reader.next() ?: return fields
        val entry = structEntry(next) ?: continue
        fields[entry.first] = entry.second
    }
}

private fun structEntry(next: Triple<Int, Int, ByteArray>): Pair<String, JsonValue>? {
    if (next.first != 1 || next.second != 2) {
        return null
    }
    return decodeMapEntry(next.third)
}

private fun decodeMapEntry(body: ByteArray): Pair<String, JsonValue>? {
    val reader = ProtoReader(body)
    var key: String? = null
    var value: JsonValue = JsonValue.Null
    while (true) {
        val next = reader.next() ?: break
        if (next.first == 1 && next.second == 2) {
            key = next.third.toString(Charsets.UTF_8)
        } else if (next.first == 2 && next.second == 2) {
            value = decodeValue(next.third)
        }
    }
    val resolved = key ?: return null
    return resolved to value
}

internal fun decodeValue(body: ByteArray): JsonValue {
    val next = ProtoReader(body).next() ?: return JsonValue.Null
    return valueKind(next.first, next.second, next.third)
}

private fun valueKind(
    field: Int,
    wire: Int,
    value: ByteArray,
): JsonValue =
    when (field) {
        1 -> JsonValue.Null
        2 -> if (wire == 1) jsonNumber(value) else JsonValue.Null
        3 -> JsonValue.Str(value.toString(Charsets.UTF_8))
        4 -> JsonValue.Bool(decodeVarint(value) != 0L)
        5 -> JsonValue.Obj(decodeStruct(value))
        6 -> JsonValue.Arr(decodeList(value))
        else -> JsonValue.Null
    }

private fun decodeList(body: ByteArray): List<JsonValue> {
    val reader = ProtoReader(body)
    val values = ArrayList<JsonValue>()
    while (true) {
        val next = reader.next() ?: return values
        if (next.first == 1 && next.second == 2) {
            values.add(decodeValue(next.third))
        }
    }
}

internal fun jsonNumber(raw: ByteArray): JsonValue {
    val number = Double.fromBits(littleEndianBits(raw))
    val integral = integralLong(number)
    return if (integral == null) JsonValue.FloatNumber(number) else JsonValue.IntNumber(integral)
}

internal fun littleEndianBits(raw: ByteArray): Long {
    var bits = 0L
    val count = minOf(raw.size, 8)
    for (index in 0 until count) {
        bits = bits or ((raw[index].toLong() and 0xFF) shl (8 * index))
    }
    return bits
}

internal fun integralLong(number: Double): Long? {
    if (!number.isFinite()) {
        return null
    }
    val asLong = number.toLong()
    if (asLong.toDouble() != number) {
        return null
    }
    return asLong
}
