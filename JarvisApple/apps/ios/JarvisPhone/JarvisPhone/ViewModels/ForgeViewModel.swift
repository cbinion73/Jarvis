import Foundation
import SwiftUI
import PhotosUI
import JarvisKit

// MARK: - ForgeModel  (local display model wrapping ForgeModelRecord)

struct ForgeModel: Identifiable {
    let id: String
    let name: String
    let photoCount: Int
    let createdAt: String
    let usdzPath: String?

    init(record: ForgeModelRecord) {
        id         = record.id
        name       = record.name
        photoCount = record.photoCount
        createdAt  = record.createdAt
        usdzPath   = record.usdzPath
    }

    init(id: String, name: String, photoCount: Int, createdAt: String, usdzPath: String?) {
        self.id         = id
        self.name       = name
        self.photoCount = photoCount
        self.createdAt  = createdAt
        self.usdzPath   = usdzPath
    }

    var createdAtFormatted: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: createdAt) {
            return date.formatted(.dateTime.month(.abbreviated).day().year())
        }
        return String(createdAt.prefix(10))
    }

    var usdzURL: URL? {
        guard let p = usdzPath, !p.isEmpty else { return nil }
        return URL(filePath: p)
    }

    var asRecord: ForgeModelRecord {
        ForgeModelRecord(id: id, name: name, photoCount: photoCount,
                         createdAt: createdAt, usdzPath: usdzPath)
    }
}

// MARK: - ForgeViewModel

/// Manages photo selection and upload for server-side photogrammetry.
/// iOS does not have PhotogrammetrySession (macOS-only); photos are
/// captured here and sent to JARVIS for processing via the Forge endpoint.
@MainActor
final class ForgeViewModel: ObservableObject {

    @Published var selectedItems: [PhotosPickerItem] = [] {
        didSet { Task { await loadSelectedImages() } }
    }
    @Published var selectedImages: [UIImage] = []
    @Published var isUploading    = false
    @Published var uploadProgress: Double = 0
    @Published var uploadStatus   = ""
    @Published var models: [ForgeModel] = []
    @Published var showPicker  = false
    @Published var previewModel: ForgeModel?
    @Published var errorMessage: String?

    // Load thumbnail images when picker items change
    private func loadSelectedImages() async {
        var images: [UIImage] = []
        for item in selectedItems {
            if let data = try? await item.loadTransferable(type: Data.self),
               let img  = UIImage(data: data) {
                images.append(img)
            }
        }
        selectedImages = images
    }

    // Fetch existing models from server
    func loadModels() async {
        do {
            let records = try await AppleAPIClient.shared.fetchForgeModels()
            models = records.map { ForgeModel(record: $0) }
        } catch {
            // Empty state is fine on first launch
        }
    }

    // Upload photos to server and queue for photogrammetry processing
    func submitForProcessing(modelName: String) async {
        guard !selectedImages.isEmpty else { return }
        isUploading    = true
        uploadProgress = 0
        uploadStatus   = "Preparing \(selectedImages.count) photos…"
        errorMessage   = nil

        do {
            // Compress each image to JPEG and batch-encode to multipart
            var parts: [ForgePhotoUpload] = []
            for (i, img) in selectedImages.enumerated() {
                guard let data = img.jpegData(compressionQuality: 0.88) else { continue }
                parts.append(ForgePhotoUpload(
                    index: i,
                    filename: String(format: "photo_%04d.jpg", i),
                    data: data.base64EncodedString()
                ))
                uploadProgress = Double(i + 1) / Double(selectedImages.count) * 0.7
                uploadStatus   = "Encoding photo \(i + 1) of \(selectedImages.count)…"
            }

            uploadStatus   = "Uploading to Forge…"
            uploadProgress = 0.8

            let job = ForgeJobPayload(
                name:   modelName.isEmpty ? "Model \(Date().formatted(.dateTime.month().day()))" : modelName,
                photos: parts.map { ForgePhotoRecord(index: $0.index, filename: $0.filename, data: $0.data) }
            )
            let result = try await AppleAPIClient.shared.submitForgeJob(job)

            uploadProgress = 1.0
            uploadStatus   = result.queued
                ? "Queued for processing (\(result.jobId.prefix(8)))"
                : "Submission failed"

            if result.queued {
                // Add a pending model to the list
                let pending = ForgeModel(
                    id:         result.jobId,
                    name:       job.name,
                    photoCount: selectedImages.count,
                    createdAt:  ISO8601DateFormatter().string(from: Date()),
                    usdzPath:   nil
                )
                models.insert(pending, at: 0)
                selectedItems  = []
                selectedImages = []
            }
        } catch {
            uploadStatus   = "Upload failed"
            errorMessage   = error.localizedDescription
        }
        isUploading = false
    }
}

// MARK: - Local upload helper (wraps ForgePhotoRecord before converting)

private struct ForgePhotoUpload {
    let index: Int
    let filename: String
    let data: String   // base64 JPEG
}
