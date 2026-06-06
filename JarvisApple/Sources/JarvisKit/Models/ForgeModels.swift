import Foundation

// MARK: - ForgeOverview

public struct ForgeOverview: Decodable, Sendable {
    public let summary: ForgeSummary
    public let activeProject: ForgeProjectDetail?
    public let projects: [ForgeProjectSummary]
    public let models: [ForgeModelRecord]
    public let recentJobs: [ForgeJobStatus]
    public let continuity: ForgeContinuity?

    private enum CodingKeys: String, CodingKey {
        case summary
        case activeProject = "active_project"
        case projects
        case models
        case recentJobs = "recent_jobs"
        case continuity
    }
}

public struct ForgeContinuity: Decodable, Sendable {
    public let subjectDisplayName: String
    public let workshopFocus: String
    public let activeWorkshopLanes: [String]
    public let queuedJobCount: Int
    public let profileFactCount: Int
    public let guidanceLines: [String]
    public let recentProfileFacts: [ForgeContinuityFact]
    public let recentFirstLight: [ForgeContinuityMoment]

    private enum CodingKeys: String, CodingKey {
        case subjectDisplayName = "subject_display_name"
        case workshopFocus = "workshop_focus"
        case activeWorkshopLanes = "active_workshop_lanes"
        case queuedJobCount = "queued_job_count"
        case profileFactCount = "profile_fact_count"
        case guidanceLines = "guidance_lines"
        case recentProfileFacts = "recent_profile_facts"
        case recentFirstLight = "recent_first_light"
    }
}

public struct ForgeContinuityFact: Decodable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let summary: String
}

public struct ForgeContinuityMoment: Decodable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let summary: String
}

public struct ForgeSummary: Decodable, Sendable {
    public let totalProjects: Int
    public let activeProjects: Int
    public let captureProjects: Int
    public let readyModels: Int
    public let approvalQueue: Int
    public let queuedJobs: Int

    private enum CodingKeys: String, CodingKey {
        case totalProjects = "total_projects"
        case activeProjects = "active_projects"
        case captureProjects = "capture_projects"
        case readyModels = "ready_models"
        case approvalQueue = "approval_queue"
        case queuedJobs = "queued_jobs"
    }
}

public struct ForgeProjectSummary: Decodable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let status: String
    public let intakeType: String
    public let updatedAt: String
    public let sourceFileCount: Int
    public let captureFrameCount: Int
    public let measurementCount: Int
    public let generatedModelCount: Int
    public let approvalCount: Int
    public let latestCaptureStatus: String?
    public let printReadiness: String?
    public let latestModelName: String?

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case status
        case intakeType = "intake_type"
        case updatedAt = "updated_at"
        case sourceFileCount = "source_file_count"
        case captureFrameCount = "capture_frame_count"
        case measurementCount = "measurement_count"
        case generatedModelCount = "generated_model_count"
        case approvalCount = "approval_count"
        case latestCaptureStatus = "latest_capture_status"
        case printReadiness = "print_readiness"
        case latestModelName = "latest_model_name"
    }
}

public struct ForgeProjectDetail: Decodable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let description: String
    public let status: String
    public let intakeType: String
    public let updatedAt: String
    public let notes: String
    public let sourceFileCount: Int
    public let captureFrameCount: Int
    public let measurementCount: Int
    public let generatedModelCount: Int
    public let approvalCount: Int
    public let latestCaptureStatus: String?
    public let captureConfidence: ForgeCaptureConfidence?
    public let missingViews: [String]
    public let generatedModels: [ForgeGeneratedModelSummary]

    private enum CodingKeys: String, CodingKey {
        case id
        case title
        case description
        case status
        case intakeType = "intake_type"
        case updatedAt = "updated_at"
        case notes
        case sourceFileCount = "source_file_count"
        case captureFrameCount = "capture_frame_count"
        case measurementCount = "measurement_count"
        case generatedModelCount = "generated_model_count"
        case approvalCount = "approval_count"
        case latestCaptureStatus = "latest_capture_status"
        case captureConfidence = "capture_confidence"
        case missingViews = "missing_views"
        case generatedModels = "generated_models"
    }
}

public struct ForgeCaptureConfidence: Decodable, Sendable {
    public let geometry: String
    public let scale: String
    public let printReadiness: String

    private enum CodingKeys: String, CodingKey {
        case geometry
        case scale
        case printReadiness = "print_readiness"
    }
}

public struct ForgeGeneratedModelSummary: Decodable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let format: String
    public let createdAt: String
    public let sourceImage: String?
    public let notes: String

    private enum CodingKeys: String, CodingKey {
        case id = "model_id"
        case title
        case format
        case createdAt = "created_at"
        case sourceImage = "source_image"
        case notes
    }
}

public struct ForgeJobStatus: Decodable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let status: String
    public let photoCount: Int
    public let createdAt: String

    private enum CodingKeys: String, CodingKey {
        case id = "job_id"
        case name
        case status
        case photoCount = "photo_count"
        case createdAt = "created_at"
    }
}

public struct ForgeProjectCreatePayload: Encodable, Sendable {
    public let title: String
    public let description: String

    public init(title: String, description: String) {
        self.title = title
        self.description = description
    }
}

// MARK: - ForgeJobPayload

public struct ForgeJobPayload: Encodable, Sendable {
    public let name:   String
    public let photos: [ForgePhotoRecord]

    public init(name: String, photos: [ForgePhotoRecord]) {
        self.name   = name
        self.photos = photos
    }
}

public struct ForgePhotoRecord: Encodable, Sendable {
    public let index:    Int
    public let filename: String
    public let data:     String   // base64-encoded JPEG

    public init(index: Int, filename: String, data: String) {
        self.index    = index
        self.filename = filename
        self.data     = data
    }
}

// MARK: - ForgeJobResult

public struct ForgeJobResult: Decodable, Sendable {
    public let queued: Bool
    public let jobId:  String

    private enum CodingKeys: String, CodingKey {
        case queued
        case jobId = "job_id"
    }
}

// MARK: - ForgeModelRecord  (network / JarvisKit layer)

/// A 3-D model entry as stored on the JARVIS server.
/// The iOS layer maps this to its local `ForgeModel` struct (in ForgeViewModel).
public struct ForgeModelRecord: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let photoCount: Int
    public let createdAt: String
    public let usdzPath: String?

    public init(id: String, name: String, photoCount: Int,
                createdAt: String, usdzPath: String?) {
        self.id         = id
        self.name       = name
        self.photoCount = photoCount
        self.createdAt  = createdAt
        self.usdzPath   = usdzPath
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case photoCount  = "photo_count"
        case createdAt   = "created_at"
        case usdzPath    = "usdz_path"
    }
}
