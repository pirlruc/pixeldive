import SwiftUI
import UIKit

struct ContentView: View {
    @EnvironmentObject private var model: DemoModel
    @State private var showPicker = false

    var body: some View {
        NavigationView {
            Form {
                connectionSection
                sessionSection
                cameraSection
                imageSection
                logSection
            }
            .navigationTitle("Pixeldive")
            .disabled(model.busy)
            .sheet(isPresented: $showPicker) {
                LibraryPicker { data, contentType in
                    Task { await model.upload(data: data, filename: name(for: contentType), contentType: contentType) }
                }
            }
        }
        .navigationViewStyle(.stack)
    }

    private var connectionSection: some View {
        Section("Service") {
            TextField("REST URL", text: $model.baseURLText)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(.URL)
            TextField("gRPC host", text: $model.grpcHost)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            TextField("gRPC port", text: $model.grpcPort)
                .keyboardType(.numberPad)
            SecureField("Bearer token (optional)", text: $model.token)
            Button("Refresh sessions") {
                Task { await model.refresh() }
            }
        }
    }

    private var sessionSection: some View {
        Section("Session") {
            Button("Create iOS session") {
                Task { await model.createSession() }
            }
            Picker("Selected", selection: selectedID) {
                Text("None").tag(String?.none)
                ForEach(model.sessions, id: \.id) { session in
                    Text(session.sessionName).tag(Optional(session.id.uuidString))
                }
            }
            if let session = model.selectedSession {
                Text(session.id.uuidString.lowercased())
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
                Text("\(session.phoneInfo.manufacturer) \(session.phoneInfo.model)")
                Text("OS \(session.phoneInfo.androidVersion) · cameras \(session.cameraCapabilities.cameraCount)")
            }
            Button("Delete selected", role: .destructive) {
                Task { await model.deleteSelected() }
            }
        }
    }

    private var cameraSection: some View {
        Section("Camera feed (gRPC)") {
            CameraPreview(session: model.camera.session)
                .frame(height: 180)
                .listRowInsets(EdgeInsets())
            if model.capturing {
                Button("Stop camera") { model.stopCamera() }
            } else {
                Button("Start camera feed") { model.startCamera() }
            }
            if !model.camera.notice.isEmpty {
                Text(model.camera.notice).font(.footnote)
            }
        }
    }

    private var imageSection: some View {
        Section("Images") {
            Button("Upload from photos") {
                showPicker = true
            }
            Button("Download first image") {
                Task { await model.downloadFirst() }
            }
            Text("\(model.images.count) image(s)")
            if let preview = model.preview, let image = UIImage(data: preview) {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
                    .frame(maxHeight: 180)
            }
        }
    }

    private var logSection: some View {
        Section("Log") {
            Text(model.log)
                .font(.footnote.monospaced())
        }
    }

    private var selectedID: Binding<String?> {
        Binding(
            get: { model.selectedSession?.id.uuidString },
            set: { newValue in
                model.selectedSession = model.sessions.first { $0.id.uuidString == newValue }
            }
        )
    }

    private func name(for contentType: String) -> String {
        contentType == "image/png" ? "frame.png" : "frame.jpg"
    }
}
