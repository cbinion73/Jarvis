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

    // MARK: - Target

    public enum Target: Sendable {
        /// https://jarvis.teambinion.org — production server (default)
        case production
        /// http://localhost:8787  — local development
        case local
        /// Tailscale VPN direct access
        case tailscale
        /// Arbitrary explicit URL
        case custom(URL)
    }

    // MARK: - State

    /// The active deployment target. Defaults to `.production`.
    /// `nonisolated(unsafe)` because it is set once at app launch before
    /// any concurrent work begins — the caller is responsible for timing.
    public nonisolated(unsafe) static var current: Target = .production

    // MARK: - Derived URL

    public static var baseURL: URL {
        switch current {
        case .production:
            return URL(string: "https://jarvis.teambinion.org")!
        case .local:
            return URL(string: "http://localhost:8787")!
        case .tailscale:
            if let stored = UserDefaults.standard.string(forKey: "jarvis.tailscale.url"),
               let url = URL(string: stored) {
                return url
            }
            return URL(string: "https://jarvis.internal")!
        case .custom(let url):
            return url
        }
    }
}
