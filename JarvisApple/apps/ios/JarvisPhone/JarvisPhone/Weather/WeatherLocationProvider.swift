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
    @Published var isRequestingLocation = false
    @Published var lastErrorMessage: String?

    private let manager = CLLocationManager()
    private var fallbackTask: Task<Void, Never>?

    /// If the cached location is younger than this, skip a fresh CLLocation request.
    private let staleness: TimeInterval = 30 * 60  // 30 minutes

    private override init() {
        super.init()
        manager.delegate        = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        authorizationStatus     = manager.authorizationStatus

        // Restore the last persisted location immediately so WeatherView can
        // display cached weather without triggering a permission prompt.
        location = Self.loadPersistedLocation()
    }

    // MARK: - Public

    func requestAndFetch(force: Bool = false, userInitiated: Bool = false) {
        authorizationStatus = manager.authorizationStatus

        // If we already have a recent location, there's nothing to do.
        if !force,
           let loc = location,
           abs(loc.timestamp.timeIntervalSinceNow) < staleness {
            return
        }

        switch manager.authorizationStatus {
        case .notDetermined:
            guard userInitiated else {
                isRequestingLocation = false
                lastErrorMessage = nil
                return
            }
            requestPermission()
        case .authorizedWhenInUse, .authorizedAlways:
            beginLocationRequest()
        default:
            isRequestingLocation = false
            lastErrorMessage = "Location access is disabled for JARVIS."
            break
        }
    }

    func requestPermission() {
        authorizationStatus = manager.authorizationStatus
        guard authorizationStatus == .notDetermined else {
            requestAndFetch(force: true)
            return
        }
        lastErrorMessage = nil
        isRequestingLocation = true
        manager.requestWhenInUseAuthorization()
    }

    private func beginLocationRequest() {
        lastErrorMessage = nil
        isRequestingLocation = true

        if let managerLocation = manager.location {
            location = managerLocation
            persistLocation(managerLocation)
        }

        manager.requestLocation()
        scheduleContinuousUpdateFallback()
    }

    private func scheduleContinuousUpdateFallback() {
        fallbackTask?.cancel()
        fallbackTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(4))
            guard !Task.isCancelled else { return }
            await MainActor.run {
                guard let self, self.isRequestingLocation else { return }
                self.manager.startUpdatingLocation()
                self.lastErrorMessage = "Still looking for a GPS fix. Try stepping near a window, or check Precise Location in Settings."
            }
        }
    }

    private func finishLocationRequest() {
        isRequestingLocation = false
        fallbackTask?.cancel()
        fallbackTask = nil
        manager.stopUpdatingLocation()
    }

    // MARK: - Persistence

    private static let persistKey = "jarvis.weather.lastLocation"

    private static func loadPersistedLocation() -> CLLocation? {
        guard let arr = UserDefaults.standard.array(forKey: persistKey) as? [Double],
              arr.count == 3 else { return nil }
        let timestamp = Date(timeIntervalSince1970: arr[2])
        let loc = CLLocation(
            coordinate: CLLocationCoordinate2D(latitude: arr[0], longitude: arr[1]),
            altitude: 0,
            horizontalAccuracy: kCLLocationAccuracyKilometer,
            verticalAccuracy: -1,
            timestamp: timestamp
        )
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
            self.lastErrorMessage = nil
            self.finishLocationRequest()
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didFailWithError error: Error) {
        let message = Self.locationErrorMessage(error)
        Task { @MainActor in
            self.isRequestingLocation = false
            self.lastErrorMessage = message
            self.fallbackTask?.cancel()
            self.fallbackTask = nil
            self.manager.stopUpdatingLocation()
        }
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            self.authorizationStatus = status
            if status == .authorizedWhenInUse || status == .authorizedAlways {
                self.beginLocationRequest()
            }
        }
    }

    private nonisolated static func locationErrorMessage(_ error: Error) -> String {
        guard let clError = error as? CLError else {
            return error.localizedDescription
        }

        switch clError.code {
        case .denied:
            return "Location access is disabled for JARVIS."
        case .locationUnknown:
            return "iOS could not get a location fix yet. Try again, or step near a window."
        case .network:
            return "iOS could not use the network to determine location."
        default:
            return clError.localizedDescription
        }
    }
}
