@preconcurrency import EventKit
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
    private let client = AppleAPIClient.shared

    private init() {
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

    func requestAccessAndSync() async {
        guard calendarStatus != .fullAccess || remindersStatus != .fullAccess else {
            await syncAll()
            return
        }
        await requestAccess()
        await syncAll()
    }

    func syncAll() async {
        guard calendarStatus == .fullAccess || remindersStatus == .fullAccess else {
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

        let payload: [CalendarEventRecord] = events.prefix(50).map { event in
            CalendarEventRecord(
                id: event.eventIdentifier ?? UUID().uuidString,
                title: event.title ?? "",
                start: ISO8601DateFormatter().string(from: event.startDate),
                end: ISO8601DateFormatter().string(from: event.endDate),
                allDay: event.isAllDay,
                calendar: event.calendar?.title ?? "",
                location: event.location ?? "",
                notes: event.notes,
                url: event.url?.absoluteString
            )
        }

        await push(path: "/api/apple/calendar", payload: CalendarPush(events: payload, source: "eventkit"))
        lastEventCount = events.count
    }

    // MARK: - Reminders

    private func syncReminders() async {
        let predicate = store.predicateForIncompleteReminders(
            withDueDateStarting: nil, ending: nil, calendars: nil
        )

        // Extract Sendable data inside the callback before crossing async boundary
        struct ReminderData: Sendable {
            let id: String, title: String, list: String
            let priority: Int, completed: Bool, due: String?, notes: String?
        }

        let extracted: [ReminderData] = await withUnsafeContinuation { continuation in
            store.fetchReminders(matching: predicate) { items in
                let data = (items ?? []).prefix(50).map { r in
                    ReminderData(
                        id:        r.calendarItemIdentifier,
                        title:     r.title ?? "",
                        list:      r.calendar?.title ?? "",
                        priority:  r.priority,
                        completed: r.isCompleted,
                        due:       r.dueDateComponents?.date.map { ISO8601DateFormatter().string(from: $0) },
                        notes:     r.notes
                    )
                }
                continuation.resume(returning: data)
            }
        }

        let payload: [ReminderRecord] = extracted.map { r in
            ReminderRecord(
                id: r.id,
                title: r.title,
                list: r.list,
                priority: r.priority,
                completed: r.completed,
                due: r.due,
                notes: r.notes
            )
        }

        await push(path: "/api/apple/reminders", payload: ReminderPush(reminders: payload, source: "eventkit"))
        lastReminderCount = extracted.count
    }

    // MARK: - HTTP push

    private func push<P: Encodable & Sendable>(path: String, payload: P) async {
        try? await client.postAcknowledged(path, body: payload)
    }
}

private struct CalendarEventRecord: Encodable, Sendable {
    let id: String
    let title: String
    let start: String
    let end: String
    let allDay: Bool
    let calendar: String
    let location: String
    let notes: String?
    let url: String?

    enum CodingKeys: String, CodingKey {
        case id, title, start, end, calendar, location, notes, url
        case allDay = "all_day"
    }
}

private struct CalendarPush: Encodable, Sendable {
    let events: [CalendarEventRecord]
    let source: String
}

private struct ReminderRecord: Encodable, Sendable {
    let id: String
    let title: String
    let list: String
    let priority: Int
    let completed: Bool
    let due: String?
    let notes: String?
}

private struct ReminderPush: Encodable, Sendable {
    let reminders: [ReminderRecord]
    let source: String
}
