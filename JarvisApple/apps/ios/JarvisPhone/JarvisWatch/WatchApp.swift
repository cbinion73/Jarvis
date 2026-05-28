import SwiftUI

@main
struct JarvisWatchApp: App {

    @StateObject private var vm = WatchViewModel.shared

    var body: some Scene {
        WindowGroup {
            WatchRootView()
                .environmentObject(vm)
        }
    }
}

struct WatchRootView: View {
    @EnvironmentObject var vm: WatchViewModel

    var body: some View {
        TabView {
            BriefingWatchView()
            NeedsWatchView()
            WeatherWatchView()
        }
        .tabViewStyle(.verticalPage)
    }
}
