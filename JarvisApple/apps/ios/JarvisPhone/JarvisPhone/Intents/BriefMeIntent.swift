import AppIntents
import AVFoundation
import JarvisKit

/// "Hey Siri, JARVIS brief me" — fetches the morning briefing and
/// has Siri read it aloud as a spoken dialog response.
///
/// Also registered as an App Shortcut so it appears automatically
/// in Spotlight and the Shortcuts app without any user setup.
@available(iOS 16.0, *)
struct BriefMeIntent: AppIntent {

    nonisolated(unsafe) static var title: LocalizedStringResource = "JARVIS Brief Me"
    nonisolated(unsafe) static var description = IntentDescription(
        "Get your personalised morning briefing from JARVIS.",
        categoryName: "JARVIS"
    )

    nonisolated(unsafe) static var openAppWhenRun: Bool = false

    // MARK: - Perform

    func perform() async throws -> some ProvidesDialog & ShowsSnippetView {
        let packet = try await AppleAPIClient.shared.fetchBriefing()
        let spoken = buildSpokenText(from: packet)
        let snippet = BriefingSnippetView(greeting: packet.greeting, items: packet.briefingItems)
        return .result(dialog: IntentDialog(stringLiteral: spoken), view: snippet)
    }

    // MARK: - Helpers

    private func buildSpokenText(from packet: BriefingPacket) -> String {
        var lines: [String] = [packet.greeting]

        let topItems = packet.briefingItems.prefix(3)
        for item in topItems {
            lines.append(item.text)
        }

        if !packet.needsItems.isEmpty {
            let count = packet.needsItems.count
            lines.append("You have \(count) \(count == 1 ? "item" : "items") waiting for your approval.")
        }

        if packet.briefingItems.isEmpty && packet.needsItems.isEmpty {
            lines.append("All clear. No outstanding items.")
        }

        return lines.joined(separator: ". ")
    }
}

// MARK: - App Shortcuts (registers automatically with Siri)

@available(iOS 16.0, *)
struct JarvisShortcuts: AppShortcutsProvider {
    @AppShortcutsBuilder
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: BriefMeIntent(),
            phrases: [
                "Brief me with \(.applicationName)",
                "Give me my briefing with \(.applicationName)",
                "What's my morning brief in \(.applicationName)",
                "Morning brief with \(.applicationName)",
            ],
            shortTitle: "Morning Brief",
            systemImageName: "sun.horizon.fill"
        )

        if #available(iOS 18.0, *) {
            AppShortcut(
                intent: StartJarvisConversationIntent(),
                phrases: [
                    "Talk to \(.applicationName)",
                    "Open \(.applicationName) conversation",
                    "Start \(.applicationName) voice mode",
                ],
                shortTitle: "Talk to JARVIS",
                systemImageName: "waveform.circle.fill"
            )

            AppShortcut(
                intent: AskJarvisIntent(),
                phrases: [
                    "Ask \(.applicationName)",
                    "Talk to \(.applicationName) with a question",
                    "Open \(.applicationName) and ask something",
                ],
                shortTitle: "Ask JARVIS",
                systemImageName: "sparkles"
            )
        }
    }
}

// MARK: - Snippet view shown in Siri UI

import SwiftUI

@available(iOS 16.0, *)
private struct BriefingSnippetView: View {
    let greeting: String
    let items: [BriefingItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(greeting)
                .font(.headline)
                .foregroundColor(.cyan)
            ForEach(items.prefix(3)) { item in
                HStack(alignment: .top, spacing: 6) {
                    Circle()
                        .fill(item.priority == "high" ? Color.orange : Color.secondary)
                        .frame(width: 6, height: 6)
                        .padding(.top, 5)
                    Text(item.text)
                        .font(.subheadline)
                        .foregroundColor(.primary)
                }
            }
        }
        .padding(12)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
