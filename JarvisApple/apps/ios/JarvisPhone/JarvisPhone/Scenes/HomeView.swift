import SwiftUI
import HomeKit
import JarvisKit

// MARK: - HomeView  "The Control Room"

struct HomeView: View {

    @StateObject private var hk = HomeKitManager.shared
    @State private var serverState: HomeState?
    @State private var appState: AppStateOverview?
    @State private var isLoadingServerState = false
    @State private var serverError: String?

    private let amber = Color.orange

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {
                        liveStateSection

                        if !hk.isAuthorized {
                            setupState
                        } else if hk.accessories.isEmpty {
                            emptyState
                        } else {
                            contentView
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Home")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 6) {
                        // All lights off quick action
                        if !hk.lights.isEmpty {
                            Button {
                                Task {
                                    for light in hk.lights {
                                        await hk.setLightOn(light, on: false)
                                    }
                                }
                            } label: {
                                Label("All Off", systemImage: "lightbulb.slash.fill")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(amber)
                            }
                            .glassEffect(in: Capsule())
                        }

                        Button {
                            Task { await loadServerState() }
                        } label: {
                            if isLoadingServerState {
                                ProgressView().tint(amber).scaleEffect(0.8)
                            } else {
                                Image(systemName: "arrow.clockwise")
                                    .foregroundStyle(amber)
                            }
                        }
                        .glassEffect(in: Circle())
                    }
                }
            }
        }
        .task { await loadServerState() }
        .refreshable { await loadServerState() }
    }

    // MARK: - Content

    private var contentView: some View {
        VStack(spacing: 14) {
            // ── Status banner ──────────────────────────────────
            HStack(spacing: 14) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(hk.homes.first?.name ?? "Home")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text("\(hk.accessories.count) devices paired")
                        .font(.caption)
                        .foregroundStyle(amber.opacity(0.8))
                }
                Spacer()
                Image(systemName: "house.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(amber.opacity(0.7))
            }
            .padding(16)
            .glassEffect(in: RoundedRectangle(cornerRadius: 16))

            // ── Lights ─────────────────────────────────────────
            if !hk.lights.isEmpty {
                HomeSection(title: "Lights", icon: "lightbulb.fill", accent: amber) {
                    LazyVGrid(
                        columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2),
                        spacing: 10
                    ) {
                        ForEach(hk.lights, id: \.uniqueIdentifier) { light in
                            LightTile(accessory: light)
                        }
                    }
                }
            }

            // ── Locks ──────────────────────────────────────────
            if !hk.locks.isEmpty {
                HomeSection(title: "Locks", icon: "lock.shield.fill", accent: .green) {
                    ForEach(hk.locks, id: \.uniqueIdentifier) { lock in
                        LockRow(accessory: lock)
                    }
                }
            }

            // ── Climate ────────────────────────────────────────
            if !hk.thermostats.isEmpty {
                HomeSection(title: "Climate", icon: "thermometer.medium", accent: Color(red: 0.4, green: 0.75, blue: 1.0)) {
                    ForEach(hk.thermostats, id: \.uniqueIdentifier) { thermo in
                        ThermostatRow(accessory: thermo)
                    }
                }
            }
        }
    }

    // MARK: - Setup / empty states

    private var liveStateSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                ZStack {
                    Circle()
                        .fill((serverError == nil ? amber : Color.red).opacity(0.12))
                        .frame(width: 42, height: 42)
                    Image(systemName: serverError == nil ? "dot.radiowaves.left.and.right" : "exclamationmark.triangle.fill")
                        .foregroundStyle(serverError == nil ? amber : .red)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Live JARVIS Home")
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                    Text(serverError ?? "Household state from the production JARVIS stack")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                if isLoadingServerState {
                    ProgressView().tint(amber)
                }
            }

            if let state = serverState {
                HStack(spacing: 10) {
                    liveMetric(title: "Present", value: state.presentMembers.isEmpty ? "0" : "\(state.presentMembers.count)")
                    liveMetric(title: "Lights", value: state.lightsOn.isEmpty ? "0" : "\(state.lightsOn.count)")
                    liveMetric(title: "Alerts", value: state.alerts.isEmpty ? "0" : "\(state.alerts.count)")
                }

                HStack(spacing: 10) {
                    liveMetric(title: "Inside", value: "\(Int(state.temperature.inside.rounded()))°")
                    liveMetric(title: "Target", value: "\(Int(state.temperature.target.rounded()))°")
                    liveMetric(title: "Mode", value: state.temperature.mode.isEmpty ? "—" : state.temperature.mode.capitalized)
                }

                if !state.presentMembers.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Present Members")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)
                        Text(state.presentMembers.joined(separator: " • "))
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.82))
                    }
                }

                if !state.alerts.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Live Alerts")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.red)
                        ForEach(Array(state.alerts.enumerated()), id: \.offset) { _, alert in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(alert.message)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text("\(alert.entity) · \(alert.state)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }

                if let appState {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Household Context")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(amber)

                        HStack(spacing: 10) {
                            liveMetric(title: "Events", value: "\(appState.calendar.count)")
                            liveMetric(title: "Reminders", value: "\(appState.reminders.count)")
                            liveMetric(title: "Alerts", value: "\(appState.notifications.pendingCount)")
                        }

                        if let nextEvent = appState.calendar.nextItems.first, !nextEvent.title.isEmpty {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(nextEvent.title)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(nextEvent.start.isEmpty ? "Upcoming family event" : nextEvent.start)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }
                }
            } else if serverError == nil {
                Text("Loading live house state from JARVIS…")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private var setupState: some View {
        VStack(spacing: 20) {
            Image(systemName: "house.circle")
                .font(.system(size: 60))
                .foregroundStyle(amber.opacity(0.5))
            Text("Connect HomeKit")
                .font(.title3.bold())
                .foregroundStyle(.white)
            Text("JARVIS will control your lights, locks, and climate through HomeKit.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Text("Add your home in the Apple Home app first, then return here.")
                .font(.caption)
                .foregroundStyle(.white.opacity(0.4))
                .multilineTextAlignment(.center)
        }
        .padding(32)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .frame(maxWidth: .infinity)
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "house.fill")
                .font(.system(size: 48))
                .foregroundStyle(amber.opacity(0.35))
            Text("No devices found")
                .font(.title3.bold())
                .foregroundStyle(.white)
            Text("Add accessories in the Apple Home app.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
    }

    private func liveMetric(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 14))
    }

    private func loadServerState() async {
        isLoadingServerState = true
        defer { isLoadingServerState = false }
        do {
            async let home = AppleAPIClient.shared.fetchHomeState()
            async let state = AppleAPIClient.shared.fetchAppState()
            serverState = try await home
            appState = try await state
            serverError = nil
        } catch {
            serverError = error.localizedDescription
        }
    }
}

// MARK: - Home section

private struct HomeSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: icon)
                .font(.caption.weight(.semibold))
                .foregroundStyle(accent)
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Light tile

private struct LightTile: View {
    let accessory: HMAccessory

    @State private var isOn: Bool = false

    private var powerChar: HMCharacteristic? {
        accessory.services
            .first(where: { $0.serviceType == HMServiceTypeLightbulb })?
            .characteristics
            .first(where: { $0.characteristicType == HMCharacteristicTypePowerState })
    }

    var body: some View {
        Button {
            isOn.toggle()
            Task { await HomeKitManager.shared.setLightOn(accessory, on: isOn) }
        } label: {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Image(systemName: isOn ? "lightbulb.fill" : "lightbulb")
                        .font(.system(size: 22))
                        .foregroundStyle(isOn ? Color.orange : .white.opacity(0.35))
                        .shadow(color: isOn ? Color.orange.opacity(0.6) : .clear, radius: 8)
                    Spacer()
                    Circle()
                        .fill(isOn ? Color.orange : Color.white.opacity(0.1))
                        .frame(width: 10, height: 10)
                }
                Text(accessory.name)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                Text(isOn ? "On" : "Off")
                    .font(.caption2)
                    .foregroundStyle(isOn ? Color.orange.opacity(0.8) : .white.opacity(0.3))
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .glassEffect(in: RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(isOn ? Color.orange.opacity(0.4) : .clear, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .onAppear {
            isOn = powerChar?.value as? Bool ?? false
        }
    }
}

// MARK: - Lock row

private struct LockRow: View {
    let accessory: HMAccessory

    private var isLocked: Bool {
        let char = accessory.services
            .first(where: { $0.serviceType == HMServiceTypeLockMechanism })?
            .characteristics
            .first(where: { $0.characteristicType == HMCharacteristicTypeCurrentLockMechanismState })
        let val = char?.value as? Int
        return val == 1  // 1 = secured
    }

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(isLocked ? Color.green.opacity(0.15) : Color.orange.opacity(0.15))
                    .frame(width: 44, height: 44)
                Image(systemName: isLocked ? "lock.fill" : "lock.open.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(isLocked ? .green : .orange)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(accessory.name)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.white)
                Text(isLocked ? "Secured" : "Unlocked")
                    .font(.caption)
                    .foregroundStyle(isLocked ? .green.opacity(0.8) : .orange.opacity(0.8))
            }
            Spacer()
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Thermostat row

private struct ThermostatRow: View {
    let accessory: HMAccessory

    private var targetTempC: Double? {
        accessory.services
            .first(where: { $0.serviceType == HMServiceTypeThermostat })?
            .characteristics
            .first(where: { $0.characteristicType == HMCharacteristicTypeTargetTemperature })?
            .value as? Double
    }

    private var tempFString: String {
        guard let c = targetTempC else { return "—" }
        let f = c * 9 / 5 + 32
        return String(format: "%.0f°F", f)
    }

    var body: some View {
        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(Color(red: 0.4, green: 0.75, blue: 1.0).opacity(0.12))
                    .frame(width: 44, height: 44)
                Image(systemName: "thermometer.medium")
                    .font(.system(size: 18))
                    .foregroundStyle(Color(red: 0.4, green: 0.75, blue: 1.0))
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(accessory.name)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.white)
                Text("Target: \(tempFString)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(tempFString)
                .font(.title3.bold().monospacedDigit())
                .foregroundStyle(Color(red: 0.4, green: 0.75, blue: 1.0))
        }
        .padding(.vertical, 2)
    }
}

#Preview {
    HomeView()
}
