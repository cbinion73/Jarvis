import Foundation
import WatchConnectivity
import JarvisKit
import CoreLocation

/// Manages the iPhone side of the Watch Connectivity session.
///
/// Responsibilities:
/// - Sends briefing + needs data to Watch whenever it's freshly loaded.
/// - Responds to Watch requests for a data refresh.
/// - Keeps `applicationContext` up-to-date so Watch always has the latest snapshot.
@MainActor
final class WatchSessionManager: NSObject, ObservableObject {

    static let shared = WatchSessionManager()

    private var session: WCSession?

    private override init() {
        super.init()
        guard WCSession.isSupported() else { return }
        let s = WCSession.default
        s.delegate = self
        s.activate()
        session = s
    }

    // MARK: - Push data to Watch

    func sendBriefing(_ packet: BriefingPacket) {
        guard let session, session.activationState == .activated,
              session.isWatchAppInstalled else { return }

        // Build a lightweight dictionary for applicationContext
        let context: [String: Any] = [
            "greeting":      packet.greeting,
            "mode":          packet.mode,
            "needs_count":   packet.needsItems.count,
            "briefing_top3": packet.briefingItems.prefix(3).map { ["text": $0.text, "priority": $0.priority] },
            "ts":            ISO8601DateFormatter().string(from: Date()),
        ]

        try? session.updateApplicationContext(context)
        session.transferUserInfo(context)   // also queue for reliable delivery
    }

    func sendNeeds(_ items: [NeedsItem]) {
        guard let session, session.activationState == .activated,
              session.isWatchAppInstalled else { return }

        let payload: [String: Any] = [
            "needs": items.map { ["id": $0.id, "text": $0.text, "agent": $0.agent, "risk": $0.risk] },
            "ts": ISO8601DateFormatter().string(from: Date()),
        ]
        session.transferUserInfo(payload)
    }

    /// Pushes live WeatherKit snapshot to Watch (called after WeatherManager loads data).
    func sendWeather(_ wx: CurrentWeatherSnapshot, forecast: [DayForecastSnapshot]) {
        guard let session, session.activationState == .activated,
              session.isWatchAppInstalled else { return }

        let forecastPayload: [[String: String]] = forecast.prefix(3).map {
            ["name": $0.name, "high": $0.highString, "low": $0.lowString, "condition": $0.condition]
        }
        let payload: [String: Any] = [
            "weather": [
                "temp":       wx.tempString,
                "feels_like": wx.feelsLikeString,
                "condition":  wx.condition,
                "humidity":   wx.humidityString,
                "wind":       wx.wind,
                "visual_key": wx.visualKey,
                "forecast":   forecastPayload,
            ] as [String: Any],
            "ts": ISO8601DateFormatter().string(from: Date()),
        ]
        try? session.updateApplicationContext(payload)
        session.transferUserInfo(payload)
    }
}

// MARK: - WCSessionDelegate

extension WatchSessionManager: @preconcurrency WCSessionDelegate {

    nonisolated func session(
        _ session: WCSession,
        activationDidCompleteWith activationState: WCSessionActivationState,
        error: Error?
    ) {
        if let error { print("[JARVIS Watch] Session error: \(error)") }
    }

    nonisolated func sessionDidBecomeInactive(_ session: WCSession) {}
    nonisolated func sessionDidDeactivate(_ session: WCSession) {
        session.activate()
    }

    /// Watch requested a data refresh
    nonisolated func session(
        _ session: WCSession,
        didReceiveMessage message: [String: Any],
        replyHandler: @escaping ([String: Any]) -> Void
    ) {
        guard message["action"] as? String == "refresh" else {
            replyHandler(["ok": false])
            return
        }
        Task { @MainActor in
            do {
                let packet = try await AppleAPIClient.shared.fetchBriefing()
                let needs  = try await AppleAPIClient.shared.fetchNeeds()
                self.sendBriefing(packet)
                self.sendNeeds(needs)
                replyHandler(["ok": true, "needs_count": needs.count])
            } catch {
                replyHandler(["ok": false, "error": error.localizedDescription])
            }
        }
    }
}
