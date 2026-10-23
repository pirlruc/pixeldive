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
        .package(url: "https://github.com/apple/swift-nio.git", from: "2.100.0"),
        .package(url: "https://github.com/apple/swift-nio-ssl.git", from: "2.23.0"),
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
                .product(
                    name: "NIOSSL",
                    package: "swift-nio-ssl",
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
