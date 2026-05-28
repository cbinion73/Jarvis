import Vision
import UIKit
import JarvisKit

/// On-device OCR, barcode scanning, and document detection via Vision framework.
/// Free — runs on Neural Engine, no API calls required.
@MainActor
final class VisionManager: ObservableObject {

    static let shared = VisionManager()

    @Published var recognizedText:  String = ""
    @Published var barcodeValue:    String = ""
    @Published var isProcessing     = false
    @Published var errorMessage:    String?

    private init() {}

    // MARK: - OCR: Recognize text in image

    func recognizeText(in image: UIImage) async -> String {
        guard let cgImage = image.cgImage else { return "" }
        isProcessing = true
        defer { isProcessing = false }

        return await withCheckedContinuation { continuation in
            let request = VNRecognizeTextRequest { req, error in
                guard error == nil,
                      let observations = req.results as? [VNRecognizedTextObservation]
                else {
                    continuation.resume(returning: "")
                    return
                }
                let text = observations
                    .compactMap { $0.topCandidates(1).first?.string }
                    .joined(separator: "\n")
                continuation.resume(returning: text)
            }
            request.recognitionLevel    = .accurate
            request.usesLanguageCorrection = true
            request.recognitionLanguages = ["en-US"]

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])
        }
    }

    // MARK: - Barcode / QR scanning

    func scanBarcode(in image: UIImage) async -> String? {
        guard let cgImage = image.cgImage else { return nil }

        return await withCheckedContinuation { continuation in
            let request = VNDetectBarcodesRequest { req, _ in
                let result = (req.results as? [VNBarcodeObservation])?.first?.payloadStringValue
                continuation.resume(returning: result)
            }
            request.symbologies = [.qr, .ean13, .ean8, .code128, .upce, .pdf417]
            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            try? handler.perform([request])
        }
    }

    // MARK: - Scan + send to JARVIS

    /// OCR an image and POST the recognized text to JARVIS for processing.
    func scanAndSend(_ image: UIImage, context: String = "document") async -> String {
        let text = await recognizeText(in: image)
        guard !text.isEmpty else { return "No text found" }

        recognizedText = text

        guard let url  = URL(string: JARVISEnvironment.baseURL.absoluteString + "/api/apple/vision/scan"),
              let body = try? JSONSerialization.data(withJSONObject: [
                "text": text, "context": context, "source": "vision_ocr"
              ]) else { return text }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        _ = try? await URLSession.shared.data(for: req)

        return text
    }
}
