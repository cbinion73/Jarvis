import Foundation

// MARK: - JARVISEnvironment

/// JARVIS environment configuration.
///
/// Set `JARVISEnvironment.current` once at app launch (e.g. in the App's `init`)
/// before `AppleAPIClient.shared` performs any requests:
///
/// ```swift
/// JARVISEnvironment.current = .production
/// ```
public enum JARVISEnvironment {
    private static let baseURLInfoKey = "JARVIS_BASE_URL"
    private static let baseURLEnvKey = "JARVIS_BASE_URL"

    // MARK: - Target

    public enum Target: Sendable {
        /// https://jarvis.teambinion.org — production server (default)
        case production
    }

    // MARK: - State

    /// The active deployment target. Defaults to `.production`.
    /// `nonisolated(unsafe)` because it is set once at app launch before
    /// any concurrent work begins — the caller is responsible for timing.
    public nonisolated(unsafe) static var current: Target = .production

    // MARK: - Derived URL

    public static var baseURL: URL {
        if let override = configuredBaseURL() {
            return override
        }
        return URL(string: "https://jarvis.teambinion.org")!
    }

    public static var isOverrideActive: Bool {
        configuredBaseURL() != nil
    }

    public static var environmentLabel: String {
        isOverrideActive ? "Local Override" : "Production"
    }

    public static var environmentSummary: String {
        if isOverrideActive {
            return "This app is temporarily pointed at a custom JARVIS backend for local runtime verification."
        }
        return "This app is locked to the live JARVIS production server."
    }

    private static func configuredBaseURL() -> URL? {
        let bundleValue = Bundle.main.object(forInfoDictionaryKey: baseURLInfoKey) as? String
        let envValue = ProcessInfo.processInfo.environment[baseURLEnvKey]
        guard let candidate = (envValue?.isEmpty == false ? envValue : bundleValue)?
            .trimmingCharacters(in: .whitespacesAndNewlines),
              !candidate.isEmpty
        else {
            return nil
        }
        return URL(string: candidate)
    }
}
