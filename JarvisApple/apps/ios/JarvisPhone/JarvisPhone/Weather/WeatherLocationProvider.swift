import Foundation
import CoreLocation

/// Wraps CLLocationManager for async/await use by WeatherManager.
///
/// Fixes:
/// - Last-known location is persisted to UserDefaults so the app never needs
///   to show the location prompt after the first grant.
/// - `requestAndFetch()` is a no-op when a fresh location is already available
///   (avoids re-requesting on every WeatherView `.onAppear`).
@MainActor
final class WeatherLocationProvider: NSObject, ObservableObject {

    static let shared = WeatherLocationProvider()

    @Published var location: CLLocation?
    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined

    private let manager = CLLocationManager()

    /// If the cached location is younger than this, skip a fresh CLLocation request.
    private let staleness: TimeInterval = 30 * 60  // 30 minutes

    private override init() {
        super.init()
        manager.delegate        = self
        manager.desiredAccuracy = kCLLocationAccuracyKilometer
        authorizationStatus     = manager.authorizationStatus

        // Restore the last persisted location immediately so WeatherView can
        // display cached weather without triggering a permission prompt.
        location = Self.loadPersistedLocation()
    }

    // MARK: - Public

    func requestAndFetch() {
        // If we already have a recent location, there's nothing to do.
        if let loc = location,
           abs(loc.timestamp.timeIntervalSinceNow) < staleness {
            return
        }

        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways:
            manager.requestLocation()
        default:
            break
        }
    }

    // MARK: - Persistence

    private static let persistKey = "jarvis.weather.lastLocation"

    private static func loadPersistedLocation() -> CLLocation? {
        guard let arr = UserDefaults.standard.array(forKey: persistKey) as? [Double],
              arr.count == 3 else { return nil }
        let loc = CLLocation(latitude: arr[0], longitude: arr[1])
        // Restore the saved timestamp so staleness checks are correct
        let age = Date().timeIntervalSince1970 - arr[2]
        // Only use cache if it's less than 24 h old
        guard age < 86_400 else { return nil }
        return loc
    }

    private func persistLocation(_ loc: CLLocation) {
        let arr: [Double] = [
            loc.coordinate.latitude,
            loc.coordinate.longitude,
            Date().timeIntervalSince1970,
        ]
        UserDefaults.standard.set(arr, forKey: Self.persistKey)
    }
}

// MARK: - CLLocationManagerDelegate
// @preconcurrency removed — CLLocationManagerDelegate is already properly
// marked for Swift 6 concurrency in the iOS 26 SDK.

extension WeatherLocationProvider: CLLocationManagerDelegate {

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        Task { @MainActor in
            self.location = loc
            self.persistLocation(loc)
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didFailWithError error: Error) {
        // Silently ignore — WeatherView handles the nil-location empty state.
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            self.authorizationStatus = status
            if status == .authorizedWhenInUse || status == .authorizedAlways {
                // Only request a fresh fix if we don't already have one.
                if self.location == nil {
                    self.manager.requestLocation()
                }
            }
        }
    }
}
