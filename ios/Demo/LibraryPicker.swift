import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

/// iOS 15-compatible photo picker (PHPicker; PhotosPicker is iOS 16+).
struct LibraryPicker: UIViewControllerRepresentable {
    var onPick: (Data, String) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(onPick: onPick)
    }

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration(photoLibrary: .shared())
        config.filter = .images
        config.selectionLimit = 1
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let onPick: (Data, String) -> Void

        init(onPick: @escaping (Data, String) -> Void) {
            self.onPick = onPick
        }

        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            picker.dismiss(animated: true)
            guard let provider = results.first?.itemProvider else { return }
            loadImage(provider)
        }

        private static func deliver(_ data: Data?, type: String, onPick: @escaping (Data, String) -> Void) {
            guard let data else { return }
            DispatchQueue.main.async {
                onPick(data, type)
            }
        }

        private func loadImage(_ provider: NSItemProvider) {
            if provider.hasItemConformingToTypeIdentifier(UTType.png.identifier) {
                provider.loadDataRepresentation(forTypeIdentifier: UTType.png.identifier) { data, _ in
                    Self.deliver(data, type: "image/png", onPick: self.onPick)
                }
                return
            }
            provider.loadDataRepresentation(forTypeIdentifier: UTType.jpeg.identifier) { data, _ in
                Self.deliver(data, type: "image/jpeg", onPick: self.onPick)
            }
        }
    }
}
