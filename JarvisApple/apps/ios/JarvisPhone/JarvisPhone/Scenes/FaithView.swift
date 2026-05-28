import SwiftUI
import JarvisKit

// MARK: - FaithView  "Formation"
// One Above All · Spiritual Steward

struct FaithView: View {

    @State private var overview: FaithOverview?
    @State private var isLoading  = false
    @State private var error: String?
    @State private var prayerText = ""
    @State private var showPrayer = false
    @FocusState private var prayerFocused: Bool

    private let gold   = Color(red: 1.0, green: 0.85, blue: 0.35)
    private let ivory  = Color(red: 0.98, green: 0.96, blue: 0.90)

    var body: some View {
        NavigationStack {
            ZStack {
                // Warm, quiet background — unlike the electric tabs, Faith is still
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.08, green: 0.07, blue: 0.02), Color.black],
                        startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.6)
                    )
                }
                .ignoresSafeArea()

                Group {
                    if isLoading && overview == nil { loadingView }
                    else if let ov = overview { contentView(ov) }
                    else if let e = error { errorView(e) }
                    else { loadingView }
                }
            }
            .navigationTitle("Faith")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { Task { await load() } } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .glassEffect(in: Circle())
                }
            }
        }
        .task { await load() }
        .refreshable { await load() }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "sparkles")
                .font(.system(size: 36)).foregroundStyle(gold.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Loading today's word…").font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Content

    @ViewBuilder
    private func contentView(_ ov: FaithOverview) -> some View {
        ScrollView {
            VStack(spacing: 16) {

                // ── Daily word hero card ─────────────────────────
                dailyWordCard(ov.dailyWord)

                // ── Prayer capture ──────────────────────────────
                prayerCard

                // ── Morning context hints ────────────────────────
                if !ov.morningContext.isEmpty {
                    FaithSection(title: "Morning Context", icon: "sunrise.fill", accent: gold) {
                        ForEach(ov.morningContext.sorted(by: { $0.key < $1.key }), id: \.key) { key, val in
                            HStack(alignment: .top, spacing: 8) {
                                Text(key.capitalized)
                                    .font(.caption2.weight(.semibold))
                                    .foregroundStyle(gold.opacity(0.7))
                                    .frame(width: 70, alignment: .leading)
                                Text(val)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.8))
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Daily word card

    @ViewBuilder
    private func dailyWordCard(_ dw: DailyWord) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            // Agent header
            HStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .foregroundStyle(gold)
                    .font(.caption)
                VStack(alignment: .leading, spacing: 1) {
                    Text(dw.agent)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(gold)
                    if !dw.agentTitle.isEmpty {
                        Text(dw.agentTitle)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                if !dw.domain.isEmpty {
                    Text(dw.domain)
                        .font(.system(size: 8, weight: .medium))
                        .foregroundStyle(gold.opacity(0.6))
                        .padding(.horizontal, 6).padding(.vertical, 3)
                        .background(gold.opacity(0.1), in: Capsule())
                }
            }

            Divider().opacity(0.2)

            // The word
            if !dw.word.isEmpty {
                Text(dw.word)
                    .font(.subheadline)
                    .foregroundStyle(ivory)
                    .fixedSize(horizontal: false, vertical: true)
                    .lineSpacing(4)
            } else {
                Text("No daily word available yet. JARVIS will generate one soon.")
                    .font(.subheadline.italic())
                    .foregroundStyle(.white.opacity(0.4))
            }

            // Scripture passage
            if !dw.passage.isEmpty {
                Divider().opacity(0.2)
                HStack(spacing: 6) {
                    Image(systemName: "book.closed.fill")
                        .font(.caption2).foregroundStyle(gold.opacity(0.6))
                    Text(dw.passage)
                        .font(.caption)
                        .foregroundStyle(gold.opacity(0.8))
                        .italic()
                }
            }
        }
        .padding(18)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .overlay(
            RoundedRectangle(cornerRadius: 20)
                .stroke(gold.opacity(0.15), lineWidth: 1)
        )
    }

    // MARK: - Prayer card

    private var prayerCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: "hands.sparkles.fill")
                    .font(.system(size: 11, weight: .semibold)).foregroundStyle(gold)
                Text("PRAYER")
                    .font(.system(size: 10, weight: .bold)).tracking(1.0).foregroundStyle(gold.opacity(0.85))
                Spacer()
                if showPrayer {
                    Button("Cancel") { showPrayer = false; prayerText = "" }
                        .font(.caption).foregroundStyle(.secondary)
                }
            }

            if showPrayer {
                TextField("Share your prayer…", text: $prayerText, axis: .vertical)
                    .focused($prayerFocused)
                    .foregroundStyle(.white).tint(gold)
                    .lineLimit(2...6)
                    .padding(.horizontal, 12).padding(.vertical, 10)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 12))

                Button {
                    let text = prayerText
                    prayerText = ""; showPrayer = false
                    Task {
                        let cap = ChronicleCapture(type: "prayer", note: text)
                        _ = try? await AppleAPIClient.shared.captureChronicle(cap)
                    }
                } label: {
                    Label("Offer Prayer", systemImage: "arrow.up.circle.fill")
                        .frame(maxWidth: .infinity)
                        .font(.subheadline.weight(.semibold))
                }
                .buttonStyle(.borderedProminent)
                .tint(gold)
                .disabled(prayerText.trimmingCharacters(in: .whitespaces).isEmpty)
            } else {
                Button {
                    showPrayer = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { prayerFocused = true }
                } label: {
                    HStack {
                        Image(systemName: "plus.circle")
                            .foregroundStyle(gold.opacity(0.7))
                        Text("Add a prayer…")
                            .font(.subheadline).foregroundStyle(.white.opacity(0.45))
                        Spacer()
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Error

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "sparkles").font(.system(size: 44)).foregroundStyle(gold.opacity(0.5))
            Text("Faith unavailable").font(.headline).foregroundStyle(.white)
            Text(msg).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Retry") { Task { await load() } }
                .buttonStyle(.borderedProminent).tint(gold)
        }
        .padding(24).glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32).frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func load() async {
        isLoading = true; error = nil
        do { overview = try await AppleAPIClient.shared.fetchFaith() }
        catch { self.error = error.localizedDescription }
        isLoading = false
    }
}

// MARK: - Faith section

private struct FaithSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon).font(.system(size: 11, weight: .semibold)).foregroundStyle(accent)
                Text(title.uppercased()).font(.system(size: 10, weight: .bold)).tracking(1.0).foregroundStyle(accent.opacity(0.85))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

#Preview { FaithView() }
