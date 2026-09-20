import Foundation

#if os(iOS)
import AVFoundation
import CoreMedia
import UIKit
#endif

enum LiveDevice {
    static func snapshot(sessionName: String) -> SessionCreate {
        #if os(iOS)
        return iosSnapshot(sessionName: sessionName)
        #else
        return processSnapshot(sessionName: sessionName)
        #endif
    }
}

#if os(iOS)
private func iosSnapshot(sessionName: String) -> SessionCreate {
    let device = UIDevice.current
    let version = device.systemVersion
    let machine = hardwareMachine()
    let screen = UIScreen.main.bounds
    let scale = UIScreen.main.scale
    let ramBytes = ProcessInfo.processInfo.physicalMemory
    let ramMb = Int(ramBytes / 1_048_576)
    return SessionCreate(
        sessionName: sessionName,
        phoneInfo: PhoneInfo(
            manufacturer: "Apple",
            model: device.model,
            brand: "apple",
            device: machine,
            board: machine,
            androidVersion: version,
            sdkInt: majorVersion(version)
        ),
        phoneCapabilities: PhoneCapabilities(
            totalRamMb: ramMb,
            availableRamMb: ramMb / 2,
            cpuAbi: "arm64",
            cpuCores: ProcessInfo.processInfo.processorCount,
            screenWidthPx: Int(screen.width * scale),
            screenHeightPx: Int(screen.height * scale),
            screenDensityDpi: Int(160 * scale),
            isLowRamDevice: ramMb < 2048
        ),
        cameraCapabilities: CameraCapabilities(cameras: liveCameras()),
        metadata: JSONValue.strings([
            "source": "pixeldive-ios-sdk",
            "platform": "ios",
            "system_name": device.systemName,
            "ios_version": version,
        ])
    )
}

private func liveCameras() -> [CameraInfo] {
    let session = AVCaptureDevice.DiscoverySession(
        deviceTypes: [
            .builtInWideAngleCamera,
            .builtInUltraWideCamera,
            .builtInTelephotoCamera,
        ],
        mediaType: .video,
        position: .unspecified
    )
    let mapped = session.devices.enumerated().map { offset, device in
        cameraInfo(device, fallbackID: String(offset))
    }
    return mapped
}

private func cameraInfo(_ device: AVCaptureDevice, fallbackID: String) -> CameraInfo {
    let facing = facingLabel(device.position)
    let dims = largestDimensions(device.formats)
    let resolution = "\(dims.width)x\(dims.height)"
    let ois = hasStabilization(device.activeFormat)
    var capabilities = ["BACKWARD_COMPATIBLE"]
    if Int(dims.width) * Int(dims.height) >= 12_000_000 {
        capabilities.append("RAW")
    }
    let level = device.position == .back ? "LEVEL_3" : "LIMITED"
    let cameraID = device.uniqueID.isEmpty ? fallbackID : device.uniqueID
    return CameraInfo(
        cameraId: cameraID,
        lensFacing: facing,
        hardwareLevel: level,
        sensorOrientation: 90,
        maxResolution: resolution,
        hasFlash: device.hasFlash,
        hasOpticalStabilization: ois,
        supportedCapabilities: capabilities
    )
}

private func facingLabel(_ position: AVCaptureDevice.Position) -> String {
    switch position {
    case .front:
        return "FRONT"
    case .back:
        return "BACK"
    default:
        return "EXTERNAL"
    }
}

private func largestDimensions(_ formats: [AVCaptureDevice.Format]) -> CMVideoDimensions {
    var best = CMVideoDimensions(width: 0, height: 0)
    var bestPixels: Int32 = 0
    for format in formats {
        let size = CMVideoFormatDescriptionGetDimensions(format.formatDescription)
        let pixels = size.width * size.height
        if pixels > bestPixels {
            best = size
            bestPixels = pixels
        }
    }
    return best
}

private func hasStabilization(_ format: AVCaptureDevice.Format) -> Bool {
    format.isVideoStabilizationModeSupported(.cinematic)
        || format.isVideoStabilizationModeSupported(.standard)
}
#endif

private func processSnapshot(sessionName: String) -> SessionCreate {
    let info = ProcessInfo.processInfo
    let version = "\(info.operatingSystemVersion.majorVersion).\(info.operatingSystemVersion.minorVersion)"
    let ramMb = Int(info.physicalMemory / 1_048_576)
    var payload = DeviceSnapshot.sampleiPhone(sessionName: sessionName)
    payload.phoneInfo.model = info.hostName
    payload.phoneInfo.androidVersion = version
    payload.phoneInfo.sdkInt = info.operatingSystemVersion.majorVersion
    payload.phoneCapabilities.cpuCores = info.processorCount
    payload.phoneCapabilities.totalRamMb = ramMb
    payload.phoneCapabilities.availableRamMb = max(ramMb / 2, 1)
    payload.metadata["system_name"] = .string(info.operatingSystemVersionString)
    payload.metadata["ios_version"] = .string(version)
    payload.metadata["live_source"] = .string("processinfo")
    payload.cameraCapabilities = CameraCapabilities(cameras: [])
    return payload
}

func majorVersion(_ version: String) -> Int {
    let head = version.split(separator: ".").first.flatMap { Int($0) }
    return head ?? 0
}

func hardwareMachine() -> String {
    var system = utsname()
    uname(&system)
    let mirror = Mirror(reflecting: system.machine)
    let bytes = mirror.children.compactMap { child -> UInt8? in
        guard let value = child.value as? Int8, value != 0 else { return nil }
        return UInt8(bitPattern: value)
    }
    return String(bytes: bytes, encoding: .utf8) ?? ""
}
