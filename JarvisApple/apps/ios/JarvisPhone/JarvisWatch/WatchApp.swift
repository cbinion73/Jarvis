import SwiftUI

@main
struct JarvisWatchApp: App {

    @StateObject private var vm = WatchViewModel.shared

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                JarvisWatchHomeView()
            }
            .environmentObject(vm)
        }
    }
}
