import SwiftUI
import JarvisKit

// MARK: - VoiceView  "The Bridge"

struct VoiceView: View {

    @StateObject private var vm      = VoiceViewModel()
    @StateObject private var speech  = SpeechRecognitionManager.shared
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
        }
    }

    // MARK: - Idle state

    private var idlePrompt: some View {
        VStack(spacing: 12) {
            Image(systemName: "waveform.circle")
                .font(.system(size: 56))
                .foregroundStyle(violet.opacity(0.4))
            Text("Tap the mic and speak to JARVIS")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.35))
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 60)
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
                if speech.isListening {
                    speech.stopListening()
                } else {
                    speech.startListening { text in
                        Task { await vm.send(text) }
                    }
                }
            }

            Text(speech.isListening ? "Listening… tap to stop" : "Tap to speak")
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
