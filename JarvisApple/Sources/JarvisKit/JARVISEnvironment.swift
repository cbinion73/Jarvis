import Foundation

// MARK: - JARVISEnvironment

/// JARVIS environment configuration.
///
/// Set `JARVISEnvironment.current` once at app launch (e.g. in the App's `init`)
/// before `AppleAPIClient.shared` performs any requests:
///
/// ```swift
/// JARVISEnvironment.current = .tailscale
/// ```
public enum JARVISEnvironment: Sendable {

    // MARK: - Target

    public enum Target: Sendable {
        /// http://localhost:8787  — local development
        case local
        /// https://jarvis.internal — remote access via Tailscale VPN
        case tailscale
        /// Arbitrary explicit URL
        case custom(URL)
    }

    // MARK: - State

    /// The active deployment target. Defaults to `.local`.
    public static var current: Target = .local

    // MARK: - Derived URL

    public static var baseURL: URL {
        switch current {
        case .local:
            // swiftlint:disable:next force_unwrapping
            return URL(string: "http://localhost:8787")!
        case .tailscale:
            // The Tailscale hostname is read from UserDefaults when set;
            // falls back to the canonical internal hostname.
            if let stored = UserDefaults.standard.string(forKey: "jarvis.tailscale.url"),
               let url = URL(string: stored) {
                return url
            }
            // swiftlint:disable:next force_unwrapping
            return URL(string: "https://jarvis.internal")!
        case .custom(let url):
            return url
        }
    }
}
