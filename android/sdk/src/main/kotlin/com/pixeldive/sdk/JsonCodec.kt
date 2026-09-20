package com.pixeldive.sdk

import kotlinx.serialization.json.Json
import kotlinx.serialization.modules.SerializersModule

internal object JsonCodec {
    val json: Json =
        Json {
            ignoreUnknownKeys = true
            encodeDefaults = true
            serializersModule = SerializersModule {}
        }
}
