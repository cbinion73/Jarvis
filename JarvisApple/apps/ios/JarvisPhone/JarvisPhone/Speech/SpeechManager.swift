import AVFoundation
import UIKit

/// Replaces ElevenLabs — speaks text using the best available on-device Siri voice.
/// The server sends a push notification with `"speak": "<text>"` and this class
/// handles it. Also used directly by BriefMeIntent and in-app voice responses.
@MainActor
final class SpeechManager: NSObject, ObservableObject {

    static let shared = SpeechManager()

    @Published var isSpeaking = false

    private let synthesizer = AVSpeechSynthesizer()
    private var queue: [String] = []

    private override init() {
        super.init()
        synthesizer.delegate = self
        configureAudioSession()
    }

    // MARK: - Public API

    /// Speak text immediately, queuing behind any current utterance.
    func speak(_ text: String, rate: Float = 0.52, pitch: Float = 1.0) {
        guard !text.isEmpty else { return }
        queue.append(text)
        if !synthesizer.isSpeaking { drainQueue(rate: rate, pitch: pitch) }
    }

    /// Read the full morning brief aloud.
    func speakBrief(greeting: String, items: [String]) {
        stopSpeaking()
        var parts = [greeting]
        parts.append(contentsOf: items.prefix(5))
        parts.forEach { speak($0, rate: 0.50) }
    }

    func stopSpeaking() {
        synthesizer.stopSpeaking(at: .immediate)
        queue.removeAll()
    }

    // MARK: - Private

    private func drainQueue(rate: Float, pitch: Float) {
        guard let text = queue.first else { return }
        queue.removeFirst()

        let utterance        = AVSpeechUtterance(string: text)
        utterance.voice      = bestVoice()
        utterance.rate       = rate
        utterance.pitchMultiplier = pitch
        utterance.preUtteranceDelay  = 0.1
        utterance.postUtteranceDelay = 0.15

        isSpeaking = true
        synthesizer.speak(utterance)
    }

    /// Picks the best available enhanced Siri voice (en-US preferred).
    private func bestVoice() -> AVSpeechSynthesisVoice? {
        let preferred = ["com.apple.voice.enhanced.en-US.Evan",   // iOS 26
                         "com.apple.voice.premium.en-US.Evan",
                         "com.apple.voice.enhanced.en-US.Ava",
                         "com.apple.voice.enhanced.en-US.Tom",
                         "com.apple.voice.enhanced.en-US.Samantha"]
        for id in preferred {
            if let v = AVSpeechSynthesisVoice(identifier: id) { return v }
        }
        return AVSpeechSynthesisVoice(language: "en-US")
    }

    private func configureAudioSession() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .spokenAudio,
                                 options: [.duckOthers, .allowBluetooth])
        try? session.setActive(true)
    }
}

// MARK: - Delegate

extension SpeechManager: @preconcurrency AVSpeechSynthesizerDelegate {

    func speechSynthesizer(
        _ synthesizer: AVSpeechSynthesizer,
        didFinish utterance: AVSpeechUtterance
    ) {
        let rate  = utterance.rate
        let pitch = utterance.pitchMultiplier
        Task { @MainActor in
            if self.queue.isEmpty {
                self.isSpeaking = false
            } else {
                self.drainQueue(rate: rate, pitch: pitch)
            }
        }
    }
}
