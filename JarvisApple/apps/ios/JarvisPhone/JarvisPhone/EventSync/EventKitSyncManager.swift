import EventKit
import JarvisKit

/// Reads Calendar events and Reminders directly from the device (all calendars —
/// iCloud, local, Exchange, Google synced locally) and pushes to the JARVIS server.
/// Replaces the Google Calendar API dependency for events that live on the device.
@MainActor
final class EventKitSyncManager: ObservableObject {

    static let shared = EventKitSyncManager()

    @Published var calendarStatus: EKAuthorizationStatus = .notDetermined
    @Published var remindersStatus: EKAuthorizationStatus = .notDetermined
    @Published var lastSyncDate: Date?
    @Published var lastEventCount = 0
    @Published var lastReminderCount = 0
    @Published var isSyncing = false

    private let store = EKEventStore()

    private override init() {
        calendarStatus  = EKEventStore.authorizationStatus(for: .event)
        remindersStatus = EKEventStore.authorizationStatus(for: .reminder)
    }

    // MARK: - Authorization

    func requestAccess() async {
        do {
            let calOK  = try await store.requestFullAccessToEvents()
            let remOK  = try await store.requestFullAccessToReminders()
            calendarStatus  = calOK  ? .fullAccess : .denied
            remindersStatus = remOK  ? .fullAccess : .denied
        } catch {
            print("[EventKit] Auth error: \(error)")
        }
    }

    // MARK: - Sync

    func syncAll() async {
        guard calendarStatus == .fullAccess || remindersStatus == .fullAccess else {
            await requestAccess()
            return
        }
        isSyncing = true
        defer { isSyncing = false }

        await withTaskGroup(of: Void.self) { group in
            if calendarStatus == .fullAccess {
                group.addTask { await self.syncCalendar() }
            }
            if remindersStatus == .fullAccess {
                group.addTask { await self.syncReminders() }
            }
        }
        lastSyncDate = Date()
    }

    // MARK: - Calendar

    private func syncCalendar() async {
        let now    = Date()
        let twoWeeks = Calendar.current.date(byAdding: .day, value: 14, to: now)!
        let predicate = store.predicateForEvents(withStart: now, end: twoWeeks, calendars: nil)
        let events = store.events(matching: predicate)

        let payload: [[String: Any]] = events.prefix(50).map { event in
            var dict: [String: Any] = [
                "id":       event.eventIdentifier ?? UUID().uuidString,
                "title":    event.title ?? "",
                "start":    ISO8601DateFormatter().string(from: event.startDate),
                "end":      ISO8601DateFormatter().string(from: event.endDate),
                "all_day":  event.isAllDay,
                "calendar": event.calendar?.title ?? "",
                "location": event.location ?? "",
            ]
            if let notes = event.notes { dict["notes"] = notes }
            if let url   = event.url   { dict["url"]   = url.absoluteString }
            return dict
        }

        await push(path: "/api/apple/calendar", payload: ["events": payload, "source": "eventkit"])
        lastEventCount = events.count
    }

    // MARK: - Reminders

    private func syncReminders() async {
        let predicate = store.predicateForIncompleteReminders(
            withDueDateStarting: nil, ending: nil, calendars: nil
        )

        let reminders: [EKReminder] = await withCheckedContinuation { continuation in
            store.fetchReminders(matching: predicate) { items in
                continuation.resume(returning: items ?? [])
            }
        }

        let payload: [[String: Any]] = reminders.prefix(50).map { r in
            var dict: [String: Any] = [
                "id":       r.calendarItemIdentifier,
                "title":    r.title ?? "",
                "list":     r.calendar?.title ?? "",
                "priority": r.priority,
                "completed": r.isCompleted,
            ]
            if let due = r.dueDateComponents?.date {
                dict["due"] = ISO8601DateFormatter().string(from: due)
            }
            if let notes = r.notes { dict["notes"] = notes }
            return dict
        }

        await push(path: "/api/apple/reminders", payload: ["reminders": payload, "source": "eventkit"])
        lastReminderCount = reminders.count
    }

    // MARK: - HTTP push

    private func push(path: String, payload: [String: Any]) async {
        guard let url = URL(string: JARVISEnvironment.baseURL.absoluteString + path),
              let body = try? JSONSerialization.data(withJSONObject: payload) else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        _ = try? await URLSession.shared.data(for: req)
    }
}
