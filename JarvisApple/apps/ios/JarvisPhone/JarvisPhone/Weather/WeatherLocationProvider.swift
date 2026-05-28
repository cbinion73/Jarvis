import Foundation
import CoreLocation

/// Wraps CLLocationManager with async/await to hand a single CLLocation to WeatherManager.
@MainActor
final class WeatherLocationProvider: NSObject, ObservableObject {

    static let shared = WeatherLocationProvider()

    @Published var location: CLLocation?
    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined

    private let manager = CLLocationManager()

    private override init() {
        super.init()
        manager.delegate        = self
        manager.desiredAccuracy = kCLLocationAccuracyKilometer
        authorizationStatus     = manager.authorizationStatus
    }

    func requestAndFetch() {
        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways:
            manager.requestLocation()
        default:
            break
        }
    }
}

extension WeatherLocationProvider: @preconcurrency CLLocationManagerDelegate {

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        Task { @MainActor in self.location = loc }
    }

    nonisolated func locationManager(_ manager: CLLocationManager,
                                     didFailWithError error: Error) {
        // Silently swallow location errors; WeatherView shows an empty state
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            self.authorizationStatus = status
            if status == .authorizedWhenInUse || status == .authorizedAlways {
                manager.requestLocation()
            }
        }
    }
}
