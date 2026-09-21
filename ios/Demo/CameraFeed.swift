import AVFoundation
import CoreImage
import ImageIO
import SwiftUI
import UIKit

/// Live camera preview plus JPEG frames for gRPC upload.
final class CameraFeed: NSObject, ObservableObject {
    @Published var running = false
    @Published var notice = ""

    let session = AVCaptureSession()
    var onJPEG: ((Data) -> Void)?

    private let output = AVCaptureVideoDataOutput()
    private let queue = DispatchQueue(label: "pixeldive.camera")
    private let ciContext = CIContext()
    private let busyLock = NSLock()
    private var busy = false
    private var lastEmit = Date.distantPast
    private let minInterval: TimeInterval = 0.45

    func setBusy(_ value: Bool) {
        busyLock.lock()
        busy = value
        busyLock.unlock()
    }

    private func isBusy() -> Bool {
        busyLock.lock()
        defer { busyLock.unlock() }
        return busy
    }

    func requestAndStart() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            start()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    if granted {
                        self?.start()
                    } else {
                        self?.notice = "Camera permission denied."
                    }
                }
            }
        default:
            notice = "Camera permission denied."
        }
    }

    func stop() {
        queue.async { [weak self] in
            self?.session.stopRunning()
            DispatchQueue.main.async { self?.running = false }
        }
    }

    private func start() {
        queue.async { [weak self] in
            self?.configureAndRun()
        }
    }

    private func configureAndRun() {
        if session.isRunning {
            DispatchQueue.main.async { self.running = true }
            return
        }
        do {
            try configure()
            session.startRunning()
            DispatchQueue.main.async { self.running = true }
        } catch {
            DispatchQueue.main.async { self.notice = error.localizedDescription }
        }
    }

    private func configure() throws {
        if !session.inputs.isEmpty {
            return
        }
        session.beginConfiguration()
        defer { session.commitConfiguration() }
        guard let device = AVCaptureDevice.default(for: .video) else {
            throw PixeldiveCameraError.unavailable
        }
        let input = try AVCaptureDeviceInput(device: device)
        guard session.canAddInput(input), session.canAddOutput(output) else {
            throw PixeldiveCameraError.unavailable
        }
        session.addInput(input)
        output.alwaysDiscardsLateVideoFrames = true
        output.setSampleBufferDelegate(self, queue: queue)
        session.addOutput(output)
        session.sessionPreset = .medium
    }
}

extension CameraFeed: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        let now = Date()
        if now.timeIntervalSince(lastEmit) < minInterval || isBusy() {
            return
        }
        lastEmit = now
        guard let jpeg = jpegData(sampleBuffer) else { return }
        DispatchQueue.main.async { self.onJPEG?(jpeg) }
    }

    private func jpegData(_ sampleBuffer: CMSampleBuffer) -> Data? {
        guard let imageBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            return nil
        }
        let image = CIImage(cvImageBuffer: imageBuffer)
        guard let space = CGColorSpace(name: CGColorSpace.sRGB) else {
            return nil
        }
        let quality: [CIImageRepresentationOption: Any] = [
            kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.55,
        ]
        return ciContext.jpegRepresentation(of: image, colorSpace: space, options: quality)
    }
}

enum PixeldiveCameraError: Error, LocalizedError {
    case unavailable

    var errorDescription: String? {
        "No camera available."
    }
}

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewSurface {
        let view = PreviewSurface()
        view.previewLayer.session = session
        view.previewLayer.videoGravity = .resizeAspectFill
        return view
    }

    func updateUIView(_ uiView: PreviewSurface, context: Context) {
        uiView.previewLayer.session = session
    }
}

class PreviewSurface: UIView {
    override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }

    var previewLayer: AVCaptureVideoPreviewLayer {
        (layer as? AVCaptureVideoPreviewLayer) ?? AVCaptureVideoPreviewLayer()
    }
}
