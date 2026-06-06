import SwiftUI
import JarvisKit

// MARK: - VoiceView  "The Bridge"

struct VoiceView: View {

    @ObservedObject private var vm      = VoiceViewModel.shared
    @ObservedObject private var speech = SpeechRecognitionManager.shared
    @ObservedObject private var speaker = SpeechManager.shared
    @Environment(\.scenePhase) private var scenePhase
    @State private var typeText      = ""
    @State private var showKeyboard  = false
    @FocusState private var kbFocused: Bool

    private let violet = Color(red: 0.72, green: 0.45, blue: 1.0)

    var body: some View {
        NavigationStack {
            ZStack {
                // Violet-tinted deep space background
                ZStack {
                    Color.black
                    RadialGradient(
                        colors: [violet.opacity(0.08), .clear],
                        center: .bottom,
                        startRadius: 0,
                        endRadius: 500
                    )
                }
                .ignoresSafeArea()

                VStack(spacing: 0) {
                    // ── Conversation history ──────────────────────────────
                    ScrollViewReader { proxy in
                        ScrollView {
                            LazyVStack(spacing: 12) {
                                if vm.exchanges.isEmpty && !speech.isListening {
                                    idlePrompt
                                        .id("idle")
                                }
                                if vm.isConversationActive || speech.isListening {
                                    conversationStatusCard
                                        .id("conversation-status")
                                }
                                if let error = speech.errorMessage {
                                    speechErrorCard(error)
                                        .id("speech-error")
                                }
                                if let error = vm.errorMessage {
                                    appErrorCard(error)
                                        .id("app-error")
                                }
                                if let state = vm.voiceState {
                                    voiceConsoleCard(state)
                                        .id("voice-console")
                                }
                                ForEach(vm.exchanges) { ex in
                                    exchangeCard(ex)
                                        .id(ex.id)
                                }
                                if vm.isThinking {
                                    thinkingIndicator
                                        .id("thinking")
                                }
                                // Live transcript
                                if speech.isListening && !speech.transcript.isEmpty {
                                    liveTranscript
                                        .id("live")
                                }
                            }
                            .padding(.horizontal, 16)
                            .padding(.vertical, 12)
                        }
                        .onChange(of: vm.exchanges.count) { _, _ in
                            withAnimation { proxy.scrollTo(vm.exchanges.last?.id, anchor: .bottom) }
                        }
                        .onChange(of: speech.transcript) { _, _ in
                            withAnimation { proxy.scrollTo("live", anchor: .bottom) }
                        }
                    }

                    // ── Keyboard input row ────────────────────────────────
                    if showKeyboard {
                        keyboardRow
                    }

                    // ── Mic button + controls ─────────────────────────────
                    micControl
                }
            }
            .navigationTitle("Voice")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    if !vm.exchanges.isEmpty {
                        Button("Clear") { vm.clear() }
                            .foregroundStyle(violet.opacity(0.8))
                            .font(.caption)
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showKeyboard.toggle()
                        if showKeyboard { kbFocused = true }
                    } label: {
                        Image(systemName: showKeyboard ? "keyboard.chevron.compact.down.fill" : "keyboard")
                            .foregroundStyle(violet.opacity(0.8))
                    }
                    .glassEffect(in: Circle())
                }
            }
            .onAppear {
                handlePendingLaunchOrResume()
                Task { await vm.refreshVoiceState() }
            }
            .onChange(of: scenePhase) { _, phase in
                guard phase == .active else { return }
                handlePendingLaunchOrResume()
                Task { await vm.refreshVoiceState() }
            }
        }
    }

    // MARK: - Idle state

    private var idlePrompt: some View {
        VStack(spacing: 12) {
            Image(systemName: "waveform.circle")
                .font(.system(size: 56))
                .foregroundStyle(violet.opacity(0.4))
            Text("Start a hands-free conversation with JARVIS")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.35))
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
    }

    private var conversationStatusCard: some View {
        HStack(spacing: 8) {
            Image(systemName: speech.isListening ? "waveform" : (speaker.isSpeaking ? "speaker.wave.2.fill" : "sparkles"))
                .foregroundStyle(violet)
                .font(.caption)
                .symbolEffect(.variableColor.iterative, isActive: speech.isListening || speaker.isSpeaking)
            Text(vm.conversationStatus)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.8))
            Spacer()
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func speechErrorCard(_ error: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
                .font(.caption)
                .padding(.top, 2)
            Text(error)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.85))
                .fixedSize(horizontal: false, vertical: true)
            Spacer()
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func appErrorCard(_ error: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "bolt.horizontal.circle.fill")
                .foregroundStyle(.red.opacity(0.85))
                .font(.caption)
                .padding(.top, 2)
            Text(error)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.85))
                .fixedSize(horizontal: false, vertical: true)
            Spacer()
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func voiceConsoleCard(_ state: VoiceConsoleState) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 10) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Voice Console")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(violet)
                    Text(state.voiceStack.detail)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text(state.conversation.title)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.9))
                    Text("\(state.conversation.turnCount) turns")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            HStack(spacing: 10) {
                consoleMetric(title: "Facts", value: "\(state.memoryOverview.profileFactCount)")
                consoleMetric(title: "Proposals", value: "\(state.memoryOverview.pendingProposals)")
                consoleMetric(title: "Recents", value: "\(state.recentConversations.count)")
            }

            if !state.memoryOverview.guidanceLines.isEmpty
                || !state.memoryOverview.recentProfileFacts.isEmpty
                || !state.memoryOverview.recentFirstLight.isEmpty
                || !state.memoryOverview.longHorizonLines.isEmpty
                || !state.memoryOverview.activeThreads.isEmpty
            {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Carry Forward")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.92))

                    if !state.memoryOverview.preferredVoice.isEmpty || !state.memoryOverview.briefingStyle.isEmpty {
                        VStack(alignment: .leading, spacing: 3) {
                            if !state.memoryOverview.preferredVoice.isEmpty {
                                Text("Preferred voice: \(state.memoryOverview.preferredVoice)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary.opacity(0.95))
                            }
                            if !state.memoryOverview.briefingStyle.isEmpty {
                                Text("Briefing style: \(state.memoryOverview.briefingStyle.replacingOccurrences(of: "_", with: " ").capitalized)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary.opacity(0.95))
                            }
                        }
                    }

                    if !state.memoryOverview.guidanceLines.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Voice Rhythm")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.92))
                            ForEach(state.memoryOverview.guidanceLines, id: \.self) { line in
                                Text(line)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary.opacity(0.95))
                            }
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                    }

                    if !state.memoryOverview.longHorizonLines.isEmpty || !state.memoryOverview.activeThreads.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Long Horizon")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.92))
                            ForEach(state.memoryOverview.longHorizonLines.prefix(2), id: \.self) { line in
                                Text(line)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary.opacity(0.95))
                            }
                            if !state.memoryOverview.activeThreads.isEmpty {
                                Text(state.memoryOverview.activeThreads.joined(separator: " • "))
                                    .font(.caption2)
                                    .foregroundStyle(.secondary.opacity(0.9))
                                    .lineLimit(2)
                            }
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                    }

                    if !state.memoryOverview.recentProfileFacts.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Durable Patterns")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.92))
                            ForEach(state.memoryOverview.recentProfileFacts) { fact in
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(fact.title)
                                        .font(.caption.weight(.medium))
                                        .foregroundStyle(.white.opacity(0.92))
                                    Text(fact.summary)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.95))
                                }
                            }
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                    }

                    if !state.memoryOverview.recentFirstLight.isEmpty {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Recent First Light")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.92))
                            ForEach(state.memoryOverview.recentFirstLight) { moment in
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(moment.label)
                                        .font(.caption.weight(.medium))
                                        .foregroundStyle(.white.opacity(0.92))
                                    Text(moment.summary)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary.opacity(0.95))
                                }
                            }
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                    }
                }
            }

            if !state.conversation.latestAssistantText.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Latest JARVIS Reply")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.92))
                    Text(state.conversation.latestAssistantText)
                        .font(.caption2)
                        .foregroundStyle(.secondary.opacity(0.95))
                        .lineLimit(4)
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
            }

            if !state.quickCommands.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Quick Commands")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.92))
                    ForEach(state.quickCommands, id: \.self) { command in
                        Button {
                            Task { await vm.send(command) }
                        } label: {
                            Text(command)
                                .font(.caption2.weight(.medium))
                                .foregroundStyle(violet.opacity(0.95))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 8)
                                .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 10))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            if !state.conversation.recentTurns.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Recent Context")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.92))
                    ForEach(state.conversation.recentTurns) { turn in
                        VStack(alignment: .leading, spacing: 2) {
                            Text((turn.role == "user" ? "You" : turn.agent).uppercased())
                                .font(.caption2.weight(.semibold))
                                .foregroundStyle(turn.role == "user" ? .white.opacity(0.65) : violet.opacity(0.82))
                            Text(turn.text)
                                .font(.caption2)
                                .foregroundStyle(.secondary.opacity(0.95))
                                .lineLimit(3)
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                    }
                }
            }

            if !state.recentConversations.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Recent Sessions")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.white.opacity(0.92))
                    ForEach(state.recentConversations) { session in
                        HStack(spacing: 8) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(session.title)
                                    .font(.caption.weight(.medium))
                                    .foregroundStyle(.white.opacity(0.9))
                                    .lineLimit(1)
                                Text("\(session.turnCount) turns")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
                    }
                }
            }
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func handlePendingLaunchOrResume() {
        let launchCenter = VoiceConversationLaunchCenter.shared
        launchCenter.refreshFromStore()
        if let launch = launchCenter.consumePendingLaunch() {
            vm.activateConversation(launch: launch)
        } else {
            vm.ensureConversationIsLive()
        }
    }

    // MARK: - Exchange card

    @ViewBuilder
    private func exchangeCard(_ ex: VoiceViewModel.Exchange) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            // User command
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "person.circle.fill")
                    .foregroundStyle(.white.opacity(0.5))
                    .font(.caption)
                    .padding(.top, 2)
                Text(ex.userText)
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.75))
                    .fixedSize(horizontal: false, vertical: true)
            }

            Divider().opacity(0.2)

            // JARVIS response
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "sparkles")
                    .foregroundStyle(violet)
                    .font(.caption)
                    .padding(.top, 2)
                VStack(alignment: .leading, spacing: 4) {
                    Text(ex.response)
                        .font(.subheadline)
                        .foregroundStyle(.white)
                        .fixedSize(horizontal: false, vertical: true)
                    Text(ex.agent)
                        .font(.caption2)
                        .foregroundStyle(violet.opacity(0.7))
                }
            }

            // Timestamp
            Text(ex.timestamp, style: .time)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .trailing)
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Thinking indicator

    private var thinkingIndicator: some View {
        HStack(spacing: 8) {
            Image(systemName: "sparkles")
                .foregroundStyle(violet)
                .font(.caption)
            ThinkingDots(color: violet)
            Spacer()
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Live transcript

    private var liveTranscript: some View {
        HStack(spacing: 8) {
            Image(systemName: "waveform")
                .foregroundStyle(violet)
                .font(.caption)
                .symbolEffect(.variableColor.iterative, isActive: speech.isListening)
            Text(speech.transcript)
                .font(.subheadline.italic())
                .foregroundStyle(.white.opacity(0.6))
                .fixedSize(horizontal: false, vertical: true)
            Spacer()
        }
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func consoleMetric(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 14))
    }

    // MARK: - Keyboard row

    private var keyboardRow: some View {
        HStack(spacing: 8) {
            TextField("Type a command…", text: $typeText, axis: .vertical)
                .focused($kbFocused)
                .foregroundStyle(.white)
                .tint(violet)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .glassEffect(in: RoundedRectangle(cornerRadius: 12))
                .lineLimit(1...4)

            Button {
                let text = typeText
                typeText = ""
                Task { await vm.send(text) }
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 30))
                    .foregroundStyle(typeText.isEmpty ? .white.opacity(0.25) : violet)
            }
            .disabled(typeText.isEmpty)
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 8)
    }

    // MARK: - Mic control

    private var micControl: some View {
        VStack(spacing: 16) {
            // Animated rings + mic button
            ZStack {
                if speech.isListening {
                    ForEach(0..<3, id: \.self) { i in
                        Circle()
                            .stroke(violet.opacity(0.25 - Double(i) * 0.07), lineWidth: 1.5)
                            .frame(width: CGFloat(88 + i * 36))
                            .scaleEffect(speech.isListening ? 1.0 : 0.85)
                            .animation(
                                .easeInOut(duration: 1.2)
                                    .repeatForever(autoreverses: true)
                                    .delay(Double(i) * 0.25),
                                value: speech.isListening
                            )
                    }
                }

                Circle()
                    .fill(speech.isListening ? violet : Color.white.opacity(0.08))
                    .frame(width: 72, height: 72)
                    .shadow(color: speech.isListening ? violet.opacity(0.5) : .clear, radius: 20)

                Image(systemName: speech.isListening ? "stop.fill" : "mic.fill")
                    .font(.system(size: 26, weight: .medium))
                    .foregroundStyle(.white)
            }
            .onTapGesture {
                vm.toggleConversationMicrophone()
            }

            Text(
                speech.isListening
                    ? (vm.isDuplexArmed ? "Listening while JARVIS speaks. Pause to interrupt." : "Listening... JARVIS will send after you pause")
                    : (speaker.isSpeaking
                        ? "JARVIS is speaking. You can interrupt anytime."
                        : (vm.isConversationActive ? "Conversation paused. Tap to resume." : "Tap to speak"))
            )
                .font(.caption)
                .foregroundStyle(.white.opacity(0.35))
        }
        .padding(.top, 16)
        .padding(.bottom, 20)
    }
}

// MARK: - Thinking dots animation

private struct ThinkingDots: View {
    let color: Color
    @State private var phase = 0

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(color.opacity(i == phase ? 1.0 : 0.3))
                    .frame(width: 6, height: 6)
                    .scaleEffect(i == phase ? 1.2 : 1.0)
                    .animation(.easeInOut(duration: 0.3), value: phase)
            }
        }
        .onAppear {
            Timer.scheduledTimer(withTimeInterval: 0.4, repeats: true) { _ in
                Task { @MainActor in
                    phase = (phase + 1) % 3
                }
            }
        }
    }
}

#Preview {
    VoiceView()
}
