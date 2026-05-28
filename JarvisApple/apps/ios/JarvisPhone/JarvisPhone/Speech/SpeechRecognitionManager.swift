import Speech
import AVFoundation

/// Free on-device speech recognition — replaces Whisper API calls.
/// Supports both continuous listening and one-shot recognition.
@MainActor
final class SpeechRecognitionManager: ObservableObject {

    static let shared = SpeechRecognitionManager()

    @Published var transcript    = ""
    @Published var isListening   = false
    @Published var isAuthorized  = false
    @Published var errorMessage: String?

    private let recognizer       = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private var request:           SFSpeechAudioBufferRecognitionRequest?
    private var task:              SFSpeechRecognitionTask?
    private let audioEngine        = AVAudioEngine()
    private var onFinal:           ((String) -> Void)?

    private init() {
        Task { await checkAuthorization() }
    }

    // MARK: - Authorization

    func checkAuthorization() async {
        let speechStatus = await Self.requestSpeechAuth()
        let audioGranted = await AVAudioApplication.requestRecordPermission()
        isAuthorized = (speechStatus == .authorized) && audioGranted
    }

    // nonisolated so the TCC callback fires without @MainActor isolation check
    private nonisolated static func requestSpeechAuth() async -> SFSpeechRecognizerAuthorizationStatus {
        await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }
    }

    // MARK: - Start / Stop

    /// Start listening. `onFinal` is called with the final transcript when stopped.
    func startListening(onFinal: @escaping (String) -> Void) {
        guard isAuthorized, !(recognizer?.isAvailable ?? false == false) else {
            errorMessage = "Speech recognition unavailable"
            return
        }
        guard !isListening else { return }

        self.onFinal = onFinal
        transcript   = ""
        errorMessage = nil

        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults     = true
        req.requiresOnDeviceRecognition    = false  // allow server for better accuracy
        request = req

        let node   = audioEngine.inputNode
        let format = node.outputFormat(forBus: 0)
        node.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            self?.request?.append(buffer)
        }

        try? audioEngine.start()
        isListening = true

        task = recognizer?.recognitionTask(with: req) { [weak self] result, error in
            guard let self else { return }
            if let result {
                Task { @MainActor in
                    self.transcript = result.bestTranscription.formattedString
                }
            }
            if error != nil || result?.isFinal == true {
                Task { @MainActor in self.stopListening() }
            }
        }
    }

    func stopListening() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        task?.finish()
        request    = nil
        task       = nil
        isListening = false

        let final = transcript
        if !final.isEmpty { onFinal?(final) }
        onFinal = nil
    }

    /// One-shot: record for `duration` seconds then return transcript.
    func transcribe(duration: TimeInterval = 5) async -> String {
        return await withCheckedContinuation { continuation in
            startListening { text in continuation.resume(returning: text) }
            Task {
                try? await Task.sleep(for: .seconds(duration))
                await MainActor.run { self.stopListening() }
            }
        }
    }
}
