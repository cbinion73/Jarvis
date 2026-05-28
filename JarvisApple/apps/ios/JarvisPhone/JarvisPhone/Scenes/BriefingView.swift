import SwiftUI
import JarvisKit

struct BriefingView: View {

    @ObservedObject var viewModel: BriefingViewModel
    @StateObject private var nowPlaying = NowPlayingManager.shared
    @StateObject private var speech     = SpeechRecognitionManager.shared
    @State private var showingVoiceInput = false
    @State private var voiceTranscript  = ""

    var body: some View {
        NavigationStack {
            ZStack {
                // Deep space background
                Color.black.ignoresSafeArea()

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
            .navigationTitle("Morning Brief")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 10) {
                        // Voice input button
                        Button {
                            showingVoiceInput = true
                            speech.startListening { text in
                                voiceTranscript = text
                                showingVoiceInput = false
                                Task { await viewModel.sendVoiceCommand(text) }
                            }
                        } label: {
                            Image(systemName: speech.isListening ? "waveform.circle.fill" : "mic.circle")
                                .foregroundStyle(speech.isListening ? .red : .primary)
                        }
                        .glassEffect(in: Circle())

                        Button {
                            Task { await viewModel.refresh() }
                        } label: {
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
            ProgressView()
                .tint(.cyan)
                .scaleEffect(1.4)
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

                // ── Now Playing card (shown only when music is active) ─────
                if nowPlaying.isPlaying, let title = nowPlaying.title {
                    NowPlayingCard(
                        title: title,
                        artist: nowPlaying.artist ?? "",
                        artwork: nowPlaying.artwork
                    )
                }

                // ── Greeting glass card ───────────────────────────
                VStack(alignment: .leading, spacing: 4) {
                    Text(packet.greeting)
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text("\(packet.mode.capitalized) · \(packet.generatedAt.prefix(10))")
                        .font(.caption)
                        .foregroundStyle(.cyan.opacity(0.8))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                // ── Intelligence ─────────────────────────────────
                if !packet.briefingItems.isEmpty {
                    GlassSection(title: "Intelligence", icon: "brain.head.profile") {
                        ForEach(packet.briefingItems) { item in
                            BriefingItemRow(item: item)
                            if item.id != packet.briefingItems.last?.id {
                                Divider().opacity(0.3)
                            }
                        }
                    }
                }

                // ── Needs You ────────────────────────────────────
                if !packet.needsItems.isEmpty {
                    GlassSection(title: "Needs You", icon: "exclamationmark.circle.fill", accentColor: .orange) {
                        ForEach(packet.needsItems) { item in
                            NeedsSummaryRow(item: item)
                        }
                    }
                }

                // ── Agents Working ───────────────────────────────
                if !packet.workingItems.isEmpty {
                    GlassSection(title: "Agents Working", icon: "gearshape.2.fill", accentColor: .cyan) {
                        ForEach(packet.workingItems) { item in
                            WorkingItemRow(item: item)
                        }
                    }
                }

                // ── Drift ────────────────────────────────────────
                if !packet.driftItems.isEmpty {
                    GlassSection(title: "Drift Signals", icon: "waveform.path", accentColor: .yellow) {
                        ForEach(packet.driftItems) { item in
                            DriftItemRow(item: item)
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
                .foregroundStyle(.yellow)
            Text("Couldn't reach JARVIS")
                .font(.headline)
                .foregroundStyle(.white)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Try Again") { Task { await viewModel.refresh() } }
                .buttonStyle(.borderedProminent)
                .tint(.cyan)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
    }
}

// MARK: - Glass Section container

private struct GlassSection<Content: View>: View {
    let title: String
    let icon: String
    var accentColor: Color = .white
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(title, systemImage: icon)
                .font(.caption.weight(.semibold))
                .foregroundStyle(accentColor)
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Row types

private struct BriefingItemRow: View {
    let item: BriefingItem
    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            if item.priority == "high" {
                Image(systemName: "exclamationmark.circle.fill")
                    .foregroundStyle(.orange)
                    .font(.caption)
                    .padding(.top, 2)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(item.text).font(.subheadline).foregroundStyle(.white)
                if let sub = item.sub {
                    Text(sub).font(.caption).foregroundStyle(.secondary)
                }
                Text(item.agent).font(.caption2).foregroundStyle(.cyan.opacity(0.7))
            }
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
        HStack {
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

private struct WorkingItemRow: View {
    let item: WorkingItem
    var body: some View {
        HStack(spacing: 8) {
            ProgressView().scaleEffect(0.75).tint(.cyan)
            VStack(alignment: .leading, spacing: 1) {
                Text(item.agent).font(.caption2).foregroundStyle(.cyan)
                Text(item.action).font(.subheadline).foregroundStyle(.white)
            }
        }
    }
}

private struct DriftItemRow: View {
    let item: DriftItem
    var body: some View {
        HStack {
            Image(systemName: item.severity == "significant" ? "exclamationmark.triangle.fill" : "info.circle")
                .foregroundStyle(.yellow)
                .font(.caption)
            Text(item.text).font(.subheadline).foregroundStyle(.white)
        }
    }
}

// MARK: - Now Playing Card

private struct NowPlayingCard: View {
    let title:   String
    let artist:  String
    let artwork: UIImage?

    var body: some View {
        HStack(spacing: 12) {
            // Album art or music note
            Group {
                if let img = artwork {
                    Image(uiImage: img)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                } else {
                    Image(systemName: "music.note")
                        .font(.title2)
                        .foregroundStyle(.purple)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .frame(width: 48, height: 48)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            // Track info
            VStack(alignment: .leading, spacing: 2) {
                Label("Now Playing", systemImage: "waveform")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.purple.opacity(0.8))
                Text(title)
                    .font(.subheadline.bold())
                    .foregroundStyle(.white)
                    .lineLimit(1)
                Text(artist)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer()

            // Equaliser animation dots
            HStack(spacing: 3) {
                ForEach(0..<3, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.purple.opacity(0.8))
                        .frame(width: 3, height: CGFloat([10, 16, 12][i]))
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
