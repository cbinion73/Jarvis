import SwiftUI
import PhotosUI
import QuickLook
import JarvisKit

// MARK: - ForgeView  "The Workshop"
// Forge · 3-D Capture & Photogrammetry

struct ForgeView: View {

    @StateObject private var vm = ForgeViewModel()
    @State private var modelName = ""
    @State private var projectTitle = ""
    @State private var projectDescription = ""
    @State private var isCreatingProject = false
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
                        if let summary = vm.summary {
                            workspacePulseCard(summary)
                        }

                        if let continuity = vm.overview?.continuity,
                           continuity.profileFactCount > 0
                            || continuity.queuedJobCount > 0
                            || !continuity.activeWorkshopLanes.isEmpty
                            || !continuity.guidanceLines.isEmpty
                            || !continuity.recentProfileFacts.isEmpty
                            || !continuity.recentFirstLight.isEmpty {
                            continuityCard(continuity)
                        }

                        projectIntakeCard
                        captureCard

                        if !vm.selectedImages.isEmpty {
                            photosGrid
                        }

                        if vm.isUploading {
                            uploadCard
                        }

                        if let err = vm.errorMessage {
                            Text(err)
                                .font(.caption)
                                .foregroundStyle(.red)
                                .padding(12)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .glassEffect(in: RoundedRectangle(cornerRadius: 12))
                        }

                        if let project = vm.activeProject {
                            activeProjectSection(project)
                        }

                        if !vm.recentJobs.isEmpty {
                            recentJobsSection
                        }

                        if !vm.models.isEmpty {
                            modelsSection
                        }

                        if !vm.projects.isEmpty {
                            projectsSection
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Forge")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await vm.loadOverview() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
            .sheet(isPresented: $vm.showPicker) {
                photoPicker
            }
            .sheet(item: $vm.previewModel) { model in
                ModelPreviewSheet(model: model, copper: copper)
            }
        }
        .task { await vm.loadOverview() }
    }

    // MARK: - Workspace pulse

    private func workspacePulseCard(_ summary: ForgeSummary) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                ZStack {
                    Circle().fill(copper.opacity(0.12)).frame(width: 44, height: 44)
                    Image(systemName: "shippingbox.fill")
                        .font(.system(size: 20))
                        .foregroundStyle(copper)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Workshop Pulse")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text("Live Forge project posture from JARVIS")
                        .font(.caption2)
                        .foregroundStyle(copper.opacity(0.7))
                }
            }

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                ForgeMetricTile(title: "Projects", value: "\(summary.totalProjects)", accent: copper)
                ForgeMetricTile(title: "Active", value: "\(summary.activeProjects)", accent: .blue)
                ForgeMetricTile(title: "Captures", value: "\(summary.captureProjects)", accent: .yellow)
                ForgeMetricTile(title: "Models", value: "\(summary.readyModels)", accent: .green)
                ForgeMetricTile(title: "Approvals", value: "\(summary.approvalQueue)", accent: .orange)
                ForgeMetricTile(title: "Queued", value: "\(summary.queuedJobs)", accent: .mint)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func continuityCard(_ continuity: ForgeContinuity) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                ZStack {
                    Circle().fill(copper.opacity(0.12)).frame(width: 44, height: 44)
                    Image(systemName: "point.3.connected.trianglepath.dotted")
                        .font(.system(size: 18))
                        .foregroundStyle(copper)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text("Carry Forward")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text("Workshop memory and recent rhythm from JARVIS")
                        .font(.caption2)
                        .foregroundStyle(copper.opacity(0.7))
                }
            }

            HStack(spacing: 10) {
                ForgeMetricTile(title: "Facts", value: "\(continuity.profileFactCount)", accent: copper)
                ForgeMetricTile(title: "Queued", value: "\(continuity.queuedJobCount)", accent: .mint)
                ForgeMetricTile(title: "Lanes", value: "\(continuity.activeWorkshopLanes.count)", accent: .blue)
            }

            if !continuity.workshopFocus.isEmpty {
                Text(continuity.workshopFocus)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.white.opacity(0.86))
                    .fixedSize(horizontal: false, vertical: true)
            }

            if !continuity.activeWorkshopLanes.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("ACTIVE LANES")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(1.0)
                        .foregroundStyle(.secondary)
                    Text(continuity.activeWorkshopLanes.joined(separator: " • "))
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.74))
                }
            }

            if !continuity.guidanceLines.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("WORKSHOP RHYTHM")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(1.0)
                        .foregroundStyle(.secondary)
                    ForEach(continuity.guidanceLines, id: \.self) { line in
                        Text("• \(line)")
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.74))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }

            if !continuity.recentProfileFacts.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("DURABLE PATTERNS")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(1.0)
                        .foregroundStyle(.secondary)
                    ForEach(continuity.recentProfileFacts) { fact in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(fact.title)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(.white)
                            if !fact.summary.isEmpty {
                                Text(fact.summary)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.72))
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
            }

            if !continuity.recentFirstLight.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("RECENT FIRST LIGHT")
                        .font(.system(size: 9, weight: .bold))
                        .tracking(1.0)
                        .foregroundStyle(.secondary)
                    ForEach(continuity.recentFirstLight) { moment in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(moment.label)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white)
                            Text(moment.summary)
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.72))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Intake card

    private var projectIntakeCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                Image(systemName: "plus.square.on.square")
                    .font(.system(size: 18))
                    .foregroundStyle(copper)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Workshop Intake")
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text("Create a live Forge project before capture, modeling, and print review.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Project title")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(copper.opacity(0.85))
                TextField("Garden bracket, camera mount, family keepsake...", text: $projectTitle)
                    .textInputAutocapitalization(.words)
                    .padding(10)
                    .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Description")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(copper.opacity(0.85))
                TextField("What are we making and what matters most?", text: $projectDescription, axis: .vertical)
                    .lineLimit(3...5)
                    .padding(10)
                    .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))
            }

            Button {
                let title = projectTitle
                let description = projectDescription
                Task {
                    isCreatingProject = true
                    await vm.createProject(title: title, description: description)
                    isCreatingProject = false
                    if vm.errorMessage == nil {
                        projectTitle = ""
                        projectDescription = ""
                    }
                }
            } label: {
                Label(isCreatingProject ? "Creating Project…" : "Create Forge Project", systemImage: "hammer.fill")
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .foregroundStyle(.black)
                    .background(copper, in: RoundedRectangle(cornerRadius: 12))
            }
            .buttonStyle(.plain)
            .disabled(isCreatingProject || projectTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .opacity(isCreatingProject || projectTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? 0.7 : 1)
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
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
                    Text("Forge Capture")
                        .font(.title3.bold()).foregroundStyle(.white)
                    Text("3-D Capture · Photogrammetry")
                        .font(.caption2).foregroundStyle(copper.opacity(0.7))
                }
            }

            Divider().opacity(0.2)

            Text("Select 20–200 overlapping photos of an object. Photos upload to JARVIS and are processed into a USDZ 3-D model you can view in AR.")
                .font(.subheadline).foregroundStyle(.white.opacity(0.7))
                .fixedSize(horizontal: false, vertical: true)

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

            if vm.selectedImages.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForgeHintRow(icon: "rotate.3d", text: "Walk 360° around the object", color: copper)
                    ForgeHintRow(icon: "arrow.up.and.down", text: "Vary your height — high & low", color: copper)
                    ForgeHintRow(icon: "sun.max", text: "Even diffuse lighting works best", color: copper)
                    ForgeHintRow(icon: "photo.badge.plus", text: "20 photos minimum, 200 max", color: copper)
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
                Image(systemName: "photo.stack")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(copper)
                Text("SELECTED PHOTOS")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(copper.opacity(0.85))
                Spacer()
                Text("\(vm.selectedImages.count)")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(copper)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
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

    // MARK: - Active project section

    private func activeProjectSection(_ project: ForgeProjectDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: "scope")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(copper)
                Text("ACTIVE PROJECT")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(copper.opacity(0.85))
            }

            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(project.title)
                            .font(.headline)
                            .foregroundStyle(.white)
                        Text(project.description.isEmpty ? "No description yet." : project.description)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    ForgeStatusBadge(status: project.status, accent: copper)
                }

                HStack(spacing: 8) {
                    ForgeMicroChip(text: "\(project.sourceFileCount) files", accent: .blue)
                    ForgeMicroChip(text: "\(project.captureFrameCount) frames", accent: .yellow)
                    ForgeMicroChip(text: "\(project.generatedModelCount) models", accent: .green)
                    if project.measurementCount > 0 {
                        ForgeMicroChip(text: "\(project.measurementCount) measurements", accent: .mint)
                    }
                }

                if let confidence = project.captureConfidence {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Capture confidence")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(copper.opacity(0.85))
                        HStack(spacing: 8) {
                            ForgeMicroChip(text: "Geometry \(confidence.geometry.capitalized)", accent: .blue)
                            ForgeMicroChip(text: "Scale \(confidence.scale.capitalized)", accent: .orange)
                            ForgeMicroChip(text: "Print \(confidence.printReadiness.replacingOccurrences(of: "_", with: " ").capitalized)", accent: .green)
                        }
                    }
                }

                if !project.missingViews.isEmpty {
                    Text("Missing views: \(project.missingViews.map { $0.capitalized }.joined(separator: ", "))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if !project.generatedModels.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Recent outputs")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(copper.opacity(0.85))
                        ForEach(project.generatedModels) { model in
                            ForgeOutputRow(model: model, copper: copper)
                        }
                    }
                }
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Jobs

    private var recentJobsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "clock.arrow.trianglehead.counterclockwise.rotate.90")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(copper)
                Text("RECENT JOBS")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(copper.opacity(0.85))
            }
            ForEach(vm.recentJobs.prefix(4)) { job in
                ForgeJobRow(job: job, copper: copper)
                if job.id != vm.recentJobs.prefix(4).last?.id {
                    Divider().opacity(0.18)
                }
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Models section

    private var modelsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "cube.fill")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(copper)
                Text("3-D MODELS")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(copper.opacity(0.85))
            }
            ForEach(vm.models) { model in
                ForgeModelRow(model: model, copper: copper) {
                    if model.usdzPath != nil {
                        vm.previewModel = model
                    }
                }
                if model.id != vm.models.last?.id {
                    Divider().opacity(0.18)
                }
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Projects section

    private var projectsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "shippingbox")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(copper)
                Text("PROJECTS")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(copper.opacity(0.85))
            }
            ForEach(vm.projects) { project in
                ForgeProjectRow(project: project, copper: copper)
                if project.id != vm.projects.last?.id {
                    Divider().opacity(0.18)
                }
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

        func previewController(_ c: QLPreviewController, previewItemAt i: Int) -> any QLPreviewItem {
            url as NSURL
        }
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
                            .font(.system(size: 44))
                            .foregroundStyle(copper.opacity(0.3))
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

private struct ForgeMetricTile: View {
    let title: String
    let value: String
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .bold))
                .tracking(0.8)
                .foregroundStyle(accent.opacity(0.8))
            Text(value)
                .font(.title3.weight(.bold))
                .foregroundStyle(.white)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 12))
    }
}

private struct ForgeMicroChip: View {
    let text: String
    let accent: Color

    var body: some View {
        Text(text)
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(accent)
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(accent.opacity(0.12), in: Capsule())
    }
}

private struct ForgeStatusBadge: View {
    let status: String
    let accent: Color

    private var tint: Color {
        switch status {
        case "completed", "print_ready", "slice_ready", "model_ready":
            return .green
        case "capture_in_progress", "needs_more_views", "needs_measurements", "modeling":
            return .yellow
        case "approval_required":
            return .orange
        case "failed", "inspection_failed":
            return .red
        default:
            return accent
        }
    }

    var body: some View {
        Text(status.replacingOccurrences(of: "_", with: " ").capitalized)
            .font(.system(size: 10, weight: .semibold))
            .foregroundStyle(tint)
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(tint.opacity(0.12), in: Capsule())
    }
}

private struct ForgeProjectRow: View {
    let project: ForgeProjectSummary
    let copper: Color

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(copper.opacity(0.08))
                    .frame(width: 44, height: 44)
                Image(systemName: "shippingbox.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(copper.opacity(0.8))
            }
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(project.title)
                        .font(.subheadline)
                        .foregroundStyle(.white)
                    Spacer()
                    ForgeStatusBadge(status: project.status, accent: copper)
                }
                Text("\(project.sourceFileCount) files · \(project.captureFrameCount) frames · \(project.generatedModelCount) models")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if let latestModelName = project.latestModelName, !latestModelName.isEmpty {
                    Text("Latest: \(latestModelName)")
                        .font(.caption2)
                        .foregroundStyle(copper.opacity(0.85))
                } else if let latestCaptureStatus = project.latestCaptureStatus, !latestCaptureStatus.isEmpty {
                    Text("Capture: \(latestCaptureStatus.replacingOccurrences(of: "_", with: " ").capitalized)")
                        .font(.caption2)
                        .foregroundStyle(copper.opacity(0.85))
                }
            }
        }
        .padding(.vertical, 2)
    }
}

private struct ForgeJobRow: View {
    let job: ForgeJobStatus
    let copper: Color

    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(copper.opacity(0.08))
                    .frame(width: 40, height: 40)
                Image(systemName: "clock.fill")
                    .font(.system(size: 16))
                    .foregroundStyle(copper.opacity(0.8))
            }
            VStack(alignment: .leading, spacing: 3) {
                Text(job.name)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                Text("\(job.photoCount) photos · \(job.createdAt.prefix(10))")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            ForgeStatusBadge(status: job.status, accent: copper)
        }
        .padding(.vertical, 2)
    }
}

private struct ForgeOutputRow: View {
    let model: ForgeGeneratedModelSummary
    let copper: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(model.title)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                Spacer()
                ForgeMicroChip(text: model.format.uppercased(), accent: copper)
            }
            if let sourceImage = model.sourceImage, !sourceImage.isEmpty {
                Text("Source: \(sourceImage)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            if !model.notes.isEmpty {
                Text(model.notes)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(10)
        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
    }
}

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

private struct ForgeHintRow: View {
    let icon: String
    let text: String
    let color: Color

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundStyle(color.opacity(0.6))
                .frame(width: 22)
            Text(text)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.7))
        }
    }
}

#Preview { ForgeView() }
