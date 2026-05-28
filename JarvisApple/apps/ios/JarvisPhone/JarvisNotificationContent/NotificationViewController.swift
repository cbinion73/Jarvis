import UIKit
import UserNotifications
import UserNotificationsUI

/// Custom notification UI for JARVIS approval requests.
/// Shown when user swipes down on an approval push notification.
/// Displays the full request text + Approve/Deny buttons inline.
final class NotificationViewController: UIViewController, @preconcurrency UNNotificationContentExtension {

    // MARK: - UI

    private let riskBar       = UIView()
    private let agentLabel    = UILabel()
    private let titleLabel    = UILabel()
    private let bodyLabel     = UILabel()
    private let expiryLabel   = UILabel()
    private let approveButton = UIButton(type: .system)
    private let denyButton    = UIButton(type: .system)
    private let statusLabel   = UILabel()

    private var requestId: String?
    private var baseURL: String {
        UserDefaults(suiteName: "group.com.binion.jarvisphone")?
            .string(forKey: "jarvis.base_url")
            ?? "https://jarvis.teambinion.org"
    }

    // MARK: - Lifecycle

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(white: 0.08, alpha: 1)
        setupUI()
    }

    // MARK: - UNNotificationContentExtension

    func didReceive(_ notification: UNNotification) {
        let info = notification.request.content.userInfo

        requestId = info["request_id"] as? String

        let risk  = (info["risk"]  as? String) ?? "medium"
        let agent = (info["agent"] as? String) ?? "JARVIS"
        let text  = notification.request.content.body
        let exp   = info["expires_in"] as? String

        // Risk colour
        riskBar.backgroundColor = riskColor(risk)
        agentLabel.text = agent.uppercased()
        titleLabel.text = notification.request.content.title
        bodyLabel.text  = text
        expiryLabel.text = exp.map { "Expires: \($0)" } ?? ""
        expiryLabel.isHidden = (exp == nil)
    }

    func didReceive(_ response: UNNotificationResponse,
                    completionHandler completion: @escaping (UNNotificationContentExtensionResponseOption) -> Void) {
        switch response.actionIdentifier {
        case "APPROVE_ACTION":
            handleApprove(completion: completion)
        case "DENY_ACTION":
            handleDeny(completion: completion)
        default:
            completion(.dismissAndForwardAction)
        }
    }

    // MARK: - Actions

    private func handleApprove(completion: @escaping (UNNotificationContentExtensionResponseOption) -> Void) {
        guard let rid = requestId else {
            completion(.dismiss)
            return
        }
        setStatus("Approving…", color: .systemGreen)
        approveButton.isEnabled = false
        denyButton.isEnabled    = false

        Task {
            let url = URL(string: "\(baseURL)/api/apple/approvals/\(rid)/approve")!
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try? JSONSerialization.data(withJSONObject: ["approved_by": "chris"])
            _ = try? await URLSession.shared.data(for: req)

            await MainActor.run {
                setStatus("✓ Approved", color: .systemGreen)
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                    completion(.dismiss)
                }
            }
        }
    }

    private func handleDeny(completion: @escaping (UNNotificationContentExtensionResponseOption) -> Void) {
        setStatus("Dismissed", color: .systemOrange)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
            completion(.dismiss)
        }
    }

    private func setStatus(_ text: String, color: UIColor) {
        statusLabel.text      = text
        statusLabel.textColor = color
        statusLabel.isHidden  = false
    }

    // MARK: - UI Setup

    private func setupUI() {
        // Risk bar (left edge accent)
        riskBar.translatesAutoresizingMaskIntoConstraints = false
        riskBar.layer.cornerRadius = 2
        view.addSubview(riskBar)

        // Agent label
        agentLabel.font = .systemFont(ofSize: 10, weight: .semibold)
        agentLabel.textColor = UIColor(white: 0.5, alpha: 1)

        // Title label
        titleLabel.font = .systemFont(ofSize: 15, weight: .bold)
        titleLabel.textColor = .white
        titleLabel.numberOfLines = 2

        // Body label
        bodyLabel.font = .systemFont(ofSize: 13)
        bodyLabel.textColor = UIColor(white: 0.8, alpha: 1)
        bodyLabel.numberOfLines = 4

        // Expiry
        expiryLabel.font = .systemFont(ofSize: 11)
        expiryLabel.textColor = UIColor(white: 0.5, alpha: 1)

        // Status
        statusLabel.font = .systemFont(ofSize: 13, weight: .medium)
        statusLabel.isHidden = true

        // Approve button
        approveButton.setTitle("Approve", for: .normal)
        approveButton.setImage(UIImage(systemName: "checkmark.shield.fill"), for: .normal)
        approveButton.tintColor = .white
        approveButton.backgroundColor = UIColor.systemGreen.withAlphaComponent(0.85)
        approveButton.layer.cornerRadius = 10
        approveButton.contentEdgeInsets = UIEdgeInsets(top: 10, left: 16, bottom: 10, right: 16)
        approveButton.addTarget(self, action: #selector(approveTapped), for: .touchUpInside)

        // Deny button
        denyButton.setTitle("Dismiss", for: .normal)
        denyButton.tintColor = UIColor(white: 0.6, alpha: 1)
        denyButton.backgroundColor = UIColor(white: 0.18, alpha: 1)
        denyButton.layer.cornerRadius = 10
        denyButton.contentEdgeInsets = UIEdgeInsets(top: 10, left: 16, bottom: 10, right: 16)
        denyButton.addTarget(self, action: #selector(denyTapped), for: .touchUpInside)

        // Stack
        let textStack = UIStackView(arrangedSubviews: [agentLabel, titleLabel, bodyLabel, expiryLabel])
        textStack.axis = .vertical
        textStack.spacing = 4

        let buttonStack = UIStackView(arrangedSubviews: [approveButton, denyButton])
        buttonStack.axis = .horizontal
        buttonStack.spacing = 10
        buttonStack.distribution = .fillEqually

        let mainStack = UIStackView(arrangedSubviews: [textStack, buttonStack, statusLabel])
        mainStack.axis = .vertical
        mainStack.spacing = 14
        mainStack.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(mainStack)

        NSLayoutConstraint.activate([
            riskBar.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 12),
            riskBar.topAnchor.constraint(equalTo: view.topAnchor, constant: 14),
            riskBar.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -14),
            riskBar.widthAnchor.constraint(equalToConstant: 4),

            mainStack.leadingAnchor.constraint(equalTo: riskBar.trailingAnchor, constant: 12),
            mainStack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
            mainStack.topAnchor.constraint(equalTo: view.topAnchor, constant: 16),
            mainStack.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -16),
        ])
    }

    @objc private func approveTapped() {
        extensionContext?.performNotificationDefaultAction()
    }

    @objc private func denyTapped() {
        extensionContext?.dismissNotificationContentExtension()
    }

    private func riskColor(_ risk: String) -> UIColor {
        switch risk {
        case "high":   return .systemRed
        case "medium": return .systemOrange
        default:       return .systemYellow
        }
    }
}
