import MediaPlayer
import MusicKit
import SwiftUI
import JarvisKit

/// Observes the system music player and pushes Now Playing info to JARVIS.
/// Uses MediaPlayer (no auth needed) for metadata + MusicKit for album art.
@MainActor
final class NowPlayingManager: ObservableObject {

    static let shared = NowPlayingManager()

    @Published var title:      String?
    @Published var artist:     String?
    @Published var album:      String?
    @Published var artwork:    UIImage?
    @Published var isPlaying   = false
    @Published var elapsedTime: TimeInterval = 0
    @Published var duration:    TimeInterval = 0

    private let player = MPMusicPlayerController.systemMusicPlayer
    private var pushDebounceTask: Task<Void, Never>?

    private init() {
        setupNotifications()
        refresh()
    }

    // MARK: - Public

    func refresh() {
        let item = player.nowPlayingItem
        title    = item?.title
        artist   = item?.artist
        album    = item?.albumTitle
        artwork  = item?.artwork?.image(at: CGSize(width: 120, height: 120))
        isPlaying = player.playbackState == .playing
        elapsedTime = player.currentPlaybackTime
        duration    = item?.playbackDuration ?? 0
        schedulePush()
    }

    // MARK: - Notifications

    private func setupNotifications() {
        player.beginGeneratingPlaybackNotifications()
        let nc = NotificationCenter.default

        nc.addObserver(forName: .MPMusicPlayerControllerNowPlayingItemDidChange,
                       object: player, queue: .main) { [weak self] _ in
            Task { @MainActor [weak self] in self?.refresh() }
        }
        nc.addObserver(forName: .MPMusicPlayerControllerPlaybackStateDidChange,
                       object: player, queue: .main) { [weak self] _ in
            Task { @MainActor [weak self] in self?.refresh() }
        }
    }

    // MARK: - Push to JARVIS (debounced 2 s)

    private func schedulePush() {
        pushDebounceTask?.cancel()
        pushDebounceTask = Task {
            try? await Task.sleep(for: .seconds(2))
            guard !Task.isCancelled else { return }
            await push()
        }
    }

    private func push() async {
        guard let title else { return }
        var artworkBase64: String?
        // Encode artwork as base64 thumbnail (≤ 80×80)
        if let img = artwork,
           let small = img.resize(to: CGSize(width: 80, height: 80)),
           let jpeg  = small.jpegData(compressionQuality: 0.6) {
            artworkBase64 = jpeg.base64EncodedString()
        }

        let payload = NowPlayingPayload(
            title: title,
            artist: artist ?? "",
            album: album ?? "",
            isPlaying: isPlaying,
            source: "mediaplayerkit",
            artworkBase64: artworkBase64
        )
        try? await AppleAPIClient.shared.postAcknowledged("/api/apple/now-playing", body: payload)
    }
}

private struct NowPlayingPayload: Encodable, Sendable {
    let title: String
    let artist: String
    let album: String
    let isPlaying: Bool
    let source: String
    let artworkBase64: String?

    enum CodingKeys: String, CodingKey {
        case title, artist, album, source
        case isPlaying = "is_playing"
        case artworkBase64 = "artwork_b64"
    }
}

// MARK: - UIImage resize helper

private extension UIImage {
    func resize(to size: CGSize) -> UIImage? {
        UIGraphicsBeginImageContextWithOptions(size, false, 0)
        defer { UIGraphicsEndImageContext() }
        draw(in: CGRect(origin: .zero, size: size))
        return UIGraphicsGetImageFromCurrentImageContext()
    }
}
