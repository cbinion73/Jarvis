import Foundation
import NetworkExtension
import CoreLocation
import JarvisKit

/// Detects when the iPhone joins or leaves the home WiFi network and
/// reports the presence event to the JARVIS server automatically.
///
/// **First launch:** saves the current SSID as the home network.
/// **Subsequent launches:** fires `arrived_home` or `left_home` when the SSID changes.
///
/// Requires:
///  - `com.apple.developer.networking.wifi-info` entitlement (Access WiFi Information)
///  - Location "When In Use" permission (iOS requires it for SSID access)
@MainActor
final class WiFiPresenceMonitor: NSObject, ObservableObject {

    static let shared = WiFiPresenceMonitor()

    @Published var currentSSID: String?
    @Published var isHome = false

    private let client = AppleAPIClient.shared
    private let locationManager = CLLocationManager()

    private var lastReportedSSID: String?
    private var lastPresenceEvent: String?

    // MARK: - Persistence keys

    private let homeSSIDKey  = "jarvis.home.ssid"
    private let actorIdKey   = "jarvis-claimed-user-v1"   // matches JS localStorage key

    var homeSSID: String? {
        get { UserDefaults.standard.string(forKey: homeSSIDKey) }
        set { UserDefaults.standard.set(newValue, forKey: homeSSIDKey) }
    }

    var actorId: String {
        UserDefaults.standard.string(forKey: actorIdKey) ?? "chris"
    }

    // MARK: - Init

    private override init() {
        super.init()
        locationManager.delegate = self
    }

    // MARK: - Public API

    /// Call once at app launch. Uses location permission only after the user
    /// grants it elsewhere; startup should never trigger the system prompt.
    func start() {
        switch locationManager.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways:
            Task { await checkAndReport() }
        case .notDetermined:
            break
        default:
            print("[JARVIS WiFi] Location permission denied — WiFi presence unavailable.")
        }
    }

    /// Re-check current network (call when app enters foreground).
    func refresh() {
        Task { await checkAndReport() }
    }

    // MARK: - Core logic

    func checkAndReport() async {
        let network = await NEHotspotNetwork.fetchCurrent()
        let ssid    = network?.ssid
        currentSSID = ssid

        // Skip if nothing changed
        guard ssid != lastReportedSSID else { return }
        lastReportedSSID = ssid

        // First launch — save current SSID as home and mark present
        if homeSSID == nil {
            if let ssid {
                homeSSID = ssid
                isHome = true
                print("[JARVIS WiFi] Saved '\(ssid)' as home network.")
                await report(.arrivedHome)
            }
            return
        }

        let nowHome = ssid == homeSSID
        isHome = nowHome

        let event: PresenceEvent = nowHome ? .arrivedHome : .leftHome

        // Avoid duplicate reports for the same event
        guard event.rawValue != lastPresenceEvent else { return }
        lastPresenceEvent = event.rawValue

        print("[JARVIS WiFi] \(event.rawValue) (SSID: \(ssid ?? "none"))")
        await report(event)
    }

    // MARK: - Network call

    private func report(_ event: PresenceEvent) async {
        do {
            try await client.reportPresence(actorId: actorId, event: event, lat: 0, lon: 0)
            print("[JARVIS WiFi] Reported \(event.rawValue) for \(actorId)")
        } catch {
            print("[JARVIS WiFi] Presence report failed: \(error.localizedDescription)")
        }
    }
}

// MARK: - CLLocationManagerDelegate

extension WiFiPresenceMonitor: CLLocationManagerDelegate {
    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        // Read authorizationStatus from the shared instance on MainActor — don't
        // send the delegate-supplied `manager` reference across the isolation boundary.
        Task { @MainActor in
            switch self.locationManager.authorizationStatus {
            case .authorizedWhenInUse, .authorizedAlways:
                await self.checkAndReport()
            default:
                break
            }
        }
    }
}
