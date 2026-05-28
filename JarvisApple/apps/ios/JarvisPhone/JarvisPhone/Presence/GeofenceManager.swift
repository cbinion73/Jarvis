import CoreLocation
import JarvisKit

/// More reliable home presence detection than WiFi SSID.
/// Uses CLCircularRegion geofencing — fires on entry/exit even before WiFi connects.
@MainActor
final class GeofenceManager: NSObject, ObservableObject {

    static let shared = GeofenceManager()

    @Published var isHome = false
    @Published var homeCoordinate: CLLocationCoordinate2D?

    private let manager      = CLLocationManager()
    private let regionID     = "jarvis.home.region"
    private let radiusMeters = 150.0   // ~500 ft — adjust to taste

    // UserDefaults keys
    private let latKey = "jarvis.home.lat"
    private let lonKey = "jarvis.home.lon"

    private override init() {
        super.init()
        manager.delegate              = self
        manager.desiredAccuracy       = kCLLocationAccuracyBest
        manager.allowsBackgroundLocationUpdates = true
        manager.pausesLocationUpdatesAutomatically = false
        loadSavedHome()
    }

    // MARK: - Setup

    func requestPermission() {
        manager.requestAlwaysAuthorization()
    }

    /// Save current location as home and start geofencing it.
    func setHomeToCurrentLocation() {
        manager.requestLocation()
    }

    /// Start monitoring the saved home region.
    func startMonitoring() {
        guard let coord = homeCoordinate else { return }
        let region = CLCircularRegion(
            center: coord,
            radius: radiusMeters,
            identifier: regionID
        )
        region.notifyOnEntry = true
        region.notifyOnExit  = true
        manager.startMonitoring(for: region)
        manager.requestState(for: region)   // get current state immediately
    }

    // MARK: - Persistence

    private func loadSavedHome() {
        let ud = UserDefaults.standard
        let lat = ud.double(forKey: latKey)
        let lon = ud.double(forKey: lonKey)
        if lat != 0 && lon != 0 {
            homeCoordinate = CLLocationCoordinate2D(latitude: lat, longitude: lon)
        }
    }

    private func saveHome(_ coord: CLLocationCoordinate2D) {
        homeCoordinate = coord
        UserDefaults.standard.set(coord.latitude,  forKey: latKey)
        UserDefaults.standard.set(coord.longitude, forKey: lonKey)
    }

    // MARK: - Report to server

    private func reportPresence(arrived: Bool) {
        isHome = arrived
        Task {
            guard let url = URL(string: JARVISEnvironment.baseURL.absoluteString + "/api/apple/presence") else { return }
            let payload: [String: Any] = [
                "event":     arrived ? "arrived" : "left",
                "source":    "geofence",
                "timestamp": ISO8601DateFormatter().string(from: Date()),
            ]
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
            _ = try? await URLSession.shared.data(for: req)
        }
    }
}

// MARK: - CLLocationManagerDelegate

extension GeofenceManager: @preconcurrency CLLocationManagerDelegate {

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didEnterRegion region: CLRegion) {
        guard region.identifier == regionID else { return }
        Task { @MainActor in self.reportPresence(arrived: true) }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didExitRegion region: CLRegion) {
        guard region.identifier == regionID else { return }
        Task { @MainActor in self.reportPresence(arrived: false) }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didDetermineState state: CLRegionState,
                                     for region: CLRegion) {
        guard region.identifier == regionID else { return }
        Task { @MainActor in self.isHome = (state == .inside) }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        Task { @MainActor in
            // First location fix after setHomeToCurrentLocation() was called
            if self.homeCoordinate == nil {
                self.saveHome(loc.coordinate)
                self.startMonitoring()
            }
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            if status == .authorizedAlways { self.startMonitoring() }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didFailWithError error: Error) {}
}
