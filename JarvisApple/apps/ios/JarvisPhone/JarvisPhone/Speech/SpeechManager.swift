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
    private var finishHandlers: [() -> Void] = []

    private override init() {
        super.init()
        synthesizer.delegate = self
    }

    // MARK: - Public API

    /// Speak text immediately, queuing behind any current utterance.
    func speak(
        _ text: String,
        rate: Float = 0.52,
        pitch: Float = 1.0,
        preferDuplex: Bool = false,
        onFinish: (() -> Void)? = nil
    ) {
        guard !text.isEmpty else { return }
        queue.append(text)
        if let onFinish {
            finishHandlers.append(onFinish)
        }
        configureAudioSession(preferDuplex: preferDuplex)
        if !synthesizer.isSpeaking { drainQueue(rate: rate, pitch: pitch, preferDuplex: preferDuplex) }
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
        finishHandlers.removeAll()
        isSpeaking = false
        deactivateAudioSession()
    }

    // MARK: - Private

    private func drainQueue(rate: Float, pitch: Float, preferDuplex: Bool) {
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

    /// Picks the best available installed Apple voice for spoken replies.
    /// Third-party apps do not get Siri's assistant voice directly, so we choose
    /// the best premium/enhanced system voice that iOS exposes to AVSpeech.
    private func bestVoice() -> AVSpeechSynthesisVoice? {
        let voices = AVSpeechSynthesisVoice.speechVoices()
        let englishVoices = voices.filter {
            let language = $0.language.lowercased()
            return language == "en-us" || language.hasPrefix("en-us-") || language.hasPrefix("en-us_")
        }

        func score(_ voice: AVSpeechSynthesisVoice) -> Int {
            let identifier = voice.identifier.lowercased()
            let name = voice.name.lowercased()
            var total = 0

            if identifier.contains("premium") { total += 400 }
            if identifier.contains("enhanced") { total += 250 }
            if identifier.contains("siri") { total += 120 }
            if name.contains("siri") { total += 100 }

            if #available(iOS 16.0, *) {
                switch voice.quality {
                case .premium:
                    total += 400
                case .enhanced:
                    total += 250
                default:
                    break
                }
            }

            let favoredNames = ["ava", "samantha", "allison", "nicky", "tom", "evan"]
            if let index = favoredNames.firstIndex(where: { name.contains($0) }) {
                total += max(0, 80 - (index * 10))
            }
            return total
        }

        if let best = englishVoices.max(by: { score($0) < score($1) }) {
            return best
        }

        return AVSpeechSynthesisVoice(language: "en-US") ?? AVSpeechSynthesisVoice(language: "en")
    }

    private func configureAudioSession(preferDuplex: Bool) {
        let session = AVAudioSession.sharedInstance()
        if preferDuplex || SpeechRecognitionManager.shared.isListening {
            try? session.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [.defaultToSpeaker, .allowBluetoothHFP, .duckOthers]
            )
        } else {
            try? session.setCategory(
                .playback,
                mode: .spokenAudio,
                options: [.duckOthers, .allowBluetoothHFP]
            )
        }
        try? session.setActive(true)
    }

    private func deactivateAudioSession() {
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
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
                self.deactivateAudioSession()
                let handlers = self.finishHandlers
                self.finishHandlers.removeAll()
                handlers.forEach { $0() }
            } else {
                self.drainQueue(rate: rate, pitch: pitch, preferDuplex: SpeechRecognitionManager.shared.isListening)
            }
        }
    }
}
