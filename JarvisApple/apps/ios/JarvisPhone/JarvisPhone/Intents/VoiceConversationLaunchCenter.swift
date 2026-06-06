import Foundation

struct VoiceConversationLaunchRequest: Codable, Equatable {
    let utterance: String
    let source: String
    let createdAt: Date

    init(utterance: String = "", source: String) {
        self.utterance = utterance.trimmingCharacters(in: .whitespacesAndNewlines)
        self.source = source
        self.createdAt = Date()
    }

    func isFresh(maxAge: TimeInterval = 20) -> Bool {
        Date().timeIntervalSince(createdAt) <= maxAge
    }
}

@MainActor
final class VoiceConversationLaunchCenter: ObservableObject {

    static let shared = VoiceConversationLaunchCenter()

    @Published private(set) var pendingLaunch: VoiceConversationLaunchRequest?

    private let defaults = UserDefaults(suiteName: "group.com.binion.jarvisphone")
    private let key = "jarvis.voice.pendingLaunch"

    private init() {}

    func queueLaunch(_ launch: VoiceConversationLaunchRequest) {
        guard let defaults else { return }
        if let encoded = try? JSONEncoder().encode(launch) {
            defaults.set(encoded, forKey: key)
            pendingLaunch = launch
        }
    }

    func refreshFromStore() {
        guard pendingLaunch == nil else { return }
        guard let defaults, let data = defaults.data(forKey: key) else { return }
        guard let decoded = try? JSONDecoder().decode(VoiceConversationLaunchRequest.self, from: data) else {
            clearStoredLaunch()
            return
        }
        guard decoded.isFresh() else {
            clearStoredLaunch()
            return
        }
        pendingLaunch = decoded
    }

    func consumePendingLaunch(maxAge: TimeInterval = 20) -> VoiceConversationLaunchRequest? {
        if let pendingLaunch {
            clearStoredLaunch()
            self.pendingLaunch = nil
            return pendingLaunch.isFresh(maxAge: maxAge) ? pendingLaunch : nil
        }
        guard let defaults, let data = defaults.data(forKey: key) else { return nil }
        let decoded = try? JSONDecoder().decode(VoiceConversationLaunchRequest.self, from: data)
        clearStoredLaunch()
        pendingLaunch = nil
        guard let decoded, decoded.isFresh(maxAge: maxAge) else { return nil }
        return decoded
    }

    private func clearStoredLaunch() {
        defaults?.removeObject(forKey: key)
    }
}
