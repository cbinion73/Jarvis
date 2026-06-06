import SwiftUI
import JarvisKit

// MARK: - FaithView  "Formation"
// One Above All · Spiritual Steward

struct FaithView: View {

    @State private var overview: FaithOverview?
    @State private var isLoading = false
    @State private var error: String?
    @State private var prayerText = ""
    @State private var showPrayer = false
    @State private var activeAgent: FaithAgentSummary?
    @State private var chatMessages: [FaithChatMessage] = []
    @State private var chatDraft = ""
    @State private var chatPassage = ""
    @State private var isSending = false
    @FocusState private var prayerFocused: Bool
    @FocusState private var chatFocused: Bool

    private let gold = Color(red: 1.0, green: 0.85, blue: 0.35)
    private let ivory = Color(red: 0.98, green: 0.96, blue: 0.90)

    var body: some View {
        NavigationStack {
            ZStack {
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
        .sheet(item: $activeAgent) { agent in
            faithChatSheet(agent)
        }
    }

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "sparkles")
                .font(.system(size: 36))
                .foregroundStyle(gold.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Loading today's word…")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    @ViewBuilder
    private func contentView(_ ov: FaithOverview) -> some View {
        ScrollView {
            VStack(spacing: 16) {
                dailyWordCard(ov.dailyWord)
                prayerCard

                if !ov.formationPrompts.isEmpty {
                    FaithSection(title: "Formation Prompts", icon: "sparkles.rectangle.stack.fill", accent: gold) {
                        VStack(spacing: 8) {
                            ForEach(ov.formationPrompts, id: \.self) { prompt in
                                HStack(alignment: .top, spacing: 10) {
                                    Image(systemName: "arrow.up.right.circle.fill")
                                        .font(.caption)
                                        .foregroundStyle(gold.opacity(0.8))
                                    Text(prompt)
                                        .font(.caption)
                                        .foregroundStyle(.white.opacity(0.82))
                                    Spacer()
                                }
                                .padding(10)
                                .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                            }
                        }
                    }
                }

                if let continuity = ov.continuity,
                   continuity.profileFactCount > 0
                    || !continuity.guidanceLines.isEmpty
                    || !continuity.councilDomains.isEmpty
                    || !continuity.recentProfileFacts.isEmpty
                    || !continuity.recentFirstLight.isEmpty {
                    continuitySection(continuity)
                }

                if !ov.agents.isEmpty {
                    FaithSection(title: "Your Council", icon: "person.3.fill", accent: gold) {
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                            ForEach(ov.agents) { agent in
                                agentCard(agent)
                            }
                        }
                    }
                }

                if !ov.morningContext.isEmpty {
                    FaithSection(title: "Morning Context", icon: "sunrise.fill", accent: gold) {
                        ForEach(ov.morningContext.sorted(by: { $0.key < $1.key }), id: \.key) { key, val in
                            HStack(alignment: .top, spacing: 8) {
                                Text(key.capitalized)
                                    .font(.caption2.weight(.semibold))
                                    .foregroundStyle(gold.opacity(0.7))
                                    .frame(width: 86, alignment: .leading)
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

    @ViewBuilder
    private func continuitySection(_ continuity: FaithContinuity) -> some View {
        FaithSection(title: "Carry Forward", icon: "point.3.connected.trianglepath.dotted", accent: gold) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 10) {
                    continuityMetric("Facts", "\(continuity.profileFactCount)")
                    if !continuity.theme.isEmpty {
                        continuityMetric("Theme", continuity.theme.capitalized)
                    }
                    if !continuity.councilDomains.isEmpty {
                        continuityMetric("Council", "\(continuity.councilDomains.count)")
                    }
                }

                if !continuity.focus.isEmpty || !continuity.passage.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        if !continuity.focus.isEmpty {
                            Text("Formation focus: \(continuity.focus)")
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(ivory)
                        }
                        if !continuity.passage.isEmpty {
                            Text(continuity.passage)
                                .font(.caption)
                                .foregroundStyle(gold.opacity(0.8))
                                .italic()
                        }
                    }
                }

                if !continuity.councilDomains.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("COUNCIL DOMAINS")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        Text(continuity.councilDomains.joined(separator: " • "))
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.78))
                    }
                }

                if !continuity.guidanceLines.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("FORMATION RHYTHM")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(continuity.guidanceLines, id: \.self) { line in
                            Text("• \(line)")
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.8))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                if !continuity.recentProfileFacts.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("DURABLE PATTERNS")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(continuity.recentProfileFacts) { fact in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(fact.title)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(ivory)
                                if !fact.summary.isEmpty {
                                    Text(fact.summary)
                                        .font(.caption)
                                        .foregroundStyle(.white.opacity(0.78))
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                    }
                }

                if !continuity.recentFirstLight.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("RECENT FIRST LIGHT")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(continuity.recentFirstLight) { moment in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(moment.label)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(ivory)
                                Text(moment.summary)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.78))
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
            }
        }
    }

    private func continuityMetric(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(value)
                .font(.subheadline.weight(.bold))
                .foregroundStyle(ivory)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
            Text(label.uppercased())
                .font(.system(size: 9, weight: .bold))
                .tracking(1.0)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
    }

    @ViewBuilder
    private func dailyWordCard(_ dw: DailyWord) -> some View {
        VStack(alignment: .leading, spacing: 14) {
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
                        .padding(.horizontal, 6)
                        .padding(.vertical, 3)
                        .background(gold.opacity(0.1), in: Capsule())
                }
            }

            Divider().opacity(0.2)

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

            if !dw.passage.isEmpty {
                Divider().opacity(0.2)
                HStack(spacing: 6) {
                    Image(systemName: "book.closed.fill")
                        .font(.caption2)
                        .foregroundStyle(gold.opacity(0.6))
                    Text(dw.passage)
                        .font(.caption)
                        .foregroundStyle(gold.opacity(0.8))
                        .italic()
                }
            }
        }
        .padding(18)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .overlay(RoundedRectangle(cornerRadius: 20).stroke(gold.opacity(0.15), lineWidth: 1))
    }

    private var prayerCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: "hands.sparkles.fill")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(gold)
                Text("PRAYER")
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(gold.opacity(0.85))
                Spacer()
                if showPrayer {
                    Button("Cancel") {
                        showPrayer = false
                        prayerText = ""
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
            }

            if showPrayer {
                TextField("Share your prayer…", text: $prayerText, axis: .vertical)
                    .focused($prayerFocused)
                    .foregroundStyle(.white)
                    .tint(gold)
                    .lineLimit(2...6)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .glassEffect(in: RoundedRectangle(cornerRadius: 12))

                Button {
                    let text = prayerText
                    prayerText = ""
                    showPrayer = false
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
                            .font(.subheadline)
                            .foregroundStyle(.white.opacity(0.45))
                        Spacer()
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func agentCard(_ agent: FaithAgentSummary) -> some View {
        Button {
            chatMessages = []
            chatDraft = ""
            chatPassage = overview?.dailyWord.passage ?? ""
            activeAgent = agent
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(agent.initials)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(.black)
                        .frame(width: 28, height: 28)
                        .background(color(for: agent).opacity(0.95), in: Circle())
                    Spacer()
                    Image(systemName: "ellipsis.message.fill")
                        .font(.caption)
                        .foregroundStyle(color(for: agent))
                }
                Text(agent.name)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Text(agent.title)
                    .font(.caption2)
                    .foregroundStyle(color(for: agent).opacity(0.9))
                    .frame(maxWidth: .infinity, alignment: .leading)
                Text(agent.description)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.72))
                    .multilineTextAlignment(.leading)
                    .lineLimit(4)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(color(for: agent).opacity(0.18), lineWidth: 1))
        }
        .buttonStyle(.plain)
    }

    private func faithChatSheet(_ agent: FaithAgentSummary) -> some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()
                VStack(spacing: 0) {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 10) {
                            Text(agent.initials)
                                .font(.caption.weight(.bold))
                                .foregroundStyle(.black)
                                .frame(width: 34, height: 34)
                                .background(color(for: agent), in: Circle())
                            VStack(alignment: .leading, spacing: 2) {
                                Text(agent.name)
                                    .font(.headline)
                                    .foregroundStyle(.white)
                                Text(agent.domain)
                                    .font(.caption)
                                    .foregroundStyle(color(for: agent).opacity(0.9))
                            }
                            Spacer()
                        }

                        TextField("Passage (optional)", text: $chatPassage)
                            .textInputAutocapitalization(.never)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 10)
                            .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 12))
                    }
                    .padding(16)
                    .background(.white.opacity(0.03))

                    ScrollViewReader { proxy in
                        ScrollView {
                            VStack(spacing: 10) {
                                if chatMessages.isEmpty {
                                    Text("Ask about a passage, a prayer, or the next faithful step.")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .padding(.top, 32)
                                }
                                ForEach(chatMessages) { message in
                                    HStack {
                                        if message.role == "assistant" {
                                            bubble(message.content, accent: color(for: agent), isUser: false)
                                            Spacer(minLength: 28)
                                        } else {
                                            Spacer(minLength: 28)
                                            bubble(message.content, accent: gold, isUser: true)
                                        }
                                    }
                                    .id(message.id)
                                }
                            }
                            .padding(16)
                        }
                        .onChange(of: chatMessages.count) { _, _ in
                            if let last = chatMessages.last {
                                withAnimation {
                                    proxy.scrollTo(last.id, anchor: .bottom)
                                }
                            }
                        }
                    }

                    VStack(spacing: 10) {
                        TextField("Ask anything…", text: $chatDraft, axis: .vertical)
                            .focused($chatFocused)
                            .lineLimit(2...5)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 10)
                            .background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 12))

                        Button {
                            Task { await sendFaithMessage(agent: agent) }
                        } label: {
                            Label(isSending ? "Seeking Counsel…" : "Send to \(agent.name)", systemImage: "arrow.up.circle.fill")
                                .frame(maxWidth: .infinity)
                                .font(.subheadline.weight(.semibold))
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(color(for: agent))
                        .disabled(isSending || chatDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                    .padding(16)
                    .background(.white.opacity(0.03))
                }
            }
            .navigationTitle(agent.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        activeAgent = nil
                    }
                }
            }
        }
    }

    private func bubble(_ text: String, accent: Color, isUser: Bool) -> some View {
        Text(text)
            .font(.subheadline)
            .foregroundStyle(.white.opacity(isUser ? 0.96 : 0.9))
            .padding(12)
            .background(isUser ? gold.opacity(0.18) : accent.opacity(0.14), in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(accent.opacity(0.22), lineWidth: 1))
    }

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "sparkles")
                .font(.system(size: 44))
                .foregroundStyle(gold.opacity(0.5))
            Text("Faith unavailable")
                .font(.headline)
                .foregroundStyle(.white)
            Text(msg)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Retry") { Task { await load() } }
                .buttonStyle(.borderedProminent)
                .tint(gold)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func load() async {
        isLoading = true
        error = nil
        do { overview = try await AppleAPIClient.shared.fetchFaith() }
        catch { self.error = error.localizedDescription }
        isLoading = false
    }

    private func sendFaithMessage(agent: FaithAgentSummary) async {
        let trimmed = chatDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        isSending = true
        chatDraft = ""
        chatMessages.append(FaithChatMessage(role: "user", content: trimmed))

        do {
            let response = try await AppleAPIClient.shared.chatFaith(
                FaithChatPayload(
                    agentId: agent.id,
                    passage: chatPassage,
                    messages: chatMessages
                )
            )
            chatMessages.append(FaithChatMessage(role: "assistant", content: response.reply))
        } catch {
            chatMessages.append(FaithChatMessage(role: "assistant", content: "Faith agent unavailable right now."))
        }
        isSending = false
        chatFocused = true
    }

    private func color(for agent: FaithAgentSummary) -> Color {
        Color(hex: agent.color) ?? gold
    }
}

private struct FaithSection<Content: View>: View {
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
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

private extension Color {
    init?(hex: String) {
        let cleaned = hex.trimmingCharacters(in: .whitespacesAndNewlines).replacingOccurrences(of: "#", with: "")
        guard cleaned.count == 6, let value = Int(cleaned, radix: 16) else { return nil }
        self.init(
            red: Double((value >> 16) & 0xFF) / 255.0,
            green: Double((value >> 8) & 0xFF) / 255.0,
            blue: Double(value & 0xFF) / 255.0
        )
    }
}

#Preview { FaithView() }
