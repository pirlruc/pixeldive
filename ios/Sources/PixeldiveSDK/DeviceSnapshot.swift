import Foundation

/// Android-shaped session payloads collected from iOS (or a sample iPhone).
public enum DeviceSnapshot {
    /// Bundled iPhone-like payload used by tests and the demo when live APIs are unavailable.
    public static func sampleiPhone(sessionName: String = "ios-demo-capture") -> SessionCreate {
        SessionCreate(
            sessionName: sessionName,
            phoneInfo: PhoneInfo(
                manufacturer: "Apple",
                model: "iPhone 16 Pro",
                brand: "apple",
                device: "iPhone17,1",
                board: "iPhone17,1",
                androidVersion: "18.6",
                sdkInt: 18
            ),
            phoneCapabilities: PhoneCapabilities(
                totalRamMb: 8192,
                availableRamMb: 4096,
                cpuAbi: "arm64",
                cpuCores: 6,
                screenWidthPx: 1206,
                screenHeightPx: 2622,
                screenDensityDpi: 460,
                isLowRamDevice: false
            ),
            cameraCapabilities: CameraCapabilities(cameras: [
                CameraInfo(
                    cameraId: "com.apple.avfoundation.avcapturedevice.built-in_video:0",
                    lensFacing: "BACK",
                    hardwareLevel: "LEVEL_3",
                    sensorOrientation: 90,
                    maxResolution: "4032x3024",
                    hasFlash: true,
                    hasOpticalStabilization: true,
                    supportedCapabilities: ["BACKWARD_COMPATIBLE", "RAW"]
                ),
                CameraInfo(
                    cameraId: "com.apple.avfoundation.avcapturedevice.built-in_video:1",
                    lensFacing: "FRONT",
                    hardwareLevel: "LIMITED",
                    sensorOrientation: 270,
                    maxResolution: "3088x2316",
                    hasFlash: false,
                    hasOpticalStabilization: false,
                    supportedCapabilities: ["BACKWARD_COMPATIBLE"]
                ),
            ]),
            metadata: JSONValue.strings([
                "source": "pixeldive-ios-sdk",
                "platform": "ios",
                "system_name": "iOS",
                "ios_version": "18.6",
            ])
        )
    }

    /// Live device mapping. UIKit/AVFoundation on iOS; ProcessInfo elsewhere.
    public static func current(sessionName: String = "ios-demo-capture") -> SessionCreate {
        LiveDevice.snapshot(sessionName: sessionName)
    }

    /// Decode the bundled fixture (same object as ``sampleiPhone()``).
    public static func bundledSample() throws -> SessionCreate {
        guard let url = Bundle.module.url(forResource: "sample_ios_session", withExtension: "json") else {
            throw PixeldiveError.decoding("missing sample_ios_session.json")
        }
        let data = try Data(contentsOf: url)
        return try JSONCodec.makeDecoder().decode(SessionCreate.self, from: data)
    }
}
