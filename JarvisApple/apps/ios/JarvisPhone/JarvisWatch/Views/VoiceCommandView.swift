import SwiftUI

/// Lets you dictate a command to JARVIS from your wrist.
/// Uses watchOS's built-in scribble / dictation input.
struct VoiceCommandView: View {

    @EnvironmentObject var vm: WatchViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var commandText = ""
    @State private var sent        = false
    @State private var sending     = false
    @FocusState private var focused: Bool

    var body: some View {
        Group {
            if sent {
                sentView
            } else {
                inputView
            }
        }
        .navigationTitle("Speak")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: - Input state

    private var inputView: some View {
        VStack(spacing: 10) {
            Image(systemName: "mic.circle.fill")
                .font(.system(size: 38))
                .foregroundStyle(.purple)

            Text("What should JARVIS do?")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            TextField("Dictate…", text: $commandText)
                .focused($focused)
                .onSubmit { send() }

            if !commandText.isEmpty {
                Button(action: send) {
                    if sending {
                        ProgressView().tint(.purple)
                    } else {
                        Label("Send", systemImage: "arrow.up.circle.fill")
                            .font(.caption.weight(.semibold))
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(.purple)
                .disabled(sending)
            }
        }
        .onAppear {
            // Slight delay so nav animation finishes before keyboard appears
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                focused = true
            }
        }
    }

    // MARK: - Sent state

    private var sentView: some View {
        VStack(spacing: 10) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 38))
                .foregroundStyle(.green)
            Text("Sent")
                .font(.headline)
                .foregroundStyle(.white)
            Text(commandText)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .lineLimit(3)
            Button("Done") { dismiss() }
                .buttonStyle(.borderedProminent)
                .tint(.green)
        }
    }

    // MARK: - Send

    private func send() {
        guard !commandText.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        sending = true
        focused = false
        playWatchHaptic(.click)
        vm.sendVoiceCommand(commandText) {
            sending = false
            sent    = true
            playWatchHaptic(.success)
        }
    }
}
