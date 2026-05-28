import Foundation

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
