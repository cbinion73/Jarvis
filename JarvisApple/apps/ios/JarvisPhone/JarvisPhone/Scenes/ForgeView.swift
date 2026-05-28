import SwiftUI
import PhotosUI
import QuickLook

// MARK: - ForgeView  "The Workshop"
// Forge · 3-D Capture & Photogrammetry

struct ForgeView: View {

    @StateObject private var vm = ForgeViewModel()
    @State private var modelName = ""
    private let copper = Color(red: 1.0, green: 0.55, blue: 0.15)

    var body: some View {
        NavigationStack {
            ZStack {
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.08, green: 0.04, blue: 0.01), Color.black],
                        startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.55)
                    )
                }
                .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {

                        // ── Capture card ───────────────────────────
                        captureCard

                        // ── Selected photos grid ───────────────────
                        if !vm.selectedImages.isEmpty {
                            photosGrid
                        }

                        // ── Upload progress ────────────────────────
                        if vm.isUploading {
                            uploadCard
                        }

                        // ── Error banner ───────────────────────────
                        if let err = vm.errorMessage {
                            Text(err)
                                .font(.caption).foregroundStyle(.red)
                                .padding(12)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .glassEffect(in: RoundedRectangle(cornerRadius: 12))
                        }

                        // ── Past models ────────────────────────────
                        if !vm.models.isEmpty {
                            modelsSection
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Forge")
            .navigationBarTitleDisplayMode(.large)
            .sheet(isPresented: $vm.showPicker) {
                photoPicker
            }
            .sheet(item: $vm.previewModel) { model in
                ModelPreviewSheet(model: model, copper: copper)
            }
        }
        .task { await vm.loadModels() }
    }

    // MARK: - Capture card

    private var captureCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                ZStack {
                    Circle().fill(copper.opacity(0.12)).frame(width: 44, height: 44)
                    Image(systemName: "cube.fill")
                        .font(.system(size: 20)).foregroundStyle(copper)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Forge")
                        .font(.title3.bold()).foregroundStyle(.white)
                    Text("3-D Capture · Photogrammetry")
                        .font(.caption2).foregroundStyle(copper.opacity(0.7))
                }
            }

            Divider().opacity(0.2)

            Text("Select 20–200 overlapping photos of an object. Photos upload to JARVIS and are processed into a USDZ 3-D model you can view in AR.")
                .font(.subheadline).foregroundStyle(.white.opacity(0.7))
                .fixedSize(horizontal: false, vertical: true)

            // Model name field
            HStack(spacing: 8) {
                Image(systemName: "pencil").foregroundStyle(copper.opacity(0.6)).font(.caption)
                TextField("Model name (optional)", text: $modelName)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                    .tint(copper)
            }
            .padding(10)
            .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))

            HStack(spacing: 10) {
                // Photo library picker
                Button { vm.showPicker = true } label: {
                    Label(
                        vm.selectedImages.isEmpty
                            ? "Choose Photos"
                            : "\(vm.selectedImages.count) selected",
                        systemImage: "photo.stack.fill"
                    )
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 11)
                    .foregroundStyle(copper)
                    .background(copper.opacity(0.12), in: RoundedRectangle(cornerRadius: 12))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(copper.opacity(0.25), lineWidth: 1))
                }
                .buttonStyle(.plain)

                // Clear
                if !vm.selectedImages.isEmpty {
                    Button {
                        vm.selectedItems  = []
                        vm.selectedImages = []
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 22))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }

            // Submit button — only show when photos are selected and not uploading
            if !vm.selectedImages.isEmpty && !vm.isUploading {
                Button {
                    Task { await vm.submitForProcessing(modelName: modelName) }
                } label: {
                    Label("Submit to Forge", systemImage: "cube.transparent.fill")
                        .font(.subheadline.bold())
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .foregroundStyle(.black)
                        .background(copper, in: RoundedRectangle(cornerRadius: 12))
                }
                .buttonStyle(.plain)
            }

            // Tips when nothing selected
            if vm.selectedImages.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForgeHintRow(icon: "rotate.3d",         text: "Walk 360° around the object",     color: copper)
                    ForgeHintRow(icon: "arrow.up.and.down", text: "Vary your height — high & low",   color: copper)
                    ForgeHintRow(icon: "sun.max",           text: "Even diffuse lighting works best", color: copper)
                    ForgeHintRow(icon: "photo.badge.plus",  text: "20 photos minimum, 200 max",       color: copper)
                }
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Photos grid

    private var photosGrid: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "photo.stack").font(.system(size: 11, weight: .semibold)).foregroundStyle(copper)
                Text("SELECTED PHOTOS").font(.system(size: 10, weight: .bold)).tracking(1.0).foregroundStyle(copper.opacity(0.85))
                Spacer()
                Text("\(vm.selectedImages.count)")
                    .font(.system(size: 10, weight: .bold)).foregroundStyle(copper)
                    .padding(.horizontal, 7).padding(.vertical, 3)
                    .background(copper.opacity(0.12), in: Capsule())
            }
            LazyVGrid(
                columns: Array(repeating: GridItem(.flexible(), spacing: 4), count: 5),
                spacing: 4
            ) {
                ForEach(Array(vm.selectedImages.enumerated()), id: \.offset) { _, img in
                    Image(uiImage: img)
                        .resizable()
                        .aspectRatio(1, contentMode: .fill)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                }
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Upload progress card

    private var uploadCard: some View {
        VStack(spacing: 14) {
            HStack(spacing: 12) {
                ZStack {
                    Circle().fill(copper.opacity(0.12)).frame(width: 40, height: 40)
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 20)).foregroundStyle(copper)
                        .symbolEffect(.pulse)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Uploading…").font(.subheadline.bold()).foregroundStyle(.white)
                    Text(vm.uploadStatus).font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Text(String(format: "%.0f%%", vm.uploadProgress * 100))
                    .font(.system(size: 14, weight: .bold).monospacedDigit())
                    .foregroundStyle(copper)
            }
            ProgressView(value: vm.uploadProgress)
                .tint(copper)
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Models section

    private var modelsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "cube.fill").font(.system(size: 11, weight: .semibold)).foregroundStyle(copper)
                Text("3-D MODELS").font(.system(size: 10, weight: .bold)).tracking(1.0).foregroundStyle(copper.opacity(0.85))
            }
            ForEach(vm.models) { model in
                ForgeModelRow(model: model, copper: copper) {
                    if model.usdzPath != nil { vm.previewModel = model }
                }
                if model.id != vm.models.last?.id { Divider().opacity(0.18) }
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Photo picker

    private var photoPicker: some View {
        PhotosPicker(
            selection: $vm.selectedItems,
            maxSelectionCount: 200,
            matching: .images
        ) {
            Text("Select Photos for Forge")
        }
        .photosPickerStyle(.inline)
        .ignoresSafeArea()
    }
}

// MARK: - USDZ Quick Look (AR-ready iOS preview)

private struct USDZQLPreview: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> QLPreviewController {
        let c = QLPreviewController()
        c.dataSource = context.coordinator
        return c
    }
    func updateUIViewController(_ vc: QLPreviewController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(url: url) }

    final class Coordinator: NSObject, QLPreviewControllerDataSource {
        let url: URL
        init(url: URL) { self.url = url }
        func numberOfPreviewItems(in c: QLPreviewController) -> Int { 1 }
        func previewController(_ c: QLPreviewController,
                               previewItemAt i: Int) -> any QLPreviewItem { url as NSURL }
    }
}

private struct ModelPreviewSheet: View {
    let model: ForgeModel
    let copper: Color
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                if let url = model.usdzURL {
                    USDZQLPreview(url: url).ignoresSafeArea()
                } else {
                    VStack(spacing: 16) {
                        Image(systemName: "gearshape.2.fill")
                            .font(.system(size: 44)).foregroundStyle(copper.opacity(0.3))
                            .symbolEffect(.pulse)
                        Text(model.name).font(.headline).foregroundStyle(.white)
                        Text("Processing on JARVIS…")
                            .font(.caption).foregroundStyle(.secondary)
                        Text("Pull to refresh when complete.")
                            .font(.caption2).foregroundStyle(.tertiary)
                    }
                }
            }
            .navigationTitle(model.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done") { dismiss() }
                }
                if let url = model.usdzURL {
                    ToolbarItem(placement: .topBarTrailing) {
                        ShareLink(item: url, subject: Text(model.name)) {
                            Image(systemName: "square.and.arrow.up")
                        }
                    }
                }
            }
        }
    }
}

// MARK: - Model row

private struct ForgeModelRow: View {
    let model: ForgeModel
    let copper: Color
    let onPreview: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 8).fill(copper.opacity(0.08)).frame(width: 44, height: 44)
                Image(systemName: model.usdzPath != nil ? "cube.fill" : "gearshape.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(model.usdzPath != nil ? copper.opacity(0.6) : .secondary)
            }
            VStack(alignment: .leading, spacing: 3) {
                Text(model.name).font(.subheadline).foregroundStyle(.white)
                Text("\(model.photoCount) photos · \(model.createdAtFormatted)")
                    .font(.caption2).foregroundStyle(.secondary)
            }
            Spacer()
            if model.usdzPath != nil {
                Button(action: onPreview) {
                    Text("View")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(copper)
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(copper.opacity(0.12), in: Capsule())
                }
                .buttonStyle(.plain)
            } else {
                Text("Processing")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 8).padding(.vertical, 4)
                    .background(.white.opacity(0.06), in: Capsule())
            }
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Hint row

private struct ForgeHintRow: View {
    let icon: String; let text: String; let color: Color
    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13)).foregroundStyle(color.opacity(0.6))
                .frame(width: 22)
            Text(text).font(.subheadline).foregroundStyle(.white.opacity(0.7))
        }
    }
}

#Preview { ForgeView() }
