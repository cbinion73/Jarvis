import Foundation

public enum JarvisNotificationCategory: String, CaseIterable, Sendable {
    case briefing
    case approval
    case healthSignal
    case healthFollowup
    case urgentAttention
}
