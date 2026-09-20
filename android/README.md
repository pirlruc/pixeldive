# pixeldive Android SDK

First-party Kotlin client for the pixeldive session service. The public REST surface
matches Python `pixeldive_sdk.RestClient` and Swift `PixeldiveClient`.
`PixeldiveGrpcClient` matches `GrpcClient` (OkHttp `H2_PRIOR_KNOWLEDGE` h2c). Session
JSON uses the Android wire keys (`phone_info`, `phone_capabilities`,
`camera_capabilities`) so iOS and Android clients share one backend contract.

| Piece | Path |
|-------|------|
| Kotlin JVM library | `android/sdk` (`com.pixeldive.sdk`) |
| Demo app | `android/demo` (included when `ANDROID_HOME` is set) |
| Fixture | `android/sdk/src/main/resources/sample_android_session.json` |

Payload shape follows Android `Build` / Camera2 keys documented on
`app/device_models.py`. The JVM library maps those keys without depending on the
Android Gradle Plugin. The Compose demo implements `DeviceProbe` with `Build`,
`ActivityManager`, `DisplayMetrics`, and Camera2, tagged `metadata.platform=android`.

## Requirements (KT-*)

- JDK 21 (KT-BUILD-001)
- Gradle wrapper in `android/`
- Android SDK only for the Compose demo (KT-ENV-001 proposal). GitHub-hosted
  Ubuntu sets `ANDROID_HOME`; the demo module is **not** included from that.
  Open `android/` in Android Studio (writes `local.properties`) or set
  `PIXELDIVE_INCLUDE_ANDROID_DEMO=1`.
- JVM unit tests run with `./gradlew :sdk:test` on Linux

## SDK usage

```kotlin
import com.pixeldive.sdk.DeviceSnapshot
import com.pixeldive.sdk.PixeldiveClient
import com.pixeldive.sdk.PixeldiveGrpcClient

val client = PixeldiveClient(baseUrl = "http://127.0.0.1:8000", token = null)
val session = client.createSession(DeviceSnapshot.current())
val image = client.uploadImage(
    sessionId = session.id.toString(),
    filename = "frame.png",
    payload = pngBytes,
)
val bytes = client.downloadImage(session.id.toString(), image.id.toString())

val grpc = PixeldiveGrpcClient.insecure(host = "127.0.0.1", port = 50051)
val streamed = grpc.uploadImage(
    sessionId = session.id.toString(),
    filename = "frame.jpg",
    payload = jpegBytes,
    contentType = "image/jpeg",
)
```

`DeviceSnapshot.samplePixel()` is the fixture used in tests. `DeviceSnapshot.current()`
uses `JvmDeviceProbe` on the JVM and `AndroidDeviceProbe` in the demo.

Bearer tokens stay in memory on `PixeldiveClient` (KT-SEC-005 proposal). The demo
does not write them to `SharedPreferences`.

## Demo app

1. Run the session service (`python3 main.py` or Compose).
2. Open `android/` in Android Studio (creates `local.properties`) or set
   `PIXELDIVE_INCLUDE_ANDROID_DEMO=1`.
3. Run `:demo` on an emulator or device (emulator REST `http://10.0.2.2:8000`,
   gRPC `10.0.2.2:50051`).
4. Create a session, start the camera feed (or pick a photo). Frames upload over gRPC.

Local HTTP uses `networkSecurityConfig` domain exceptions only (KT-AND-001
proposal). Camera and photo permissions/rationale are in the demo manifest
(KT-AND-002 proposal).

## Tests

```bash
# Linux JVM (KT-TEST-001)
bash android/gradlew -p android :sdk:test

# Android-shaped fixture against the Python service (Linux CI)
bash scripts/ci-local.sh
```

Coverage floor: `config/kotlin.profile.thresholds.yml` (KT-TEST-002). CI job
`android-sdk` runs on Ubuntu with JDK 21. Compose assemble is skipped unless
`local.properties` exists or `PIXELDIVE_INCLUDE_ANDROID_DEMO=1` (do not use
`ANDROID_HOME` — GitHub runners set it).
