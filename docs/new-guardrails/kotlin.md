# Proposed Kotlin / Android guardrails (pixeldive → org)

Proposals for [pirlruc/guardrails](https://github.com/pirlruc/guardrails) after adding a
Kotlin JVM Android SDK against pin **1.6.0**. These are **not** in-repo deviations. The
Kotlin pack already exists (`kotlin/`); Android-specific twins of the Swift iOS rules
added with SDK-002 are still missing.

Companion: [README.md](README.md), analog
[kotlin/guardrails.md](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md)
and [swift/guardrails.md](https://github.com/pirlruc/guardrails/blob/1.6.0/swift/guardrails.md).

pixeldive consumes Kotlin gates from `config/kotlin.profile.thresholds.yml` (same
numbers as analog 1.6.0: 95/95 line+branch, max CC 10).

## New IDs to add (from Swift / Android)

### KT-AND-001 — Network security config, not global cleartext

Swift [SWIFT-IOS-003](swift.md) forbids `NSAllowsArbitraryLoads` and allows only a
loopback exception. Android equivalent: do **not** set
`android:usesCleartextTraffic="true"` on `<application>`. Debug talk to the emulator
host (`10.0.2.2`) or loopback belongs in `networkSecurityConfig` domain exceptions.

**Why here:** the Compose demo permits cleartext only for `10.0.2.2` / `127.0.0.1` /
`localhost` so it can hit a local pixeldive without opening the whole device.

### KT-AND-002 — Capture permissions and rationale

When a client or demo reads the camera or photo picker, `AndroidManifest` must declare
`CAMERA` / `READ_MEDIA_IMAGES` (as applicable) and the UI must carry a rationale
string. Analog: iOS `NSCameraUsageDescription` / `NSPhotoLibraryUsageDescription`.
The JVM library module must not request those permissions — only the app.

**Why here:** `AndroidDeviceProbe` reads Camera2 characteristics; the demo uploads a
user-picked photo.

### KT-SEC-005 — Tokens stay out of SharedPreferences

API bearer tokens must not be written to `SharedPreferences`, MMKV, or logs in
plaintext. Prefer EncryptedSharedPreferences / Keystore when persistence is required;
otherwise keep them in memory (pixeldive demo). Twin of [SWIFT-SEC-005](swift.md).

**Why here:** `PixeldiveClient` holds an in-memory token; the demo password field
never persists it.

### KT-ENV-001 — Linux JVM tests; emulator/Compose host-only

Kotlin [KT-BUILD-001](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md)
does not say where Gradle may run. A Foundation-only Swift overlay is proposed as
SWIFT-ENV-001. Mirror that: **`:sdk` JVM unit tests may run on Linux** (host JDK or a
digest-pinned `eclipse-temurin:21` image). Compose UI, `connectedAndroidTest`, and
emulator remain host/macOS/Android CI. Coverage still uses Kover line+branch
(KT-TEST-002).

**Why here:** pixeldive CI is Ubuntu for PY-*; the Android SDK library has no
`com.android.library` dependency. The demo is included only when `ANDROID_HOME` is
set.

## Changes to existing IDs

### KT-SEC-002 — `p/kotlin` is an accepted semgrep config

The profile already names `semgrep`. Document `p/kotlin` as the org config for
Android/JVM sources, alongside `p/python` / `p/swift` for mixed repos.

### KT-BUILD-001 — JDK 21 is an accepted LTS pin

The rule asks consumers to define a Kotlin/JDK target. Document **JDK 21** as an
accepted org LTS (current Temurin CI image) so mixed Python+Kotlin repos are not
forced onto JDK 17 by folklore.

## Do not add

- A Kotlin `doc_coverage` key. KT-DOC-001 already explains no org tool emits a
  documentation-coverage ratio.
- A Kotlin maintainability-index number. KT-CPLX-002 already rejects it.
- A requirement to assemble the Compose demo in Linux CI without `ANDROID_HOME`.
