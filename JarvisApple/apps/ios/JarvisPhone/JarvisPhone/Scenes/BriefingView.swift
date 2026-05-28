import SwiftUI
import JarvisKit

// MARK: - BriefingView  "The Oracle"

struct BriefingView: View {

    @ObservedObject var viewModel: BriefingViewModel
    @StateObject private var nowPlaying = NowPlayingManager.shared
    @StateObject private var speech     = SpeechRecognitionManager.shared

    private let gold = Color(red: 1.0, green: 0.82, blue: 0.28)

    var body: some View {
        NavigationStack {
            ZStack {
                // Warm deep-space background
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.06, green: 0.05, blue: 0.01), Color.black],
                        startPoint: .top,
                        endPoint: UnitPoint(x: 0.5, y: 0.55)
                    )
                }
                .ignoresSafeArea()

                Group {
                    if viewModel.isLoading && viewModel.packet == nil {
                        loadingView
                    } else if let packet = viewModel.packet {
                        packetView(packet)
                    } else if let error = viewModel.errorMessage {
                        errorView(error)
                    }
                }
            }
            .navigationTitle("JARVIS")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 8) {
                        Button {
                            speech.startListening { text in
                                Task { await viewModel.sendVoiceCommand(text) }
                            }
                        } label: {
                            Image(systemName: speech.isListening ? "waveform.circle.fill" : "mic.circle")
                                .foregroundStyle(speech.isListening ? .red : gold)
                                .symbolEffect(.variableColor.iterative, isActive: speech.isListening)
                        }
                        .glassEffect(in: Circle())

                        Button { Task { await viewModel.refresh() } } label: {
                            Image(systemName: "arrow.clockwise")
                        }
                        .glassEffect(in: Circle())
                    }
                }
            }
        }
        .refreshable { await viewModel.refresh() }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "sun.horizon.fill")
                .font(.system(size: 40))
                .foregroundStyle(gold.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Reaching JARVIS…")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Packet

    @ViewBuilder
    private func packetView(_ packet: BriefingPacket) -> some View {
        ScrollView {
            VStack(spacing: 14) {

                // ── Now Playing ───────────────────────────────────
                if nowPlaying.isPlaying, let title = nowPlaying.title {
                    NowPlayingCard(title: title, artist: nowPlaying.artist ?? "", artwork: nowPlaying.artwork)
                }

                // ── Greeting + mode chip ─────────────────────────
                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .top) {
                        Text(packet.greeting)
                            .font(.title3.bold())
                            .foregroundStyle(.white)
                        Spacer()
                        // Mode chip
                        Text(packet.mode.uppercased())
                            .font(.system(size: 9, weight: .black))
                            .tracking(1.2)
                            .foregroundStyle(.black)
                            .padding(.horizontal, 9)
                            .padding(.vertical, 4)
                            .background(gold, in: Capsule())
                    }
                    Text(formatDate(packet.generatedAt))
                        .font(.caption2)
                        .foregroundStyle(gold.opacity(0.6))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                // ── Intelligence ──────────────────────────────────
                if !packet.briefingItems.isEmpty {
                    OracleSection(title: "Intelligence", icon: "brain.head.profile", accent: gold) {
                        ForEach(packet.briefingItems) { item in
                            IntelRow(item: item, gold: gold)
                            if item.id != packet.briefingItems.last?.id {
                                Divider().opacity(0.2)
                            }
                        }
                    }
                }

                // ── Needs You ─────────────────────────────────────
                if !packet.needsItems.isEmpty {
                    OracleSection(title: "Needs You", icon: "exclamationmark.circle.fill", accent: .red) {
                        ForEach(packet.needsItems) { item in
                            NeedsSummaryRow(item: item)
                        }
                    }
                }

                // ── Agents Working ────────────────────────────────
                if !packet.workingItems.isEmpty {
                    OracleSection(title: "Agents Working", icon: "gearshape.2.fill", accent: .cyan) {
                        ForEach(packet.workingItems) { item in
                            AgentRow(item: item)
                        }
                    }
                }

                // ── Drift ─────────────────────────────────────────
                if !packet.driftItems.isEmpty {
                    OracleSection(title: "Drift Signals", icon: "waveform.path", accent: Color(red: 1.0, green: 0.75, blue: 0.2)) {
                        ForEach(packet.driftItems) { item in
                            DriftRow(item: item)
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Error

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 44))
                .foregroundStyle(gold)
            Text("Couldn't reach JARVIS")
                .font(.headline)
                .foregroundStyle(.white)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Try Again") { Task { await viewModel.refresh() } }
                .buttonStyle(.borderedProminent)
                .tint(gold)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func formatDate(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso.prefix(10).description }
        return d.formatted(date: .abbreviated, time: .shortened)
    }
}

// MARK: - Oracle section container

private struct OracleSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(accent)
                Text(title.uppercased())
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(accent.opacity(0.85))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Row types

private struct IntelRow: View {
    let item: BriefingItem
    let gold: Color

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            // Priority accent strip
            if item.priority == "high" {
                RoundedRectangle(cornerRadius: 2)
                    .fill(gold)
                    .frame(width: 3)
                    .padding(.trailing, 10)
                    .padding(.vertical, 2)
            }

            VStack(alignment: .leading, spacing: 3) {
                Text(item.text)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                if let sub = item.sub {
                    Text(sub).font(.caption).foregroundStyle(.secondary)
                }
                Text(item.agent)
                    .font(.caption2)
                    .foregroundStyle(gold.opacity(0.6))
            }
            .padding(.leading, item.priority == "high" ? 0 : 13)
        }
        .padding(.vertical, 2)
    }
}

private struct NeedsSummaryRow: View {
    let item: NeedsItem

    var riskColor: Color {
        switch item.risk { case "high": .red; case "medium": .orange; default: .yellow }
    }

    var body: some View {
        HStack(spacing: 10) {
            Circle().fill(riskColor).frame(width: 7, height: 7)
            VStack(alignment: .leading, spacing: 1) {
                Text(item.text).font(.subheadline).foregroundStyle(.white)
                Text(item.agent).font(.caption2).foregroundStyle(.secondary)
            }
            Spacer()
            if let exp = item.expiresIn {
                Text(exp).font(.caption2).foregroundStyle(.secondary)
            }
        }
    }
}

private struct AgentRow: View {
    let item: WorkingItem

    var body: some View {
        HStack(spacing: 10) {
            // Animated blip
            Circle()
                .fill(Color.cyan)
                .frame(width: 6, height: 6)
                .symbolEffect(.pulse)
            VStack(alignment: .leading, spacing: 1) {
                Text(item.agent).font(.caption2).foregroundStyle(.cyan)
                Text(item.action).font(.subheadline).foregroundStyle(.white)
            }
        }
    }
}

private struct DriftRow: View {
    let item: DriftItem

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: item.severity == "significant" ? "exclamationmark.triangle.fill" : "circle.dotted")
                .foregroundStyle(Color(red: 1.0, green: 0.75, blue: 0.2))
                .font(.caption)
                .padding(.top, 2)
            Text(item.text).font(.subheadline).foregroundStyle(.white)
        }
    }
}

// MARK: - Now Playing card

private struct NowPlayingCard: View {
    let title:   String
    let artist:  String
    let artwork: UIImage?

    var body: some View {
        HStack(spacing: 12) {
            Group {
                if let img = artwork {
                    Image(uiImage: img).resizable().aspectRatio(contentMode: .fill)
                } else {
                    Image(systemName: "music.note")
                        .font(.title2).foregroundStyle(.purple)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .frame(width: 50, height: 50)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 3) {
                Label("Now Playing", systemImage: "waveform")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.purple.opacity(0.8))
                Text(title)
                    .font(.subheadline.bold())
                    .foregroundStyle(.white).lineLimit(1)
                Text(artist)
                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer()

            // Equalizer bars
            HStack(alignment: .bottom, spacing: 3) {
                ForEach([14.0, 20.0, 11.0, 17.0], id: \.self) { h in
                    RoundedRectangle(cornerRadius: 1.5)
                        .fill(Color.purple.opacity(0.75))
                        .frame(width: 3, height: h)
                }
            }
        }
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

#Preview {
    BriefingView(viewModel: BriefingViewModel())
}
