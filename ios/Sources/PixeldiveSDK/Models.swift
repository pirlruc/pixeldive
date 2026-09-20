import Foundation

/// Android `Build.*` identity collected by capture clients (wire names unchanged).
public struct PhoneInfo: Codable, Sendable, Equatable {
    public var manufacturer: String
    public var model: String
    public var brand: String
    public var device: String
    public var board: String
    /// Wire key `android_version`. iOS clients send `UIDevice.systemVersion`.
    public var androidVersion: String
    /// Wire key `sdk_int`. iOS clients send the OS major version as an int.
    public var sdkInt: Int

    public init(
        manufacturer: String,
        model: String,
        brand: String,
        device: String,
        board: String,
        androidVersion: String,
        sdkInt: Int
    ) {
        self.manufacturer = manufacturer
        self.model = model
        self.brand = brand
        self.device = device
        self.board = board
        self.androidVersion = androidVersion
        self.sdkInt = sdkInt
    }
}

/// RAM, CPU, and display metrics (ActivityManager / DisplayMetrics on Android).
public struct PhoneCapabilities: Codable, Sendable, Equatable {
    public var totalRamMb: Int
    public var availableRamMb: Int
    public var cpuAbi: String
    public var cpuCores: Int
    public var screenWidthPx: Int
    public var screenHeightPx: Int
    public var screenDensityDpi: Int
    public var isLowRamDevice: Bool

    public init(
        totalRamMb: Int,
        availableRamMb: Int,
        cpuAbi: String,
        cpuCores: Int,
        screenWidthPx: Int,
        screenHeightPx: Int,
        screenDensityDpi: Int,
        isLowRamDevice: Bool
    ) {
        self.totalRamMb = totalRamMb
        self.availableRamMb = availableRamMb
        self.cpuAbi = cpuAbi
        self.cpuCores = cpuCores
        self.screenWidthPx = screenWidthPx
        self.screenHeightPx = screenHeightPx
        self.screenDensityDpi = screenDensityDpi
        self.isLowRamDevice = isLowRamDevice
    }
}

/// One Camera2-shaped camera row. iOS maps `AVCaptureDevice` into these keys.
public struct CameraInfo: Codable, Sendable, Equatable {
    public var cameraId: String
    public var lensFacing: String
    public var hardwareLevel: String
    public var sensorOrientation: Int
    public var maxResolution: String
    public var hasFlash: Bool
    public var hasOpticalStabilization: Bool
    public var supportedCapabilities: [String]

    public init(
        cameraId: String,
        lensFacing: String,
        hardwareLevel: String,
        sensorOrientation: Int,
        maxResolution: String,
        hasFlash: Bool,
        hasOpticalStabilization: Bool,
        supportedCapabilities: [String]
    ) {
        self.cameraId = cameraId
        self.lensFacing = lensFacing
        self.hardwareLevel = hardwareLevel
        self.sensorOrientation = sensorOrientation
        self.maxResolution = maxResolution
        self.hasFlash = hasFlash
        self.hasOpticalStabilization = hasOpticalStabilization
        self.supportedCapabilities = supportedCapabilities
    }
}

/// Camera enumeration. `cameraCount` must equal `cameras.count`.
public struct CameraCapabilities: Codable, Sendable, Equatable {
    public let cameraCount: Int
    public let cameras: [CameraInfo]

    public init(cameras: [CameraInfo]) {
        self.cameraCount = cameras.count
        self.cameras = cameras
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let cameras = try container.decode([CameraInfo].self, forKey: .cameras)
        let cameraCount = try container.decode(Int.self, forKey: .cameraCount)
        guard cameraCount >= 0, cameraCount == cameras.count else {
            throw DecodingError.dataCorruptedError(
                forKey: .cameraCount,
                in: container,
                debugDescription: "camera_count must equal cameras.count"
            )
        }
        self.cameraCount = cameraCount
        self.cameras = cameras
    }

    private enum CodingKeys: String, CodingKey {
        case cameraCount
        case cameras
    }
}

/// POST `/api/v1/sessions` body.
public struct SessionCreate: Codable, Sendable, Equatable {
    public var sessionName: String
    public var phoneInfo: PhoneInfo
    public var phoneCapabilities: PhoneCapabilities
    public var cameraCapabilities: CameraCapabilities
    public var metadata: [String: JSONValue]

    public init(
        sessionName: String,
        phoneInfo: PhoneInfo,
        phoneCapabilities: PhoneCapabilities,
        cameraCapabilities: CameraCapabilities,
        metadata: [String: JSONValue] = [:]
    ) {
        self.sessionName = sessionName
        self.phoneInfo = phoneInfo
        self.phoneCapabilities = phoneCapabilities
        self.cameraCapabilities = cameraCapabilities
        self.metadata = metadata
    }
}

/// PUT `/api/v1/sessions/{id}` body. All fields optional.
public struct SessionUpdate: Codable, Sendable, Equatable {
    public var sessionName: String?
    public var status: String?
    public var metadata: [String: JSONValue]?
    public var mergeMetadata: Bool

    public init(
        sessionName: String? = nil,
        status: String? = nil,
        metadata: [String: JSONValue]? = nil,
        mergeMetadata: Bool = false
    ) {
        self.sessionName = sessionName
        self.status = status
        self.metadata = metadata
        self.mergeMetadata = mergeMetadata
    }
}

/// Public session representation (no storage paths).
public struct SessionRead: Codable, Sendable, Equatable {
    public var id: UUID
    public var sessionName: String
    public var status: String
    public var createdAt: Date
    public var updatedAt: Date
    public var phoneInfo: PhoneInfo
    public var phoneCapabilities: PhoneCapabilities
    public var cameraCapabilities: CameraCapabilities
    public var metadata: [String: JSONValue]
}

/// Paginated session list.
public struct SessionPage: Codable, Sendable, Equatable {
    public var items: [SessionRead]
    public var nextCursor: String?
}

/// Public image metadata (no `storage_path`).
public struct SessionImage: Codable, Sendable, Equatable {
    public var id: UUID
    public var sessionId: UUID
    public var filename: String
    public var contentType: String
    public var sizeBytes: Int
    public var uploadedAt: Date
    public var metadata: [String: JSONValue]
}

/// Paginated image list.
public struct ImagePage: Codable, Sendable, Equatable {
    public var items: [SessionImage]
    public var nextCursor: String?
}

/// Liveness or readiness probe payload.
public struct HealthStatus: Codable, Sendable, Equatable {
    public var status: String
}
