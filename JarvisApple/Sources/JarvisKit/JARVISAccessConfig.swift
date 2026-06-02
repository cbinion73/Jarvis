import Foundation

enum JARVISAccessConfig {
    private static let clientIdInfoKey = "JARVIS_CF_ACCESS_CLIENT_ID"
    private static let clientSecretInfoKey = "JARVIS_CF_ACCESS_CLIENT_SECRET"
    private static let clientIdEnvKey = "JARVIS_CF_ACCESS_CLIENT_ID"
    private static let clientSecretEnvKey = "JARVIS_CF_ACCESS_CLIENT_SECRET"

    static func apply(to request: inout URLRequest) {
        if let clientId = value(infoKey: clientIdInfoKey, envKey: clientIdEnvKey) {
            request.setValue(clientId, forHTTPHeaderField: "CF-Access-Client-Id")
        }
        if let clientSecret = value(infoKey: clientSecretInfoKey, envKey: clientSecretEnvKey) {
            request.setValue(clientSecret, forHTTPHeaderField: "CF-Access-Client-Secret")
        }
    }

    private static func value(infoKey: String, envKey: String) -> String? {
        let bundleValue = Bundle.main.object(forInfoDictionaryKey: infoKey) as? String
        let envValue = ProcessInfo.processInfo.environment[envKey]
        let candidate = (bundleValue?.isEmpty == false ? bundleValue : envValue)?.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let candidate, !candidate.isEmpty else { return nil }
        return candidate
    }
}
