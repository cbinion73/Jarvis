import Foundation
import WatchConnectivity
import WidgetKit

/// Receives briefing and needs data from the paired iPhone via WatchConnectivity.
/// Also persists the latest snapshot to UserDefaults so complications can read it.
@MainActor
final class WatchViewModel: NSObject, ObservableObject {

    static let shared = WatchViewModel()

    // MARK: - Published state

    @Published var greeting   = "Good morning, Sir."
    @Published var mode       = "morning"
    @Published var needsCount = 0
    @Published var briefTop3: [[String: String]] = []
    @Published var needsItems: [[String: String]] = []
    @Published var lastUpdate: Date?
    @Published var isRefreshing = false

    // Weather (pushed from iPhone)
    @Published var weatherTemp:       String = "--°"
    @Published var weatherFeelsLike:  String = ""
    @Published var weatherCondition:  String = ""
    @Published var weatherHumidity:   String = ""
    @Published var weatherWind:       String = ""
    @Published var weatherVisualKey:  String? = nil
    @Published var weatherForecast:   [[String: String]] = []

    // MARK: - UserDefaults keys (shared with complication via App Group if added later)

    private let udGreeting    = "jarvis.watch.greeting"
    private let udMode        = "jarvis.watch.mode"
    private let udNeedsCount  = "jarvis.watch.needs_count"
    private let udBriefTop3   = "jarvis.watch.brief_top3"
    private let udLastUpdate  = "jarvis.watch.last_update"

    // MARK: - Init

    private override init() {
        super.init()
        loadFromDefaults()
        guard WCSession.isSupported() else { return }
        WCSession.default.delegate = self
        WCSession.default.activate()
    }

    // MARK: - Refresh (request from iPhone)

    func requestRefresh() {
        guard WCSession.default.activationState == .activated,
              WCSession.default.isReachable else { return }
        isRefreshing = true
        WCSession.default.sendMessage(["action": "refresh"]) { [weak self] reply in
            Task { @MainActor [weak self] in
                self?.isRefreshing = false
                if let count = reply["needs_count"] as? Int {
                    self?.needsCount = count
                }
            }
        } errorHandler: { [weak self] _ in
            Task { @MainActor [weak self] in self?.isRefreshing = false }
        }
    }

    // MARK: - Persistence

    private func loadFromDefaults() {
        let ud = UserDefaults.standard
        greeting    = ud.string(forKey: udGreeting)   ?? greeting
        mode        = ud.string(forKey: udMode)       ?? mode
        needsCount  = ud.integer(forKey: udNeedsCount)
        briefTop3   = (ud.array(forKey: udBriefTop3) as? [[String: String]]) ?? []
        if let ts = ud.object(forKey: udLastUpdate) as? Date { lastUpdate = ts }
    }

    private func saveToDefaults() {
        let ud = UserDefaults.standard
        ud.set(greeting,   forKey: udGreeting)
        ud.set(mode,       forKey: udMode)
        ud.set(needsCount, forKey: udNeedsCount)
        ud.set(briefTop3,  forKey: udBriefTop3)
        ud.set(Date(),     forKey: udLastUpdate)
        WidgetCenter.shared.reloadAllTimelines()
    }

    // MARK: - Apply context

    fileprivate func applyContext(_ info: [String: Any]) {
        if let g = info["greeting"]    as? String { greeting   = g }
        if let m = info["mode"]        as? String { mode       = m }
        if let n = info["needs_count"] as? Int    { needsCount = n }
        if let b = info["briefing_top3"] as? [[String: String]] { briefTop3 = b }
        if let needs = info["needs"]   as? [[String: String]]   { needsItems = needs }

        // Weather payload
        if let wx = info["weather"] as? [String: Any] {
            if let t  = wx["temp"]        as? String { weatherTemp      = t }
            if let fl = wx["feels_like"]  as? String { weatherFeelsLike = fl }
            if let c  = wx["condition"]   as? String { weatherCondition = c }
            if let h  = wx["humidity"]    as? String { weatherHumidity  = h }
            if let w  = wx["wind"]        as? String { weatherWind      = w }
            if let vk = wx["visual_key"]  as? String { weatherVisualKey = vk }
            if let fc = wx["forecast"]    as? [[String: String]] { weatherForecast = fc }
        }

        lastUpdate = Date()
        saveToDefaults()
    }
}

// MARK: - WCSessionDelegate

extension WatchViewModel: @preconcurrency WCSessionDelegate {
    // @preconcurrency suppresses Swift 6 Sendable warnings for this ObjC-era protocol

    nonisolated func session(
        _ session: WCSession,
        activationDidCompleteWith state: WCSessionActivationState,
        error: Error?
    ) {}

    nonisolated func session(_ session: WCSession, didReceiveApplicationContext context: [String: Any]) {
        // Serialize to Data (Sendable) before crossing the actor boundary
        guard let data = try? JSONSerialization.data(withJSONObject: context) else { return }
        Task { @MainActor [data] in
            guard let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            self.applyContext(dict)
        }
    }

    nonisolated func session(_ session: WCSession, didReceiveUserInfo userInfo: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: userInfo) else { return }
        Task { @MainActor [data] in
            guard let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            self.applyContext(dict)
        }
    }
}
