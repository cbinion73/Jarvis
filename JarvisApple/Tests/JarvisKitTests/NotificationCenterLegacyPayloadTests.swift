import Foundation
import Testing
@testable import JarvisKit

struct NotificationCenterLegacyPayloadTests {
    @Test
    func decodesLegacyNotificationCenterOverviewWithoutRoutingMetadata() throws {
        let data = """
        {
          "notifications": [
            {
              "id": "notif-legacy-1",
              "event_id": "",
              "category": "system",
              "title": "Focus is active",
              "detail": "JARVIS should keep interruptions quieter right now.",
              "body": "JARVIS should keep interruptions quieter right now.",
              "severity": "low",
              "status": "seen",
              "created_at": "2026-06-02T04:20:53.804226+00:00",
              "updated_at": "2026-06-02T04:20:53.804226+00:00",
              "expires_at": "",
              "audience": "household",
              "delivery_mode": "quiet_store",
              "navigation_target": "systems",
              "available_actions": ["open", "dismiss"],
              "why_now": "Current focus state changes how notifications should be delivered.",
              "source_summary": "Focus",
              "decision_reason": "Focus is active on the phone, so JARVIS should keep interruptions quieter.",
              "posture_snapshot": {
                "mode": "focus_active",
                "label": "Focus active",
                "reason": "Focus is active on the phone, so JARVIS should keep interruptions quieter.",
                "recommended_delivery": "quiet_store",
                "quiet_hours": true,
                "hour_local": 4,
                "needs_count": 0,
                "alert_count": 0
              },
              "badge": 0
            }
          ]
        }
        """.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(NotificationCenterOverview.self, from: data)
        #expect(decoded.notifications.count == 1)
        #expect(decoded.summary.total == 1)
        #expect(decoded.summary.seen == 1)
        #expect(decoded.routing.mode == "legacy")
        #expect(decoded.routing.recommendedDelivery == "badge_only")
        #expect(decoded.eventSummary.recentCount == 0)
    }
}
