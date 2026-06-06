import SwiftUI
import JarvisKit

// MARK: - PublishView  "The Press Room"
// Robbie Robertson · Publishing & Revenue

struct PublishView: View {

    @State private var overview: PublishOverview?
    @State private var isLoading  = false
    @State private var error: String?
    @State private var reviewActionInFlight: String?
    @State private var checklistActionInFlight: String?
    @State private var checklistActionMessage = ""
    @State private var checklistActionError = ""

    private let green = Color(red: 0.15, green: 0.85, blue: 0.45)

    var body: some View {
        NavigationStack {
            ZStack {
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.01, green: 0.07, blue: 0.03), Color.black],
                        startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.5)
                    )
                }
                .ignoresSafeArea()

                Group {
                    if isLoading && overview == nil { loadingView }
                    else if let ov = overview { contentView(ov) }
                    else if let e = error { errorView(e) }
                    else { loadingView }
                }
            }
            .navigationTitle("Publish")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { Task { await load() } } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .glassEffect(in: Circle())
                }
            }
        }
        .task { await load() }
        .refreshable { await load() }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.richtext.fill")
                .font(.system(size: 36)).foregroundStyle(green.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Loading publishing data…").font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Content

    @ViewBuilder
    private func contentView(_ ov: PublishOverview) -> some View {
        ScrollView {
            VStack(spacing: 14) {
                publishStoryboardHeader(ov)

                if !ov.actionItems.isEmpty {
                    PressSection(title: "Command Queue", icon: "sparkles.rectangle.stack.fill", accent: green) {
                        ForEach(ov.actionItems) { item in
                            ActionItemRow(item: item, green: green)
                            if item.id != ov.actionItems.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                if let launch = ov.launchControl {
                    launchControlCard(launch, reviewCount: ov.pendingReviewsCount)
                }

                if let workspace = ov.launchWorkspace {
                    launchWorkspaceSection(workspace)
                }

                if let continuity = ov.continuity,
                   continuity.profileFactCount > 0
                    || continuity.pendingReviewPressure > 0
                    || !continuity.activePlatforms.isEmpty
                    || !continuity.guidanceLines.isEmpty
                    || !continuity.recentProfileFacts.isEmpty
                    || !continuity.recentFirstLight.isEmpty {
                    continuitySection(continuity)
                }

                // ── Revenue banner ────────────────────────────────
                revenueBanner(ov.revenueSummary)

                if !ov.pendingReviews.isEmpty {
                    PressSection(title: "Ready For Review", icon: "checklist.unchecked", accent: green) {
                        ForEach(ov.pendingReviews) { review in
                            ReviewRow(
                                review: review,
                                green: green,
                                isActing: reviewActionInFlight == review.id,
                                onApprove: { Task { await approveReview(review.id) } },
                                onRevise: { Task { await requestRevision(review.id) } }
                            )
                            if review.id != ov.pendingReviews.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                // ── Projects ──────────────────────────────────────
                if !ov.projects.isEmpty {
                    PressSection(title: "Projects", icon: "doc.text.fill", accent: green) {
                        ForEach(ov.projects) { proj in
                            ProjectRow(project: proj, green: green)
                            if proj.id != ov.projects.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                // ── Revenue streams ───────────────────────────────
                if !ov.revenueSummary.streams.isEmpty {
                    PressSection(title: "Revenue Streams", icon: "dollarsign.circle.fill", accent: green) {
                        ForEach(ov.revenueSummary.streams) { stream in
                            StreamRow(stream: stream, green: green)
                            if stream.id != ov.revenueSummary.streams.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                // ── Upcoming calendar ─────────────────────────────
                if !ov.upcoming.isEmpty {
                    PressSection(title: "Upcoming Content", icon: "calendar.badge.plus", accent: green) {
                        ForEach(ov.upcoming) { item in
                            CalendarRow(item: item)
                            if item.id != ov.upcoming.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                supervisoryStrip(ov)
            }
            .padding(.horizontal, 16).padding(.vertical, 12)
        }
    }

    @ViewBuilder
    private func publishStoryboardHeader(_ ov: PublishOverview) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 14) {
                RoundedRectangle(cornerRadius: 22)
                    .fill(
                        LinearGradient(
                            colors: [green.opacity(0.28), Color(red: 0.34, green: 0.24, blue: 0.08), Color.black.opacity(0.92)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 88, height: 118)
                    .overlay(
                        VStack(spacing: 8) {
                            Image(systemName: "book.closed.fill")
                                .font(.system(size: 28, weight: .bold))
                                .foregroundStyle(green)
                            Text(activeProjectTitle(in: ov))
                                .font(.system(size: 10, weight: .bold))
                                .multilineTextAlignment(.center)
                                .foregroundStyle(.white.opacity(0.92))
                                .lineLimit(3)
                                .padding(.horizontal, 6)
                        }
                    )

                VStack(alignment: .leading, spacing: 8) {
                    Text("GHOSTWRITR PUBLISH HANDOFF")
                        .font(.system(size: 10, weight: .bold))
                        .tracking(1.4)
                        .foregroundStyle(green.opacity(0.82))
                    Text(activeProjectTitle(in: ov))
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.white)
                    Text(activeProjectSubtitle(in: ov))
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.72))
                    HStack(spacing: 8) {
                        publishChip(launchStatusText(in: ov), tint: .orange)
                        publishChip("\(ov.pendingReviewsCount) review\(ov.pendingReviewsCount == 1 ? "" : "s")", tint: green)
                    }
                }
                Spacer(minLength: 0)
            }

            HStack(spacing: 10) {
                storyboardMetric(title: "Package", value: packageStatusText(in: ov), tint: .orange)
                storyboardMetric(title: "Projects", value: "\(ov.projects.count)", tint: green)
                storyboardMetric(title: "Streams", value: "\(ov.revenueSummary.streamCount)", tint: .cyan)
            }
        }
        .padding(18)
        .glassEffect(in: RoundedRectangle(cornerRadius: 22))
        .overlay(
            RoundedRectangle(cornerRadius: 22)
                .stroke(green.opacity(0.14), lineWidth: 1)
        )
    }

    // MARK: - Revenue banner

    @ViewBuilder
    private func revenueBanner(_ rev: RevenueSummary) -> some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text("MONTHLY ESTIMATE")
                    .font(.system(size: 9, weight: .bold)).tracking(1.2).foregroundStyle(.secondary)
                Text(rev.monthlyEstimate.formatted(.currency(code: "USD")))
                    .font(.system(size: 32, weight: .bold).monospacedDigit())
                    .foregroundStyle(rev.monthlyEstimate > 0 ? green : .white.opacity(0.3))
                Text("\(rev.streamCount) active stream\(rev.streamCount == 1 ? "" : "s")")
                    .font(.caption2).foregroundStyle(.secondary)
            }
            Spacer()
            ZStack {
                Circle().fill(green.opacity(0.1)).frame(width: 56, height: 56)
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(rev.monthlyEstimate > 0 ? green : .white.opacity(0.2))
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(green.opacity(0.15), lineWidth: 1))
    }

    @ViewBuilder
    private func launchControlCard(_ launch: PublishLaunchControl, reviewCount: Int) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("LAUNCH CONTROL")
                        .font(.system(size: 9, weight: .bold)).tracking(1.2).foregroundStyle(.secondary)
                    Text(launch.title)
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.white)
                    HStack(spacing: 6) {
                        if !launch.phase.isEmpty {
                            badge(launch.phase.replacingOccurrences(of: "_", with: " ").capitalized, color: .cyan)
                        }
                        if !launch.status.isEmpty {
                            badge(launch.status.capitalized, color: .orange)
                        }
                        if !launch.platform.isEmpty {
                            badge(launch.platform.replacingOccurrences(of: "_", with: " ").uppercased(), color: green)
                        }
                    }
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 4) {
                    Text(daysLabel(for: launch.daysToLaunch))
                        .font(.system(size: 28, weight: .bold).monospacedDigit())
                        .foregroundStyle(launch.daysToLaunch ?? 0 <= 7 ? .orange : green)
                    Text("to launch")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            HStack(spacing: 10) {
                metricPill("\(reviewCount)", "Reviews", tint: .orange)
                metricPill("\(launch.postsPendingApproval)", "Posts Waiting", tint: .yellow)
                metricPill("\(launch.postsScheduled)", "Scheduled", tint: green)
            }

            if !launch.nextAction.isEmpty {
                Text(launch.nextAction)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(.white)
            }
            if !launch.launchDate.isEmpty {
                Text("Launch target: \(launch.launchDate.prefix(10))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(16)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(green.opacity(0.15), lineWidth: 1))
    }

    @ViewBuilder
    private func launchWorkspaceSection(_ workspace: PublishLaunchWorkspace) -> some View {
        PressSection(title: "Platform Readiness", icon: "shippingbox.fill", accent: green) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(workspace.title)
                            .font(.headline)
                            .foregroundStyle(.white)
                        HStack(spacing: 6) {
                            if !workspace.platform.isEmpty {
                                badge(workspace.platform.replacingOccurrences(of: "_", with: " ").uppercased(), color: green)
                            }
                            if !workspace.assetStatus.isEmpty {
                                badge(workspace.assetStatus.capitalized, color: assetStatusColor(workspace.assetStatus))
                            }
                        }
                    }
                    Spacer()
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("\(workspace.checklistPercent)%")
                            .font(.system(size: 28, weight: .bold).monospacedDigit())
                            .foregroundStyle(workspace.checklistPercent >= 75 ? green : .orange)
                        Text(workspace.checklistProgress.isEmpty ? "No checklist" : workspace.checklistProgress)
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                }

                if !workspace.platformFocus.isEmpty {
                    Text(workspace.platformFocus)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                if !workspace.nextChecklistStep.isEmpty {
                    Label(workspace.nextChecklistStep, systemImage: "arrowshape.right.fill")
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(.white)
                }

                if !checklistActionError.isEmpty {
                    Text(checklistActionError)
                        .font(.caption)
                        .foregroundStyle(.red.opacity(0.9))
                } else if !checklistActionMessage.isEmpty {
                    Text(checklistActionMessage)
                        .font(.caption)
                        .foregroundStyle(green.opacity(0.88))
                }

                if !workspace.assets.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("ASSET COVERAGE")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(workspace.assets) { asset in
                            AssetSummaryRow(asset: asset, accent: green)
                            if asset.id != workspace.assets.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }

                if !workspace.checklist.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("CHECKLIST")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(workspace.checklist) { item in
                            ChecklistRow(
                                item: item,
                                accent: green,
                                isActing: checklistActionInFlight == item.id,
                                onToggle: {
                                    Task { await toggleChecklistStep(projectId: workspace.projectId, item: item) }
                                }
                            )
                            if item.id != workspace.checklist.last?.id { Divider().opacity(0.2) }
                        }
                    }
                }
            }
        }
    }

    private func assetStatusColor(_ status: String) -> Color {
        switch status.lowercased() {
        case "ready", "complete": return green
        case "partial": return .orange
        default: return .secondary
        }
    }

    @ViewBuilder
    private func continuitySection(_ continuity: PublishContinuity) -> some View {
        PressSection(title: "Carry Forward", icon: "point.3.connected.trianglepath.dotted", accent: green) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 10) {
                    metricPill("\(continuity.profileFactCount)", "Facts", tint: green)
                    metricPill("\(continuity.pendingReviewPressure)", "Reviews", tint: .orange)
                    metricPill("\(continuity.activePlatforms.count)", "Platforms", tint: .cyan)
                }

                if !continuity.launchFocus.isEmpty || !continuity.briefingStyle.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        if !continuity.launchFocus.isEmpty {
                            Text(continuity.launchFocus)
                                .font(.subheadline.weight(.medium))
                                .foregroundStyle(.white)
                        }
                        if !continuity.briefingStyle.isEmpty {
                            Text("Briefing style: \(continuity.briefingStyle.replacingOccurrences(of: "_", with: " ").capitalized)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                if !continuity.activePlatforms.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("ACTIVE PLATFORMS")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        Text(continuity.activePlatforms.joined(separator: " • "))
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.74))
                    }
                }

                if !continuity.guidanceLines.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("LAUNCH RHYTHM")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(continuity.guidanceLines, id: \.self) { line in
                            Text("• \(line)")
                                .font(.caption)
                                .foregroundStyle(.white.opacity(0.72))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                if !continuity.recentProfileFacts.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("DURABLE PATTERNS")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(continuity.recentProfileFacts) { fact in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(fact.title)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(.white)
                                if !fact.summary.isEmpty {
                                    Text(fact.summary)
                                        .font(.caption)
                                        .foregroundStyle(.white.opacity(0.72))
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                    }
                }

                if !continuity.recentFirstLight.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("RECENT FIRST LIGHT")
                            .font(.system(size: 9, weight: .bold))
                            .tracking(1.0)
                            .foregroundStyle(.secondary)
                        ForEach(continuity.recentFirstLight) { moment in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(moment.label)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                Text(moment.summary)
                                    .font(.caption)
                                    .foregroundStyle(.white.opacity(0.72))
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func supervisoryStrip(_ ov: PublishOverview) -> some View {
        PressSection(title: "Supervisory Strip", icon: "person.2.wave.2.fill", accent: green) {
            HStack(alignment: .top, spacing: 12) {
                supervisorPill(name: "JARVIS", detail: "Launch posture", tint: .cyan)
                supervisorPill(name: "Ghostwritr", detail: "Source authority", tint: green)
                supervisorPill(name: "Herald", detail: ov.pendingReviewsCount > 0 ? "Review pressure" : "Queue clear", tint: .orange)
            }
        }
    }

    // MARK: - Error

    private func errorView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "doc.richtext.fill").font(.system(size: 44)).foregroundStyle(green.opacity(0.4))
            Text("Publishing unavailable").font(.headline).foregroundStyle(.white)
            Text(msg).font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
            Button("Retry") { Task { await load() } }
                .buttonStyle(.borderedProminent).tint(green)
        }
        .padding(24).glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32).frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func load() async {
        isLoading = true; error = nil
        do { overview = try await AppleAPIClient.shared.fetchPublishing() }
        catch { self.error = error.localizedDescription }
        isLoading = false
    }

    private func approveReview(_ reviewId: String) async {
        reviewActionInFlight = reviewId
        do {
            let result = try await AppleAPIClient.shared.approvePublishingReview(reviewId)
            if result.status == "approved" {
                await load()
            } else if result.status == "staged_for_review" {
                self.error = result.boundaryReason ?? "Publishing approval was staged for review."
                await load()
            } else if result.status == "blocked_by_boundary" {
                self.error = result.boundaryReason ?? "Publishing approval was blocked by boundary policy."
                await load()
            }
        } catch {
            self.error = error.localizedDescription
        }
        reviewActionInFlight = nil
    }

    private func requestRevision(_ reviewId: String) async {
        reviewActionInFlight = reviewId
        do {
            let result = try await AppleAPIClient.shared.requestPublishingRevision(reviewId)
            if result.status == "needs_revision" {
                await load()
            } else if result.status == "staged_for_review" {
                self.error = result.boundaryReason ?? "Publishing revision request was staged for review."
                await load()
            } else if result.status == "blocked_by_boundary" {
                self.error = result.boundaryReason ?? "Publishing revision request was blocked by boundary policy."
                await load()
            }
        } catch {
            self.error = error.localizedDescription
        }
        reviewActionInFlight = nil
    }

    private func toggleChecklistStep(projectId: String, item: PublishChecklistItem) async {
        guard !projectId.isEmpty else { return }
        checklistActionInFlight = item.id
        checklistActionMessage = ""
        checklistActionError = ""
        do {
            let result = try await AppleAPIClient.shared.updatePublishingChecklistStep(
                projectId: projectId,
                step: item.step,
                completed: !item.completed
            )
            checklistActionMessage = result.completed
                ? "\(result.label) marked complete. Launch checklist is now \(result.progress)."
                : "\(result.label) reopened. Launch checklist is now \(result.progress)."
            await load()
        } catch {
            checklistActionError = error.localizedDescription
        }
        checklistActionInFlight = nil
    }

    private func daysLabel(for days: Int?) -> String {
        guard let days else { return "—" }
        if days == 0 { return "0d" }
        if days < 0 { return "Live" }
        return "\(days)d"
    }

    private func activeProjectTitle(in ov: PublishOverview) -> String {
        if let title = ov.launchControl?.title, !title.isEmpty {
            return title
        }
        return ov.projects.first?.title ?? "Launch Ops"
    }

    private func activeProjectSubtitle(in ov: PublishOverview) -> String {
        if let nextAction = ov.launchControl?.nextAction, !nextAction.isEmpty {
            return nextAction
        }
        return "Editorial readiness, assembly, and launch continuity remain wired to live publish state."
    }

    private func launchStatusText(in ov: PublishOverview) -> String {
        if let status = ov.launchControl?.status, !status.isEmpty {
            return status.replacingOccurrences(of: "_", with: " ").capitalized
        }
        return "Ready"
    }

    private func packageStatusText(in ov: PublishOverview) -> String {
        if let phase = ov.launchControl?.phase, !phase.isEmpty {
            return phase.replacingOccurrences(of: "_", with: " ").capitalized
        }
        return "Live"
    }

    @ViewBuilder
    private func metricPill(_ value: String, _ label: String, tint: Color) -> some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 16, weight: .bold).monospacedDigit())
                .foregroundStyle(tint)
            Text(label.uppercased())
                .font(.system(size: 8, weight: .bold))
                .tracking(0.8)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(tint.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
    }

    @ViewBuilder
    private func badge(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 9, weight: .bold))
            .foregroundStyle(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.14), in: Capsule())
    }

    private func publishChip(_ title: String, tint: Color) -> some View {
        Text(title)
            .font(.caption2.weight(.semibold))
            .foregroundStyle(tint)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(tint.opacity(0.12), in: Capsule())
    }

    private func storyboardMetric(title: String, value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.system(size: 9, weight: .bold))
                .tracking(1.2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.subheadline.weight(.bold))
                .foregroundStyle(tint)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 16))
    }

    private func supervisorPill(name: String, detail: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(name)
                .font(.caption.weight(.bold))
                .foregroundStyle(tint)
            Text(detail)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.72))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.white.opacity(0.04), in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Press section

private struct PressSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon).font(.system(size: 11, weight: .semibold)).foregroundStyle(accent)
                Text(title.uppercased()).font(.system(size: 10, weight: .bold)).tracking(1.0).foregroundStyle(accent.opacity(0.85))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Project row

private struct ProjectRow: View {
    let project: PublishProject
    let green: Color

    var statusColor: Color {
        switch project.status {
        case "published": return green
        case "ready":     return .cyan
        case "editing":   return .orange
        default:          return .white.opacity(0.4)
        }
    }

    var typeIcon: String {
        switch project.type {
        case "book":   return "book.closed.fill"
        case "course": return "graduationcap.fill"
        default:       return "doc.text.fill"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Image(systemName: typeIcon)
                    .font(.system(size: 16))
                    .foregroundStyle(green.opacity(0.6))
                    .frame(width: 22)

                VStack(alignment: .leading, spacing: 2) {
                    Text(project.title).font(.subheadline).foregroundStyle(.white)
                    HStack(spacing: 4) {
                        Text(project.platform).font(.caption2).foregroundStyle(.secondary)
                        if !project.platform.isEmpty && !project.status.isEmpty {
                            Text("·").font(.caption2).foregroundStyle(.secondary)
                        }
                        if !project.type.isEmpty {
                            Text(project.type.replacingOccurrences(of: "_", with: " ").capitalized)
                                .font(.caption2).foregroundStyle(.secondary)
                        }
                    }
                }
                Spacer()
                Text(project.status.capitalized)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(statusColor)
                    .padding(.horizontal, 7).padding(.vertical, 3)
                    .background(statusColor.opacity(0.12), in: Capsule())
            }
            if !project.description.isEmpty {
                Text(project.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            if !project.notes.isEmpty {
                Text(project.notes)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.7))
                    .lineLimit(2)
            }
            if !project.checklistProgress.isEmpty {
                HStack(spacing: 8) {
                    Text(project.checklistProgress)
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(project.checklistPercent >= 75 ? green : .orange)
                    Text("checklist")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(project.checklistPercent)%")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            }
            if !project.platformFocus.isEmpty {
                Text(project.platformFocus)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Stream row

private struct StreamRow: View {
    let stream: RevenueStream
    let green: Color

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(stream.source).font(.subheadline).foregroundStyle(.white)
                Text(stream.type.replacingOccurrences(of: "_", with: " ").capitalized)
                    .font(.caption2).foregroundStyle(.secondary)
            }
            Spacer()
            Text(stream.monthlyEst.formatted(.currency(code: "USD")))
                .font(.subheadline.bold().monospacedDigit())
                .foregroundStyle(stream.monthlyEst > 0 ? green : .secondary)
            Text("/ mo")
                .font(.caption2).foregroundStyle(.secondary)
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Calendar row

private struct CalendarRow: View {
    let item: CalendarItem

    var statusColor: Color {
        switch item.status {
        case "ready":   return .cyan
        case "draft":   return .orange
        case "outline": return .yellow
        default:        return .white.opacity(0.3)
        }
    }

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title).font(.subheadline).foregroundStyle(.white)
                HStack(spacing: 4) {
                    if !item.contentType.isEmpty {
                        Text(item.contentType.replacingOccurrences(of: "_", with: " ").capitalized)
                            .font(.caption2).foregroundStyle(.secondary)
                    }
                    if !item.platform.isEmpty {
                        Text("·").font(.caption2).foregroundStyle(.secondary)
                        Text(item.platform).font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(item.plannedDate.prefix(10))
                    .font(.caption2.monospacedDigit()).foregroundStyle(.secondary)
                Text(item.status.capitalized)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(statusColor)
            }
        }
        .padding(.vertical, 2)
    }
}

private struct ActionItemRow: View {
    let item: PublishActionItem
    let green: Color

    private var tint: Color {
        switch item.priority.lowercased() {
        case "high": return .orange
        case "medium": return green
        default: return .secondary
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(tint.opacity(0.2))
                .frame(width: 26, height: 26)
                .overlay(
                    Image(systemName: item.kind == "review" ? "checklist" : item.kind == "launch" ? "megaphone.fill" : "calendar")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(tint)
                )
            VStack(alignment: .leading, spacing: 4) {
                Text(item.title).font(.subheadline).foregroundStyle(.white)
                Text(item.detail).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Text(item.priority.uppercased())
                .font(.system(size: 8, weight: .bold))
                .tracking(0.8)
                .foregroundStyle(tint)
        }
        .padding(.vertical, 2)
    }
}

private struct ReviewRow: View {
    let review: PublishReview
    let green: Color
    let isActing: Bool
    let onApprove: () -> Void
    let onRevise: () -> Void

    private var previewText: String {
        let raw = review.contentPreview.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return "Ready for review." }
        if raw.first == "{", let data = raw.data(using: .utf8),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            var parts: [String] = []
            if let words = json["totalWords"] as? Int { parts.append("\(words.formatted()) words") }
            if let chapters = json["chapterCount"] as? Int { parts.append("\(chapters) chapters") }
            if let subtitle = json["subtitle"] as? String, !subtitle.isEmpty { parts.append(subtitle) }
            return parts.isEmpty ? "Structured draft package ready." : parts.joined(separator: " · ")
        }
        return String(raw.prefix(140))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(review.title).font(.subheadline).foregroundStyle(.white)
                    Text(review.stageDisplay.isEmpty ? review.stageKey.replacingOccurrences(of: "_", with: " ").capitalized : review.stageDisplay)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.orange)
                }
                Spacer()
                if review.wordCount > 0 {
                    Text("\(review.wordCount.formatted()) words")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            }
            Text(previewText)
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack {
                Text(review.readySince.prefix(10))
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.secondary)
                Spacer()
                Button(isActing ? "Working…" : "Needs Work") { onRevise() }
                    .buttonStyle(.bordered)
                    .tint(.orange)
                    .disabled(isActing)
                Button(isActing ? "Working…" : "Approve") { onApprove() }
                    .buttonStyle(.borderedProminent)
                    .tint(green)
                    .disabled(isActing)
            }
        }
        .padding(.vertical, 2)
    }
}

private struct AssetSummaryRow: View {
    let asset: PublishAssetSummary
    let accent: Color

    private var statusColor: Color {
        switch asset.status.lowercased() {
        case "ready", "complete": return accent
        case "partial": return .orange
        default: return .secondary
        }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(statusColor.opacity(0.18))
                .frame(width: 26, height: 26)
                .overlay(
                    Image(systemName: asset.status.lowercased() == "ready" || asset.status.lowercased() == "complete" ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(statusColor)
                )
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(asset.title)
                        .font(.subheadline)
                        .foregroundStyle(.white)
                    Spacer()
                    Text("\(asset.itemCount)")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(statusColor)
                }
                Text(asset.detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}

private struct ChecklistRow: View {
    let item: PublishChecklistItem
    let accent: Color
    let isActing: Bool
    let onToggle: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: item.completed ? "checkmark.circle.fill" : "circle")
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(item.completed ? accent : .secondary)
                .padding(.top, 1)
            VStack(alignment: .leading, spacing: 3) {
                Text(item.label)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                HStack(spacing: 6) {
                    Text("Step \(item.order)")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                    if item.completed, !item.completedAt.isEmpty {
                        Text("·")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                        Text(item.completedAt.prefix(10))
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(accent)
                    }
                }
            }
            Spacer()
            Button(isActing ? "Working…" : (item.completed ? "Reopen" : "Complete")) {
                onToggle()
            }
            .buttonStyle(.bordered)
            .tint(item.completed ? .orange : accent)
            .disabled(isActing)
        }
        .padding(.vertical, 2)
    }
}

#Preview { PublishView() }
