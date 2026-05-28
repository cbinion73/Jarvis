import SoundAnalysis
import AVFoundation
import JarvisKit

/// Listens for specific household sounds and alerts JARVIS.
/// Uses Apple's built-in sound classifier — no mic streaming to any server.
@MainActor
final class SoundAnalysisManager: NSObject, ObservableObject {

    static let shared = SoundAnalysisManager()

    @Published var isListening     = false
    @Published var lastDetected:   SoundEvent?
    @Published var errorMessage:   String?

    // Sounds to alert on (Apple built-in classifier labels)
    static let alertSounds: Set<String> = [
        "smoke_detector", "fire_alarm", "carbon_monoxide_detector",
        "dog_barking", "baby_crying", "crying",
        "glass_breaking", "glass_shatter",
        "doorbell", "knock",
        "siren", "alarm",
        "cat_meowing",
    ]

    struct SoundEvent: Identifiable {
        let id         = UUID()
        let label:     String
        let confidence: Double
        let timestamp:  Date
    }

    private var audioEngine    = AVAudioEngine()
    private var analyzer:      SNAudioStreamAnalyzer?
    private var observer:      SNResultsObserving?
    private let analysisQueue  = DispatchQueue(label: "jarvis.sound.analysis")

    private override init() {}

    // MARK: - Control

    func startListening() {
        guard !isListening else { return }

        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .default)
            try session.setActive(true)

            let inputNode = audioEngine.inputNode
            let format    = inputNode.outputFormat(forBus: 0)

            let request   = try SNClassifySoundRequest(classifierIdentifier: .version1)
            request.windowDuration              = CMTimeMakeWithSeconds(1.5, preferredTimescale: 44100)
            request.overlapFactor               = 0.5

            let streamAnalyzer = SNAudioStreamAnalyzer(format: format)
            let obs            = SoundObserver { [weak self] label, confidence in
                Task { @MainActor in self?.handleDetection(label: label, confidence: confidence) }
            }
            try streamAnalyzer.add(request, withObserver: obs)
            observer  = obs
            analyzer  = streamAnalyzer

            Self.installAudioTap(on: inputNode, queue: analysisQueue, analyzer: streamAnalyzer)

            try audioEngine.start()
            isListening = true

        } catch {
            errorMessage = error.localizedDescription
        }
    }

    // nonisolated so the AVAudio real-time tap callback fires without @MainActor isolation check
    private nonisolated static func installAudioTap(
        on inputNode: AVAudioInputNode,
        queue: DispatchQueue,
        analyzer: SNAudioStreamAnalyzer
    ) {
        let analyzerBox = UncheckedSendable(analyzer)
        inputNode.installTap(onBus: 0, bufferSize: 8192, format: inputNode.outputFormat(forBus: 0)) { buffer, time in
            let bufferBox = UncheckedSendable(buffer)
            let sampleTime = time.sampleTime
            queue.async {
                analyzerBox.value.analyze(bufferBox.value, atAudioFramePosition: sampleTime)
            }
        }
    }

    func stopListening() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        analyzer    = nil
        observer    = nil
        isListening = false
        try? AVAudioSession.sharedInstance().setActive(false)
    }

    // MARK: - Handle detection

    private func handleDetection(label: String, confidence: Double) {
        guard confidence > 0.7,
              Self.alertSounds.contains(label) else { return }

        let event = SoundEvent(label: label, confidence: confidence, timestamp: Date())
        lastDetected = event

        // Alert JARVIS
        Task {
            await sendSoundAlert(event)
        }
    }

    private func sendSoundAlert(_ event: SoundEvent) async {
        guard let url = URL(string: JARVISEnvironment.baseURL.absoluteString + "/api/apple/sound-alert") else { return }
        let payload: [String: Any] = [
            "sound":      event.label,
            "confidence": event.confidence,
            "timestamp":  ISO8601DateFormatter().string(from: event.timestamp),
        ]
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        _ = try? await URLSession.shared.data(for: req)
    }
}

// MARK: - SNResultsObserving wrapper

private final class SoundObserver: NSObject, SNResultsObserving, @unchecked Sendable {
    let onDetect: (String, Double) -> Void
    init(onDetect: @escaping (String, Double) -> Void) { self.onDetect = onDetect }

    func request(_ request: SNRequest, didProduce result: SNResult) {
        guard let classResult = result as? SNClassificationResult,
              let top = classResult.classifications.first
        else { return }
        onDetect(top.identifier, top.confidence)
    }
}
