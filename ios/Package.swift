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
    dependencies: [
        .package(url: "https://github.com/grpc/grpc-swift.git", exact: "1.24.2"),
    ],
    targets: [
        .target(
            name: "PixeldiveSDK",
            dependencies: [
                .product(
                    name: "GRPC",
                    package: "grpc-swift",
                    condition: .when(platforms: [.macOS, .iOS, .tvOS, .watchOS])
                ),
            ],
            resources: [.copy("Fixtures/sample_ios_session.json")]
        ),
        .testTarget(
            name: "PixeldiveSDKTests",
            dependencies: [
                "PixeldiveSDK",
                .product(
                    name: "GRPC",
                    package: "grpc-swift",
                    condition: .when(platforms: [.macOS, .iOS, .tvOS, .watchOS])
                ),
            ]
        ),
    ],
    swiftLanguageModes: [.v6]
)
