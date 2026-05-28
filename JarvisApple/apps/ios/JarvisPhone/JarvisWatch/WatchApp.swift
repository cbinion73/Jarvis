import SwiftUI
import WatchKit

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
