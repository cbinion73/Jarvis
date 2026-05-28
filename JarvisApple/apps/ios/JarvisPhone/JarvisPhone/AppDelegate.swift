import UIKit
import UserNotifications
import JarvisKit

final class AppDelegate: NSObject, UIApplicationDelegate {

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        requestNotificationPermission()
        registerNotificationCategories()
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    // MARK: - Scene lifecycle

    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        if connectingSceneSession.role == UISceneSession.Role.carTemplateApplication {
            let config = UISceneConfiguration(
                name: "CarPlay Configuration",
                sessionRole: connectingSceneSession.role
            )
            config.delegateClass = CarPlaySceneDelegate.self
            return config
        }
        let config = UISceneConfiguration(
            name: "Default Configuration",
            sessionRole: connectingSceneSession.role
        )
        config.delegateClass = SceneDelegate.self
        return config
    }

    // MARK: - Push notifications

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        print("[JARVIS] APNs token: \(token)")

        // Register with JARVIS server so it can send pushes
        Task {
            await AppleAPIClient.shared.registerDeviceToken(token)
        }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        print("[JARVIS] APNs registration failed: \(error)")
    }

    // MARK: - Private

    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .badge, .sound, .criticalAlert]
        ) { granted, _ in
            if granted {
                DispatchQueue.main.async {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            }
        }
    }

    private func registerNotificationCategories() {
        // Approval category — shown inline by NotificationViewController
        let approveAction = UNNotificationAction(
            identifier: "APPROVE_ACTION",
            title: "✅ Approve",
            options: [.authenticationRequired, .foreground]
        )
        let denyAction = UNNotificationAction(
            identifier: "DENY_ACTION",
            title: "Dismiss",
            options: [.destructive]
        )
        let approvalCategory = UNNotificationCategory(
            identifier: "approval",
            actions: [approveAction, denyAction],
            intentIdentifiers: [],
            options: [.customDismissAction]
        )

        // Briefing category
        let openBriefAction = UNNotificationAction(
            identifier: "OPEN_BRIEF",
            title: "Read Brief",
            options: [.foreground]
        )
        let briefCategory = UNNotificationCategory(
            identifier: "briefing",
            actions: [openBriefAction],
            intentIdentifiers: [],
            options: []
        )

        UNUserNotificationCenter.current().setNotificationCategories([approvalCategory, briefCategory])
    }
}

// MARK: - UNUserNotificationCenterDelegate

extension AppDelegate: UNUserNotificationCenterDelegate {

    /// Show notifications even when app is in foreground
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .badge, .sound])
    }

    /// Handle notification tap — route to correct tab
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let category = response.notification.request.content.categoryIdentifier
        switch category {
        case "approval":
            NotificationCenter.default.post(name: .jarvisOpenNeeds, object: nil)
        case "briefing":
            NotificationCenter.default.post(name: .jarvisOpenBrief, object: nil)
        default:
            break
        }
        completionHandler()
    }

    /// Handle silent "speak" background push — JARVIS server sends text, iOS speaks it.
    func application(
        _ application: UIApplication,
        didReceiveRemoteNotification userInfo: [AnyHashable: Any],
        fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
    ) {
        if let text = userInfo["speak"] as? String, !text.isEmpty {
            Task { @MainActor in
                SpeechManager.shared.speak(text)
            }
            completionHandler(.newData)
        } else {
            completionHandler(.noData)
        }
    }
}

// MARK: - Notification names

extension Notification.Name {
    static let jarvisOpenNeeds = Notification.Name("jarvis.open.needs")
    static let jarvisOpenBrief = Notification.Name("jarvis.open.brief")
}
