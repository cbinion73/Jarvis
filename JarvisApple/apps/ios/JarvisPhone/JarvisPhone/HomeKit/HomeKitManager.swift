import HomeKit
import JarvisKit

/// Native HomeKit integration — direct device control without Home Assistant middleman.
@MainActor
final class HomeKitManager: NSObject, ObservableObject {

    static let shared = HomeKitManager()

    @Published var homes:          [HMHome] = []
    @Published var accessories:    [HMAccessory] = []
    @Published var isAuthorized    = false
    @Published var errorMessage:   String?

    private let homeManager = HMHomeManager()

    private override init() {
        super.init()
        homeManager.delegate = self
    }

    // MARK: - Query

    var lights: [HMAccessory] {
        accessories.filter { acc in
            acc.services.contains { $0.serviceType == HMServiceTypeLightbulb }
        }
    }

    var locks: [HMAccessory] {
        accessories.filter { acc in
            acc.services.contains { $0.serviceType == HMServiceTypeLockMechanism }
        }
    }

    var thermostats: [HMAccessory] {
        accessories.filter { acc in
            acc.services.contains { $0.serviceType == HMServiceTypeThermostat }
        }
    }

    // MARK: - Control

    func setLightOn(_ accessory: HMAccessory, on: Bool) async {
        await writeCharacteristic(in: accessory,
                                  serviceType: HMServiceTypeLightbulb,
                                  characteristicType: HMCharacteristicTypePowerState,
                                  value: on)
    }

    func setLightBrightness(_ accessory: HMAccessory, brightness: Int) async {
        await writeCharacteristic(in: accessory,
                                  serviceType: HMServiceTypeLightbulb,
                                  characteristicType: HMCharacteristicTypeBrightness,
                                  value: brightness)
    }

    func setThermostatTarget(_ accessory: HMAccessory, tempF: Double) async {
        let tempC = (tempF - 32) * 5 / 9
        await writeCharacteristic(in: accessory,
                                  serviceType: HMServiceTypeThermostat,
                                  characteristicType: HMCharacteristicTypeTargetTemperature,
                                  value: tempC)
    }

    /// Execute a home command string from JARVIS (e.g. "turn off living room lights")
    func executeCommand(_ command: String) async -> String {
        // Simple keyword matching — extend as needed
        let cmd = command.lowercased()
        var results: [String] = []

        if cmd.contains("lights off") || cmd.contains("turn off") && cmd.contains("light") {
            for light in lights {
                await setLightOn(light, on: false)
                results.append("Turned off \(light.name)")
            }
        } else if cmd.contains("lights on") || cmd.contains("turn on") && cmd.contains("light") {
            for light in lights {
                await setLightOn(light, on: true)
                results.append("Turned on \(light.name)")
            }
        }

        return results.isEmpty ? "No matching devices found" : results.joined(separator: ", ")
    }

    // MARK: - Private

    private func writeCharacteristic(
        in accessory: HMAccessory,
        serviceType: String,
        characteristicType: String,
        value: Any
    ) async {
        guard let service = accessory.services.first(where: { $0.serviceType == serviceType }),
              let char = service.characteristics.first(where: { $0.characteristicType == characteristicType })
        else { return }

        do {
            try await char.writeValue(value)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func reloadAccessories() {
        accessories = homes.flatMap { $0.accessories }
    }
}

// MARK: - HMHomeManagerDelegate

extension HomeKitManager: HMHomeManagerDelegate {

    nonisolated func homeManagerDidUpdateHomes(_ manager: HMHomeManager) {
        Task { @MainActor in
            self.homes         = manager.homes
            self.isAuthorized  = manager.authorizationStatus == .authorized
            self.reloadAccessories()
        }
    }

    nonisolated func homeManager(_ manager: HMHomeManager,
                                  didAdd home: HMHome) {
        Task { @MainActor in
            self.homes = manager.homes
            self.reloadAccessories()
        }
    }
}
