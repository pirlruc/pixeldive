// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PixeldiveSDK",
    platforms: [
        .iOS(.v15),
        .macOS(.v13),
    ],
    products: [
        .library(name: "PixeldiveSDK", targets: ["PixeldiveSDK"]),
    ],
    targets: [
        .target(
            name: "PixeldiveSDK",
            resources: [.copy("Fixtures/sample_ios_session.json")]
        ),
        .testTarget(
            name: "PixeldiveSDKTests",
            dependencies: ["PixeldiveSDK"]
        ),
    ],
    swiftLanguageModes: [.v6]
)
