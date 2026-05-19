// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "JarvisApple",
    platforms: [
        .iOS(.v18),
        .macOS(.v15),
        .tvOS(.v18),
        .watchOS(.v11),
    ],
    products: [
        .library(name: "JarvisKit", targets: ["JarvisKit"]),
        .library(name: "JarvisKitHealth", targets: ["JarvisKitHealth"]),
        .library(name: "JarvisKitIntents", targets: ["JarvisKitIntents"]),
        .library(name: "JarvisNotifications", targets: ["JarvisNotifications"]),
    ],
    targets: [
        .target(
            name: "JarvisKit",
            path: "Sources/JarvisKit"
        ),
        .target(
            name: "JarvisKitHealth",
            dependencies: ["JarvisKit"],
            path: "Sources/JarvisKitHealth"
        ),
        .target(
            name: "JarvisKitIntents",
            dependencies: ["JarvisKit"],
            path: "Sources/JarvisKitIntents"
        ),
        .target(
            name: "JarvisNotifications",
            dependencies: ["JarvisKit"],
            path: "Sources/JarvisNotifications"
        ),
        .testTarget(
            name: "JarvisKitTests",
            dependencies: ["JarvisKit", "JarvisKitHealth"],
            path: "Tests/JarvisKitTests"
        ),
    ]
)
