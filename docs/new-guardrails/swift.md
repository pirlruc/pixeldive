# Proposed Swift guardrails (pixeldive → org)

Proposals for [pirlruc/guardrails](https://github.com/pirlruc/guardrails) after adding a
Swift 6 iOS SDK against pin **1.6.0**. These are **not** in-repo deviations. The Swift
pack already exists (`swift/`); several Kotlin/Android rules have no Swift twin.

Companion: [README.md](README.md), analog
[swift/guardrails.md](https://github.com/pirlruc/guardrails/blob/1.6.0/swift/guardrails.md)
and [kotlin/guardrails.md](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md).

pixeldive consumes Swift gates from `config/swift.profile.thresholds.yml`. Extra keys
(`max_cyclomatic_complexity`) are **stricter local policy** until the analog grows them.

## New IDs to add (from Kotlin / Android)

### SWIFT-CPLX-001 — Cyclomatic complexity

Kotlin [KT-CPLX-001](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md)
gates `CyclomaticComplexMethod`. SwiftLint already emits `cyclomatic_complexity`.
Add a numeric `max_cyclomatic_complexity` key (org default **10**, same as Kotlin 1.6.0).
Do not invent a Swift average-CC ratio; SwiftLint is per-function.

**Why here:** `ios/.swiftlint.yml` already fails at 10 so the SDK cannot grow
unreviewable request helpers.

### SWIFT-CPLX-002 — Size / cognitive rules SwiftLint actually emits

Kotlin [KT-CPLX-002](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md)
uses detekt `LongMethod` / `CognitiveComplexMethod` and explicitly rejects a Python-style
maintainability index. Mirror that: require SwiftLint `function_body_length`,
`type_body_length`, and `file_length`. Do **not** add `min_maintainability_index`.

**Why here:** splitting files to please a fake MI would duplicate URLSession wrappers
the same way PY-CPLX-003 warns about.

### SWIFT-CONC-001 — Structured concurrency

Kotlin [KT-CONC-001](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md)
requires `coroutineScope` / `async` / `withContext` and forbids global scopes.
Swift equivalent: `async`/`await` and task groups; no fire-and-forget `Task { }` in
library code without an owner (the demo UI may start tasks from button handlers).

Distinct from [SWIFT-API-003](https://github.com/pirlruc/guardrails/blob/1.6.0/swift/guardrails.md)
(concurrency *model changes* need notes).

**Why here:** `PixeldiveClient` is `Sendable` and has no unstructured tasks.

### SWIFT-CONC-002 — Isolation is explicit

Kotlin [KT-CONC-002](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md)
requires suspend APIs to document dispatcher behavior. Swift: Swift 6 complete
concurrency (`SWIFT_STRICT_CONCURRENCY=complete` / `swiftLanguageModes: [.v6]`).
`@MainActor` on UI types; the SDK stays off the main actor.

**Why here:** the demo model is `@MainActor`; the package is not.

### SWIFT-API-004 — Value-type Codable models for wire payloads

Kotlin [KT-API-001](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/guardrails.md)
prefers immutable `data class` models. Swift: `struct` + `Codable` + `let` (or
`var` only where mutation is part of the snapshot builder). No `[String: Any]` on
the public session API.

**Why here:** `PhoneInfo` / `SessionCreate` are structs matching Android JSON keys.

### SWIFT-IOS-003 — App Transport Security

Cleartext HTTP is forbidden except an explicit local-network exception for debug
talking to loopback (`NSAllowsLocalNetworking`). Do not set
`NSAllowsArbitraryLoads`. Distinct from SWIFT-SEC-*.

**Why here:** the demo Info.plist allows local networking only so Xcode can hit
`http://127.0.0.1:8000`.

### SWIFT-IOS-004 — Privacy usage strings for capture

When a client or demo reads the camera or photo library, `Info.plist` must carry
`NSCameraUsageDescription` / `NSPhotoLibraryUsageDescription` (and Photo Library
Add if it saves). Analog: Android `AndroidManifest` camera permission + rationale.

**Why here:** the demo uploads a user-picked photo.

### SWIFT-SEC-005 — Tokens stay out of UserDefaults

API bearer tokens must not be written to `UserDefaults`, plists, or logs.
Prefer Keychain when persistence is required; otherwise keep them in memory on the
client (pixeldive demo). Android analog: do not store tokens in `SharedPreferences`
in plaintext (Kotlin pack does not yet spell this; propose there too if desired).

**Why here:** `PixeldiveClient` holds an in-memory token; the demo uses `SecureField`
and never persists it.

## Changes to existing IDs

### SWIFT-ENV-001 — macOS for UIKit/Xcode; Linux SPM allowed for Foundation-only

The 1.6.0 rule requires macOS for **all** local and CI build/test gates. That blocks
Linux-hosted Python services that also ship a Foundation URLSession client.

Change to: **UIKit, SwiftUI, and `xcodebuild` remain macOS.** A Foundation-only SPM
library may use `swift test` on Linux (host Swift or a digest-pinned `swift:` image).
Coverage still uses llvm-cov line coverage (SWIFT-TEST-002 already rejects branch %).

**Why here:** pixeldive CI is Ubuntu for PY-*; the iOS SDK package has no UIKit in
the library target. Demo/`xcodebuild` stays on the `ios-sdk` macOS job. Linux
`URLSession` is libcurl-backed and does not honor `URLProtocol`, so package tests
inject an `HTTPPerforming` stub instead of relying on protocol classes.

### SWIFT-TEST-002 — Library modules may be stricter than 90

Org line coverage is 90. Kotlin [KT-TEST-002](https://github.com/pirlruc/guardrails/blob/1.6.0/kotlin/profile.thresholds.yml)
is 95. Allow (and document) a consumer overlay of 95 for SPM libraries. Keep 90 as
the org floor so UIKit apps are not forced onto an unmeasurable bar.

pixeldive `config/swift.profile.thresholds.yml` uses **95** (stricter; no deviation).

Document `swift test --enable-code-coverage` plus `llvm-cov report` as an accepted
evaluator for Foundation-only SPM libraries. The profile names Xcode coverage +
`xcresultparser`; that remains the UIKit/`xcodebuild test` path. llvm-cov is the
same metric SWIFT-TEST-002 already describes. On Linux, `llvm-cov` lives next to
`swift` in the toolchain `usr/bin` (not necessarily on `PATH`); CI must resolve
it from the `swift` binary rather than assume `xcrun`.

### SWIFT-DOC-001 — public `///` ratio until sourcekitten is org tooling

The analog requires `doc_coverage` but does not name a tool. Until the org pins
SourceKitten/Jazzy, a fail-closed scan of public types/functions for a preceding
`///` is an accepted evaluator (pixeldive: `scripts/check-swift-docs.py`).

### SWIFT-LINT-001 — SwiftLint complexity rules are part of the lint gate

Name `cyclomatic_complexity` (and the SWIFT-CPLX-002 size rules) in `swift/profile.md`
next to SwiftFormat, so consumers do not treat complexity as optional extra config.

Checksum-pinned portable SwiftLint (not a system `brew install`) is an accepted
CI installer for mixed Python+Swift repos.

### SWIFT-SEC-003 — `p/swift` is an accepted semgrep config

The profile already names `semgrep`. Document `p/swift` as the org config for iOS
sources, alongside `p/python` for mixed repos.

### SWIFT-SEC-004 — Trivy filesystem scan is an accepted dependency scanner

The analog names `osv-scanner` or `grype`. Trivy `fs` on the Swift package (HIGH/
CRITICAL, fail closed) is the same class of gate and is already SHA-pinned in
this repo's Python image job. Document it as an accepted evaluator so mixed repos
do not grow a third scanner.

## Do not add

- A Swift `branch_coverage` key. SWIFT-TEST-002 already explains llvm-cov/Xcode do
  not emit branch coverage (unlike Kover on Kotlin).
- A Swift maintainability-index number. Same rationale as KT-CPLX-002.
- A requirement to run the SwiftUI demo in Linux CI.
