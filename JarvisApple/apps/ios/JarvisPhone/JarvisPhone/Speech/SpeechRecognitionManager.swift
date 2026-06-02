import Speech
import AVFoundation

enum SpeechRecognitionError: LocalizedError {
    case unavailable
    case recognizerMissing
    case audioEngineStartFailed
    case invalidInputFormat
    case audioSessionSetupFailed(String)

    var errorDescription: String? {
        switch self {
        case .unavailable:
            return "Speech recognition unavailable"
        case .recognizerMissing:
            return "Speech recognizer is unavailable on this device"
        case .audioEngineStartFailed:
            return "Microphone input could not start"
        case .invalidInputFormat:
            return "Microphone input format is unavailable"
        case .audioSessionSetupFailed(let step):
            return "Microphone input could not start (\(step))"
        }
    }
}

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
    private var audioEngine        = AVAudioEngine()
    private var onFinal:           ((String) -> Void)?
    private var onPartial:         ((String) -> Void)?
    private var suspendedSoundAnalysis = false
    private var stopRequested = false
    private var autoStopTask: Task<Void, Never>?

    private var hasActiveRecognitionSession: Bool {
        isListening || request != nil || task != nil || audioEngine.isRunning
    }

    private init() {
        refreshAuthorizationStatus()
    }

    // MARK: - Authorization

    func refreshAuthorizationStatus() {
        let speechStatus = SFSpeechRecognizer.authorizationStatus()
        let audioStatus = AVAudioSession.sharedInstance().recordPermission
        isAuthorized = (speechStatus == .authorized) && (audioStatus == .granted)
    }

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
    func startListening(onPartial: ((String) -> Void)? = nil, onFinal: @escaping (String) -> Void) {
        if hasActiveRecognitionSession {
            print("[JARVIS Speech] Start requested while session active. Ignoring duplicate start.")
            return
        }
        Task { @MainActor [weak self] in
            await self?.beginListening(onPartial: onPartial, onFinal: onFinal)
        }
    }

    private func beginListening(onPartial: ((String) -> Void)? = nil, onFinal: @escaping (String) -> Void) async {
        print("[JARVIS Speech] Mic tapped. authorized=\(isAuthorized)")
        if !isAuthorized {
            await checkAuthorization()
            print("[JARVIS Speech] Authorization refreshed. authorized=\(isAuthorized)")
        }

        guard isAuthorized else {
            fail(with: .unavailable)
            return
        }
        guard !isListening else { return }
        guard let recognizer, recognizer.isAvailable else {
            fail(with: .recognizerMissing)
            return
        }

        self.onFinal = onFinal
        self.onPartial = onPartial
        transcript   = ""
        errorMessage = nil
        stopRequested = false
        resetSessionState()

        if SoundAnalysisManager.shared.isListening {
            suspendedSoundAnalysis = true
            SoundAnalysisManager.shared.suspendForSpeechCapture()
        } else {
            suspendedSoundAnalysis = false
        }

        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults     = true
        req.requiresOnDeviceRecognition    = false  // allow server for better accuracy
        request = req

        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [.defaultToSpeaker, .allowBluetoothHFP, .duckOthers]
            )
        } catch {
            print("[JARVIS Speech] setCategory failed: \(error.localizedDescription)")
            fail(with: .audioSessionSetupFailed("setCategory"))
            return
        }
        do {
            try session.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            print("[JARVIS Speech] setActive failed: \(error.localizedDescription)")
            fail(with: .audioSessionSetupFailed("setActive"))
            return
        }

        audioEngine = AVAudioEngine()
        let node = audioEngine.inputNode
        let inputFormat = node.inputFormat(forBus: 0)
        guard inputFormat.sampleRate > 0, inputFormat.channelCount > 0 else {
            fail(with: .invalidInputFormat)
            return
        }
        node.removeTap(onBus: 0)
        Self.installRecognitionTap(on: node, format: inputFormat, request: req)

        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            print("[JARVIS Speech] audioEngine.start failed: \(error.localizedDescription)")
            fail(with: .audioEngineStartFailed)
            return
        }
        isListening = true
        print("[JARVIS Speech] Listening started.")

        task = Self.makeRecognitionTask(
            recognizer: recognizer,
            request: req,
            onTranscript: { [weak self] transcript in
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    self.transcript = transcript
                    self.onPartial?(transcript)
                    self.scheduleAutoStopAfterPause()
                }
            },
            onError: { [weak self] message in
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    if self.stopRequested, Self.isExpectedCancellation(message) {
                        print("[JARVIS Speech] Ignoring expected cancellation: \(message)")
                        return
                    }
                    if Self.isNoSpeechDetected(message) {
                        print("[JARVIS Speech] No speech detected. Ending turn quietly.")
                        self.errorMessage = nil
                        self.stopListening()
                        return
                    }
                    self.errorMessage = message
                    self.stopListening()
                }
            },
            onFinal: { [weak self] in
                Task { @MainActor [weak self] in
                    self?.stopListening()
                }
            }
        )
    }

    func stopListening() {
        let final = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        stopRequested = true
        autoStopTask?.cancel()
        autoStopTask = nil
        print("[JARVIS Speech] stopListening called. finalLength=\(final.count)")
        resetSessionState()
        isListening = false

        if !final.isEmpty {
            print("[JARVIS Speech] Sending transcript: \(final)")
        }
        onFinal?(final)
        onPartial = nil
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

    private func fail(with error: SpeechRecognitionError) {
        errorMessage = error.localizedDescription
        print("[JARVIS Speech] Failure: \(error.localizedDescription)")
        resetSessionState()
        isListening = false
        onPartial = nil
        onFinal = nil
    }

    private func resetSessionState() {
        autoStopTask?.cancel()
        autoStopTask = nil
        if audioEngine.isRunning {
            audioEngine.stop()
        }
        audioEngine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        task?.cancel()
        request = nil
        task = nil
        audioEngine = AVAudioEngine()
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        if suspendedSoundAnalysis {
            suspendedSoundAnalysis = false
            SoundAnalysisManager.shared.resumeAfterSpeechCapture()
        }
    }

    private nonisolated static func isExpectedCancellation(_ message: String) -> Bool {
        let lowered = message.lowercased()
        return lowered.contains("cancel")
    }

    private func scheduleAutoStopAfterPause() {
        let currentTranscript = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard currentTranscript.isEmpty == false else { return }
        autoStopTask?.cancel()
        autoStopTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(1.2))
            await MainActor.run {
                guard let self else { return }
                guard self.isListening else { return }
                let latest = self.transcript.trimmingCharacters(in: .whitespacesAndNewlines)
                guard latest.isEmpty == false else { return }
                print("[JARVIS Speech] Auto-stopping after pause.")
                self.stopListening()
            }
        }
    }

    private nonisolated static func isNoSpeechDetected(_ message: String) -> Bool {
        let lowered = message.lowercased()
        return lowered.contains("no speech detected")
            || lowered.contains("speech was not detected")
    }

    // nonisolated so audio and speech callbacks do not inherit @MainActor isolation
    private nonisolated static func installRecognitionTap(
        on inputNode: AVAudioInputNode,
        format: AVAudioFormat,
        request: SFSpeechAudioBufferRecognitionRequest
    ) {
        let requestBox = UncheckedSendable(request)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            requestBox.value.append(buffer)
        }
    }

    // nonisolated so the recognition callback does not trip actor queue assertions
    private nonisolated static func makeRecognitionTask(
        recognizer: SFSpeechRecognizer,
        request: SFSpeechAudioBufferRecognitionRequest,
        onTranscript: @escaping @Sendable (String) -> Void,
        onError: @escaping @Sendable (String) -> Void,
        onFinal: @escaping @Sendable () -> Void
    ) -> SFSpeechRecognitionTask {
        recognizer.recognitionTask(with: request) { result, error in
            if let result {
                onTranscript(result.bestTranscription.formattedString)
            }
            if let error {
                onError(error.localizedDescription)
            } else if result?.isFinal == true {
                onFinal()
            }
        }
    }
}
