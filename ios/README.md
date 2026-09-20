# pixeldive iOS SDK

First-party Swift client for the pixeldive session service. The public REST surface
matches Python `pixeldive_sdk.RestClient`. Session JSON keeps the Android wire keys
(`phone_info`, `phone_capabilities`, `camera_capabilities`) so iOS and Android
clients share one backend contract.

| Piece | Path |
|-------|------|
| Swift package | `ios/` (`PixeldiveSDK`) |
| Demo app | `ios/Demo/PixeldiveDemo.xcodeproj` |
| Fixture | `ios/Sources/PixeldiveSDK/Fixtures/sample_ios_session.json` |

There is a first-party Android Kotlin SDK in `android/`. Payload shape follows
Android `Build` / Camera2 keys documented on `app/device_models.py`. iOS maps
`UIDevice`, `ProcessInfo`, and `AVCaptureDevice` into those keys; native iOS
fields live under `metadata.platform=ios`.

## Requirements (SWIFT-*)

- Swift 6, SPM (SWIFT-LANG-001/003)
- iOS 15.0+ (SWIFT-IOS-001)
- Xcode for the demo app (SWIFT-ENV-001, SWIFT-LANG-002)
- Foundation-only package tests can run with `swift test` on macOS (and Linux Swift)

## SDK usage

```swift
import PixeldiveSDK

let client = PixeldiveClient(
    baseURL: URL(string: "http://127.0.0.1:8000")!,
    token: nil
)
let session = try await client.createSession(DeviceSnapshot.current())
let image = try await client.uploadImage(
    sessionID: session.id.uuidString,
    filename: "frame.png",
    payload: pngData
)
let bytes = try await client.downloadImage(
    sessionID: session.id.uuidString,
    imageID: image.id.uuidString
)
```

`DeviceSnapshot.sampleiPhone()` is the fixture used in tests. `DeviceSnapshot.current()`
reads the live device on iOS.

Bearer tokens stay in memory on `PixeldiveClient` (SWIFT-SEC-005 proposal). The demo
does not write them to `UserDefaults`.

## Demo app

1. Run the session service (`python3 main.py` or Compose).
2. Open `ios/Demo/PixeldiveDemo.xcodeproj` in Xcode (or `project.yml` via XcodeGen).
3. Run on a simulator or device.
4. Confirm the base URL, create a session, pick a photo, upload, download.

Local HTTP uses `NSAllowsLocalNetworking` only (SWIFT-IOS-003 proposal). Camera and
photo usage strings are in `Info.plist` (SWIFT-IOS-004 proposal).

## Tests

```bash
# macOS (SWIFT-TEST-001), or Linux Swift for the Foundation package
swift test --package-path ios

# Android-shaped fixture against the Python service (Linux CI)
bash scripts/ci-local.sh
```

Coverage floor: `config/swift.profile.thresholds.yml` (SWIFT-TEST-002). CI job `ios-sdk`
runs on macOS. Linux `scripts/ci-local.sh` does not claim Swift gates (SWIFT-ENV-001).
