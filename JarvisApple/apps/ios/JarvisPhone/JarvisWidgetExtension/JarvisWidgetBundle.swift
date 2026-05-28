import WidgetKit
import SwiftUI

/// Bundles all JARVIS widgets, Live Activity, and Control Center controls.
@main
struct JarvisWidgetBundle: WidgetBundle {
    var body: some Widget {
        // Home screen widgets
        JarvisSmallWidget()
        JarvisMediumWidget()
        JarvisLargeWidget()
        // Lock Screen / accessory widgets
        JarvisAccessoryWidget()
        // Live Activity (Dynamic Island + Lock Screen)
        JarvisLiveActivityWidget()
    }
}
