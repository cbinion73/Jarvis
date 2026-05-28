import SwiftUI
import JarvisKit

struct RootTabView: View {

    @StateObject private var briefingVM = BriefingViewModel()
    @StateObject private var needsVM    = NeedsViewModel()
    @StateObject private var healthVM   = HealthViewModel()
    @StateObject private var weatherMgr = WeatherManager.shared
    @StateObject private var weatherLoc = WeatherLocationProvider.shared

    var body: some View {
        TabView {
            Tab("Brief", systemImage: "sun.horizon.fill") {
                BriefingView(viewModel: briefingVM)
            }
            Tab("Needs", systemImage: "exclamationmark.circle.fill") {
                NeedsView(viewModel: needsVM)
            }
            .badge(needsVM.items.count > 0 ? needsVM.items.count : 0)

            Tab("Health", systemImage: "heart.fill") {
                HealthView(viewModel: healthVM)
            }
            Tab("Weather", systemImage: "cloud.sun.fill") {
                WeatherView()
            }
            Tab("Settings", systemImage: "gearshape.fill") {
                SettingsView()
            }
        }
        .tint(.cyan)
        .task {
            await briefingVM.load()
            await needsVM.load()
            await healthVM.load()
        }
        .onChange(of: weatherMgr.current) { _, cur in
            guard let cur else { return }
            WatchSessionManager.shared.sendWeather(cur, forecast: weatherMgr.forecast)
        }
    }
}

#Preview {
    RootTabView()
}
