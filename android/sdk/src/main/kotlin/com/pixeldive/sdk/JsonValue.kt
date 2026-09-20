package com.pixeldive.sdk

import kotlinx.serialization.KSerializer
import kotlinx.serialization.Serializable
import kotlinx.serialization.descriptors.PrimitiveKind
import kotlinx.serialization.descriptors.PrimitiveSerialDescriptor
import kotlinx.serialization.encoding.Decoder
import kotlinx.serialization.encoding.Encoder
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonDecoder
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonEncoder
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.longOrNull
import java.time.Instant
import java.util.UUID

/** JSON values stored on session/image `metadata` objects. */
@Serializable(with = JsonValueSerializer::class)
sealed class JsonValue {
    data class Str(val value: String) : JsonValue()

    data class IntNumber(val value: Long) : JsonValue()

    data class FloatNumber(val value: Double) : JsonValue()

    data class Bool(val value: Boolean) : JsonValue()

    data class Obj(val value: Map<String, JsonValue>) : JsonValue()

    data class Arr(val value: List<JsonValue>) : JsonValue()

    data object Null : JsonValue()

    companion object {
        /** String map used by sample payloads and demo metadata. */
        fun strings(values: Map<String, String>): Map<String, JsonValue> =
            values.mapValues { Str(it.value) }
    }
}

internal object JsonValueSerializer : KSerializer<JsonValue> {
    override val descriptor = PrimitiveSerialDescriptor("JsonValue", PrimitiveKind.STRING)

    override fun serialize(
        encoder: Encoder,
        value: JsonValue,
    ) {
        val json = encoder as JsonEncoder
        json.encodeJsonElement(value.toElement())
    }

    override fun deserialize(decoder: Decoder): JsonValue {
        val json = decoder as JsonDecoder
        return json.decodeJsonElement().toValue()
    }
}

internal fun JsonValue.toElement(): JsonElement =
    when (this) {
        is JsonValue.Str -> JsonPrimitive(value)
        is JsonValue.IntNumber -> JsonPrimitive(value)
        is JsonValue.FloatNumber -> JsonPrimitive(value)
        is JsonValue.Bool -> JsonPrimitive(value)
        is JsonValue.Obj -> JsonObject(value.mapValues { it.value.toElement() })
        is JsonValue.Arr -> JsonArray(value.map { it.toElement() })
        JsonValue.Null -> JsonNull
    }

internal fun JsonElement.toValue(): JsonValue =
    when (this) {
        is JsonNull -> JsonValue.Null
        is JsonObject -> JsonValue.Obj(mapValues { it.value.toValue() })
        is JsonArray -> JsonValue.Arr(map { it.toValue() })
        is JsonPrimitive -> primitiveValue()
    }

private fun JsonPrimitive.primitiveValue(): JsonValue {
    if (booleanOrNull != null && !isString) {
        return JsonValue.Bool(booleanOrNull!!)
    }
    val asLong = longOrNull
    if (asLong != null && !isString) {
        return JsonValue.IntNumber(asLong)
    }
    val asDouble = doubleOrNull
    if (asDouble != null && !isString) {
        return JsonValue.FloatNumber(asDouble)
    }
    return JsonValue.Str(content)
}

internal object UuidSerializer : KSerializer<UUID> {
    override val descriptor = PrimitiveSerialDescriptor("UUID", PrimitiveKind.STRING)

    override fun serialize(
        encoder: Encoder,
        value: UUID,
    ) {
        encoder.encodeString(value.toString())
    }

    override fun deserialize(decoder: Decoder): UUID = UUID.fromString(decoder.decodeString())
}

internal object InstantSerializer : KSerializer<Instant> {
    override val descriptor = PrimitiveSerialDescriptor("Instant", PrimitiveKind.STRING)

    override fun serialize(
        encoder: Encoder,
        value: Instant,
    ) {
        encoder.encodeString(value.toString())
    }

    override fun deserialize(decoder: Decoder): Instant = Instant.parse(decoder.decodeString())
}
