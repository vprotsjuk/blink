// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "BlinkSwiftUI",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "BlinkSwiftUI", targets: ["BlinkSwiftUI"])
    ],
    targets: [
        .target(name: "BlinkSwiftUICore"),
        .executableTarget(name: "BlinkSwiftUI", dependencies: ["BlinkSwiftUICore"]),
        .executableTarget(name: "BlinkSwiftUITestRunner", dependencies: ["BlinkSwiftUICore"], path: "Tests/BlinkSwiftUITestRunner")
    ]
)
