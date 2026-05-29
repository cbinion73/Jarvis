import SwiftUI
import JarvisKit

// MARK: - BriefingView  "The Oracle"

struct BriefingView: View {

    @ObservedObject var viewModel: BriefingViewModel
    @StateObject private var nowPlaying = NowPlayingManager.shared
    @StateObject private var speech     = SpeechRecognitionManager.shared
    @State private var status: WatchStatus?
    @State private var showingInbox = false
    @State private var calendarActionMessage = ""
    @State private var calendarActionError = ""
    @State private var reminderActionMessage = ""
    @State private var reminderActionError = ""

    private let gold = Color(red: 1.0, green: 0.82, blue: 0.28)

    var body: some View {
        NavigationStack {
            ZStack {
                // Warm deep-space background
                ZStack {
                    Color.black
                    LinearGradient(
                        colors: [Color(red: 0.06, green: 0.05, blue: 0.01), Color.black],
                        startPoint: .top,
                        endPoint: UnitPoint(x: 0.5, y: 0.55)
                    )
                }
                .ignoresSafeArea()

                Group {
                    if viewModel.isLoading && viewModel.packet == nil {
                        loadingView
                    } else if let packet = viewModel.packet {
                        packetView(packet)
                    } else if let error = viewModel.errorMessage {
                        errorView(error)
                    }
                }
            }
            .navigationTitle("JARVIS")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 8) {
                        Button {
                            speech.startListening { text in
                                Task { await viewModel.sendVoiceCommand(text) }
                            }
                        } label: {
                            Image(systemName: speech.isListening ? "waveform.circle.fill" : "mic.circle")
                                .foregroundStyle(speech.isListening ? .red : gold)
                                .symbolEffect(.variableColor.iterative, isActive: speech.isListening)
                        }
                        .glassEffect(in: Circle())

                        Button { Task { await refreshAll() } } label: {
                            Image(systemName: "arrow.clockwise")
                        }
                        .glassEffect(in: Circle())

                        Button {
                            showingInbox = true
                        } label: {
                            Image(systemName: "bell.badge")
                        }
                        .glassEffect(in: Circle())
                    }
                }
            }
        }
        .task { await loadStatus() }
        .refreshable { await refreshAll() }
        .sheet(isPresented: $showingInbox) {
            NotificationCenterView()
        }
    }

    // MARK: - Loading

    private var loadingView: some View {
        VStack(spacing: 16) {
            Image(systemName: "sun.horizon.fill")
                .font(.system(size: 40))
                .foregroundStyle(gold.opacity(0.4))
                .symbolEffect(.pulse)
            Text("Reaching JARVIS…")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Packet

    @ViewBuilder
    private func packetView(_ packet: BriefingPacket) -> some View {
        ScrollView {
            VStack(spacing: 14) {

                // ── Now Playing ───────────────────────────────────
                if nowPlaying.isPlaying, let title = nowPlaying.title {
                    NowPlayingCard(title: title, artist: nowPlaying.artist ?? "", artwork: nowPlaying.artwork)
                }

                if let status {
                    statusCard(status)
                }

                if !packet.commandItems.isEmpty {
                    commandStack(packet.commandItems)
                }

                if let appState = viewModel.appState {
                    alertBanner(
                        appState: appState,
                        focusState: viewModel.focusState,
                        controlPlane: viewModel.controlPlaneState
                    )
                    householdPostureCards(
                        appState: appState,
                        focusState: viewModel.focusState,
                        controlPlane: viewModel.controlPlaneState
                    )
                    appStateCards(appState)
                }

                // ── Greeting + mode chip ─────────────────────────
                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .top) {
                        Text(packet.greeting)
                            .font(.title3.bold())
                            .foregroundStyle(.white)
                        Spacer()
                        // Mode chip
                        Text(packet.mode.uppercased())
                            .font(.system(size: 9, weight: .black))
                            .tracking(1.2)
                            .foregroundStyle(.black)
                            .padding(.horizontal, 9)
                            .padding(.vertical, 4)
                            .background(gold, in: Capsule())
                    }
                    Text(formatDate(packet.generatedAt))
                        .font(.caption2)
                        .foregroundStyle(gold.opacity(0.6))
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                // ── Intelligence ──────────────────────────────────
                if !packet.briefingItems.isEmpty {
                    OracleSection(title: "Intelligence", icon: "brain.head.profile", accent: gold) {
                        ForEach(packet.briefingItems) { item in
                            IntelRow(item: item, gold: gold)
                            if item.id != packet.briefingItems.last?.id {
                                Divider().opacity(0.2)
                            }
                        }
                    }
                }

                if packet.briefingItems.isEmpty
                    && packet.needsItems.isEmpty
                    && packet.workingItems.isEmpty
                    && packet.driftItems.isEmpty {
                    emptyTruthState
                }

                // ── Needs You ─────────────────────────────────────
                if !packet.needsItems.isEmpty {
                    OracleSection(title: "Needs You", icon: "exclamationmark.circle.fill", accent: .red) {
                        ForEach(packet.needsItems) { item in
                            NeedsSummaryRow(item: item) {
                                await viewModel.approve(requestId: item.id)
                            }
                        }
                    }
                }

                // ── Agents Working ────────────────────────────────
                if !packet.workingItems.isEmpty {
                    OracleSection(title: "Agents Working", icon: "gearshape.2.fill", accent: .cyan) {
                        ForEach(packet.workingItems) { item in
                            AgentRow(item: item)
                        }
                    }
                }

                // ── Drift ─────────────────────────────────────────
                if !packet.driftItems.isEmpty {
                    OracleSection(title: "Drift Signals", icon: "waveform.path", accent: Color(red: 1.0, green: 0.75, blue: 0.2)) {
                        ForEach(packet.driftItems) { item in
                            DriftRow(item: item)
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }

    // MARK: - Error

    private var emptyTruthState: some View {
        VStack(spacing: 10) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 30))
                .foregroundStyle(gold.opacity(0.8))
            Text("No live briefing items")
                .font(.headline)
                .foregroundStyle(.white)
            Text("JARVIS is connected, but there is no verified briefing data to show yet.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(18)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 44))
                .foregroundStyle(gold)
            Text("Couldn't reach JARVIS")
                .font(.headline)
                .foregroundStyle(.white)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Try Again") { Task { await refreshAll() } }
                .buttonStyle(.borderedProminent)
                .tint(gold)
        }
        .padding(24)
        .glassEffect(in: RoundedRectangle(cornerRadius: 20))
        .padding(.horizontal, 32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func formatDate(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso.prefix(10).description }
        return d.formatted(date: .abbreviated, time: .shortened)
    }

    private func statusCard(_ status: WatchStatus) -> some View {
        HStack(spacing: 10) {
            snapshotMetric(title: "Mode", value: status.mode.capitalized)
            snapshotMetric(title: "Needs", value: "\(status.needsCount)")
            snapshotMetric(title: "Drift", value: status.drift ? "Yes" : "No")
        }
        .overlay(alignment: .bottomLeading) {
            Text(status.weather.isEmpty ? "Live JARVIS status" : status.weather)
                .font(.caption2)
                .foregroundStyle(gold.opacity(0.7))
                .padding(.horizontal, 14)
                .padding(.bottom, 10)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.top, 8)
        .padding(.horizontal, 14)
        .padding(.bottom, 28)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }

    private func commandStack(_ items: [CommandItem]) -> some View {
        OracleSection(title: "Command Stack", icon: "command.square.fill", accent: gold) {
            VStack(spacing: 10) {
                ForEach(items) { item in
                    HStack(alignment: .top, spacing: 0) {
                        if item.priority == "high" {
                            RoundedRectangle(cornerRadius: 2)
                                .fill(gold)
                                .frame(width: 3)
                                .padding(.trailing, 10)
                        } else {
                            Color.clear
                                .frame(width: 13)
                        }
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(alignment: .firstTextBaseline) {
                                Text(item.title)
                                    .font(.subheadline.bold())
                                    .foregroundStyle(.white)
                                Spacer(minLength: 8)
                                Text(item.kind.uppercased())
                                    .font(.system(size: 9, weight: .black))
                                    .tracking(1)
                                    .foregroundStyle(.black)
                                    .padding(.horizontal, 7)
                                    .padding(.vertical, 3)
                                    .background((item.priority == "high" ? gold : Color.white.opacity(0.5)), in: Capsule())
                            }
                            Text(item.detail)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(3)
                        }
                    }
                    .padding(.leading, item.priority == "high" ? 0 : 0)
                    if item.id != items.last?.id {
                        Divider().opacity(0.2)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func appStateCards(_ appState: AppStateOverview) -> some View {
        if appState.notifications.pendingCount > 0 || appState.calendar.count > 0 || appState.reminders.count > 0 {
            OracleSection(title: "Morning Grid", icon: "square.grid.2x2.fill", accent: gold) {
                HStack(spacing: 10) {
                    snapshotMetric(title: "Alerts", value: "\(appState.notifications.pendingCount)")
                    snapshotMetric(title: "Events", value: "\(appState.calendar.count)")
                    snapshotMetric(title: "Reminders", value: "\(appState.reminders.count)")
                }
            }
        }

        if !appState.notifications.recent.isEmpty {
            OracleSection(title: "Notifications", icon: "bell.badge.fill", accent: .yellow) {
                VStack(alignment: .leading, spacing: 10) {
                    Button {
                        showingInbox = true
                    } label: {
                        Label("Open Notification Center", systemImage: "tray.full")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(gold)
                    }
                    .buttonStyle(.plain)

                    ForEach(Array(appState.notifications.recent.prefix(3))) { notification in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(alignment: .firstTextBaseline) {
                                Text(notification.title.isEmpty ? "JARVIS Alert" : notification.title)
                                    .font(.subheadline.bold())
                                    .foregroundStyle(.white)
                                Spacer()
                                if !notification.category.isEmpty {
                                    Text(notification.category.uppercased())
                                        .font(.system(size: 9, weight: .black))
                                        .tracking(1)
                                        .foregroundStyle(.black)
                                        .padding(.horizontal, 7)
                                        .padding(.vertical, 3)
                                        .background(gold.opacity(0.9), in: Capsule())
                                }
                            }
                            if !notification.body.isEmpty {
                                Text(notification.body)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(3)
                            }
                            if let decisionReason = notification.decisionReason, !decisionReason.isEmpty {
                                Text(decisionReason)
                                    .font(.caption2)
                                    .foregroundStyle(gold.opacity(0.78))
                            }
                            if !notification.createdAt.isEmpty {
                                Text(formatTimestamp(notification.createdAt))
                                    .font(.caption2)
                                    .foregroundStyle(gold.opacity(0.7))
                            }
                        }
                        if notification.id != appState.notifications.recent.prefix(3).last?.id {
                            Divider().opacity(0.2)
                        }
                    }
                }
            }
        }

        if !appState.calendar.nextItems.isEmpty {
            OracleSection(title: "Calendar", icon: "calendar", accent: .cyan) {
                VStack(alignment: .leading, spacing: 10) {
                    if !calendarActionError.isEmpty {
                        Text(calendarActionError)
                            .font(.caption2)
                            .foregroundStyle(.red.opacity(0.9))
                    } else if !calendarActionMessage.isEmpty {
                        Text(calendarActionMessage)
                            .font(.caption2)
                            .foregroundStyle(gold.opacity(0.82))
                    }
                    ForEach(Array(appState.calendar.nextItems.prefix(3))) { nextEvent in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(nextEvent.title)
                                .font(.subheadline.bold())
                                .foregroundStyle(.white)
                            Text(nextEvent.start.isEmpty ? "Today" : formatTimestamp(nextEvent.start))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            if !nextEvent.location.isEmpty {
                                Text(nextEvent.location)
                                    .font(.caption2)
                                    .foregroundStyle(gold.opacity(0.7))
                            }
                            HStack(spacing: 10) {
                                Button("Stage Prep") {
                                    Task { await stageCalendarPrep(nextEvent) }
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(.cyan)

                                if !nextEvent.location.isEmpty {
                                    Button("Maps") {
                                        openCalendarLocation(nextEvent)
                                    }
                                    .buttonStyle(.bordered)
                                    .tint(.white.opacity(0.85))
                                }
                            }
                            .font(.caption.weight(.semibold))
                        }
                        if nextEvent.id != appState.calendar.nextItems.prefix(3).last?.id {
                            Divider().opacity(0.2)
                        }
                    }
                }
            }
        }

        if !appState.reminders.topItems.isEmpty {
            OracleSection(title: "Reminders", icon: "checklist", accent: .orange) {
                VStack(alignment: .leading, spacing: 10) {
                    if !reminderActionError.isEmpty {
                        Text(reminderActionError)
                            .font(.caption2)
                            .foregroundStyle(.red.opacity(0.9))
                    } else if !reminderActionMessage.isEmpty {
                        Text(reminderActionMessage)
                            .font(.caption2)
                            .foregroundStyle(gold.opacity(0.82))
                    }
                    ForEach(Array(appState.reminders.topItems.prefix(3))) { reminder in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(reminder.title)
                                .font(.subheadline.bold())
                                .foregroundStyle(.white)
                            Text(reminder.due.isEmpty ? reminder.list : formatTimestamp(reminder.due))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            if !reminder.list.isEmpty && !reminder.due.isEmpty {
                                Text(reminder.list)
                                    .font(.caption2)
                                    .foregroundStyle(gold.opacity(0.7))
                            }
                            HStack(spacing: 10) {
                                Button("Complete") {
                                    Task { await completeReminder(reminder) }
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(.orange)

                                Button("Snooze 1h") {
                                    Task { await snoozeReminder(reminder) }
                                }
                                .buttonStyle(.bordered)
                                .tint(.white.opacity(0.85))
                            }
                            .font(.caption.weight(.semibold))
                        }
                        if reminder.id != appState.reminders.topItems.prefix(3).last?.id {
                            Divider().opacity(0.2)
                        }
                    }
                }
            }
        }

        if appState.focus.focusActive || !appState.nowPlaying.title.isEmpty || !appState.visionScan.textPreview.isEmpty || !appState.soundAlert.label.isEmpty {
            OracleSection(title: "Ambient Signals", icon: "bell.and.waves.left.and.right.fill", accent: .purple) {
                VStack(alignment: .leading, spacing: 8) {
                    if appState.focus.focusActive {
                        signalRow(
                            title: "Focus",
                            body: appState.focus.postureLabel?.isEmpty == false
                                ? (appState.focus.postureLabel ?? "Active on the phone")
                                : "Active on the phone",
                            footnote: formatTimestamp(appState.focus.updatedAt),
                            icon: "moon.fill"
                        )
                        if let postureReason = appState.focus.postureReason, !postureReason.isEmpty {
                            Text(postureReason)
                                .font(.caption2)
                                .foregroundStyle(gold.opacity(0.75))
                        }
                    }
                    if !appState.nowPlaying.title.isEmpty {
                        signalRow(
                            title: "Now Playing",
                            body: [appState.nowPlaying.title, appState.nowPlaying.artist]
                                .filter { !$0.isEmpty }
                                .joined(separator: " — "),
                            footnote: formatTimestamp(appState.nowPlaying.updatedAt),
                            icon: "music.note"
                        )
                    }
                    if !appState.soundAlert.label.isEmpty {
                        signalRow(
                            title: "Sound Alert",
                            body: appState.soundAlert.label,
                            footnote: signalFootnote(source: appState.soundAlert.source, timestamp: appState.soundAlert.receivedAt),
                            icon: "waveform"
                        )
                    }
                    if !appState.visionScan.textPreview.isEmpty {
                        signalRow(
                            title: appState.visionScan.context.isEmpty ? "Vision Scan" : appState.visionScan.context,
                            body: appState.visionScan.textPreview,
                            footnote: signalFootnote(source: appState.visionScan.source, timestamp: appState.visionScan.receivedAt),
                            icon: "viewfinder"
                        )
                    }
                }
            }
        }
    }


    @ViewBuilder
    private func alertBanner(
        appState: AppStateOverview,
        focusState: FocusStateOverview?,
        controlPlane: ControlPlaneOverview?
    ) -> some View {
        if let notification = rankedAlert(from: appState.notifications.recent) {
            OracleSection(title: "What Matters Now", icon: "exclamationmark.bubble.fill", accent: severityColor(notification.severity)) {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(notification.title.isEmpty ? "JARVIS Alert" : notification.title)
                            .font(.headline)
                            .foregroundStyle(.white)
                        Spacer(minLength: 8)
                        pill(notification.severity.uppercased(), color: severityColor(notification.severity))
                    }
                    if !notification.detail.isEmpty {
                        Text(notification.detail)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else if !notification.body.isEmpty {
                        Text(notification.body)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if !notification.whyNow.isEmpty {
                        Text(notification.whyNow)
                            .font(.caption2)
                            .foregroundStyle(gold.opacity(0.82))
                    }
                    HStack(spacing: 8) {
                        if !notification.category.isEmpty {
                            pill(notification.category.capitalized, color: gold.opacity(0.92))
                        }
                        if !notification.deliveryMode.isEmpty {
                            pill(readableDeliveryMode(notification.deliveryMode), color: .blue.opacity(0.82))
                        }
                        if let label = notification.postureSnapshot?.label, !label.isEmpty {
                            pill(label, color: .white.opacity(0.28))
                        }
                    }
                    Button {
                        showingInbox = true
                    } label: {
                        Label("Open Notification Center", systemImage: "tray.full")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(gold)
                    }
                    .buttonStyle(.plain)
                }
            }
        } else if let focusState, focusState.interruptionPosture.quietHours || focusState.interruptionPosture.focusActive {
            OracleSection(title: "What Matters Now", icon: "moon.stars.fill", accent: .indigo) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(focusState.interruptionPosture.label)
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text(focusState.interruptionPosture.reason)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    HStack(spacing: 8) {
                        pill(readableDeliveryMode(focusState.interruptionPosture.recommendedDelivery), color: .blue.opacity(0.82))
                        if focusState.interruptionPosture.quietHours {
                            pill("Quiet Hours", color: .white.opacity(0.28))
                        }
                        if focusState.interruptionPosture.focusActive {
                            pill("Focus Active", color: .white.opacity(0.28))
                        }
                    }
                }
            }
        } else if let freshnessItem = freshestConcern(from: controlPlane) {
            OracleSection(title: "What Matters Now", icon: "antenna.radiowaves.left.and.right.slash", accent: .orange) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(freshnessItem.label)
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text(freshnessItem.detail)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if !freshnessItem.updatedAt.isEmpty {
                        Text("Last updated \(formatTimestamp(freshnessItem.updatedAt))")
                            .font(.caption2)
                            .foregroundStyle(gold.opacity(0.78))
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func householdPostureCards(
        appState: AppStateOverview,
        focusState: FocusStateOverview?,
        controlPlane: ControlPlaneOverview?
    ) -> some View {
        let presenceSummary = presenceSummaryText(appState.presence)
        let freshnessItems = Array((controlPlane?.freshness ?? []).filter { !$0.synced || $0.status.lowercased() != "fresh" }.prefix(2))
        if !presenceSummary.isEmpty || focusState != nil || !freshnessItems.isEmpty {
            OracleSection(title: "Household Posture", icon: "person.3.sequence.fill", accent: .mint) {
                VStack(alignment: .leading, spacing: 10) {
                    if !presenceSummary.isEmpty {
                        signalRow(
                            title: "Presence",
                            body: presenceSummary,
                            footnote: presenceFootnote(appState.presence),
                            icon: "house.fill"
                        )
                    }
                    if let focusState {
                        signalRow(
                            title: "Interruption Posture",
                            body: focusState.summary.label,
                            footnote: focusState.summary.detail,
                            icon: "moon.zzz.fill"
                        )
                    }
                    ForEach(freshnessItems) { item in
                        signalRow(
                            title: item.label,
                            body: item.detail,
                            footnote: item.updatedAt.isEmpty ? item.status.capitalized : formatTimestamp(item.updatedAt),
                            icon: item.synced ? "clock.badge.exclamationmark" : "arrow.triangle.2.circlepath"
                        )
                    }
                }
            }
        }
    }

    private func completeReminder(_ reminder: AppStateReminderItem) async {
        reminderActionError = ""
        do {
            if try await AppleAPIClient.shared.completeReminder(reminder.id) {
                reminderActionMessage = "Completed \(reminder.title)"
                await refreshMorningState()
            }
        } catch {
            reminderActionError = error.localizedDescription
        }
    }

    private func stageCalendarPrep(_ event: AppStateCalendarItem) async {
        calendarActionError = ""
        do {
            if try await AppleAPIClient.shared.stageCalendarPrep(
                title: event.title,
                start: event.start,
                location: event.location
            ) {
                calendarActionMessage = "Staged prep for \(event.title)"
                await refreshMorningState()
            }
        } catch {
            calendarActionError = error.localizedDescription
        }
    }

    private func openCalendarLocation(_ event: AppStateCalendarItem) {
        let destination = event.location.isEmpty ? event.title : event.location
        let query = destination.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? destination
        guard let url = URL(string: "http://maps.apple.com/?daddr=\(query)&dirflg=d") else { return }
        UIApplication.shared.open(url)
    }

    private func snoozeReminder(_ reminder: AppStateReminderItem) async {
        reminderActionError = ""
        do {
            if try await AppleAPIClient.shared.snoozeReminder(reminder.id, minutes: 60) {
                reminderActionMessage = "Snoozed \(reminder.title) for 1 hour"
                await refreshMorningState()
            }
        } catch {
            reminderActionError = error.localizedDescription
        }
    }

    private func refreshMorningState() async {
        await viewModel.refreshAppState()
        reminderActionError = viewModel.errorMessage ?? ""
    }

    private func signalRow(title: String, body: String, footnote: String, icon: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .font(.caption.bold())
                .foregroundStyle(gold)
                .frame(width: 16, height: 16)
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.caption.bold())
                    .foregroundStyle(.white)
                Text(body)
                    .font(.caption)
                    .foregroundStyle(.white)
                    .lineLimit(3)
                if !footnote.isEmpty {
                    Text(footnote)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func snapshotMetric(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.headline.bold())
                .foregroundStyle(.white)
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func refreshAll() async {
        await viewModel.refresh()
        await loadStatus()
    }

    private func formatTimestamp(_ raw: String) -> String {
        guard !raw.isEmpty else { return "" }
        let iso = ISO8601DateFormatter()
        if let date = iso.date(from: raw) {
            return date.formatted(date: .abbreviated, time: .shortened)
        }
        return raw
    }

    private func signalFootnote(source: String, timestamp: String) -> String {
        let time = formatTimestamp(timestamp)
        if source.isEmpty { return time }
        if time.isEmpty { return source }
        return "\(source) · \(time)"
    }

    private func rankedAlert(from notifications: [NotificationCenterItem]) -> NotificationCenterItem? {
        notifications
            .filter { item in
                let status = item.status.lowercased()
                return status == "pending" || status == "seen" || status == "active"
            }
            .sorted { lhs, rhs in
                let leftRank = severityRank(lhs.severity)
                let rightRank = severityRank(rhs.severity)
                if leftRank != rightRank {
                    return leftRank > rightRank
                }
                return lhs.createdAt > rhs.createdAt
            }
            .first
    }

    private func severityRank(_ severity: String) -> Int {
        switch severity.lowercased() {
        case "critical": return 4
        case "high": return 3
        case "medium": return 2
        case "low": return 1
        default: return 0
        }
    }

    private func severityColor(_ severity: String) -> Color {
        switch severity.lowercased() {
        case "critical", "high":
            return .red
        case "medium":
            return .orange
        case "low":
            return gold.opacity(0.9)
        default:
            return .white.opacity(0.35)
        }
    }

    private func readableDeliveryMode(_ mode: String) -> String {
        switch mode.lowercased() {
        case "push_now":
            return "Push Now"
        case "quiet_store":
            return "Quiet Store"
        case "hold_for_brief":
            return "Hold for Brief"
        default:
            return mode.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    private func freshestConcern(from controlPlane: ControlPlaneOverview?) -> ControlPlaneFreshnessItem? {
        controlPlane?.freshness.first(where: { !$0.synced || $0.status.lowercased() != "fresh" })
    }

    private func presenceSummaryText(_ presence: AppStatePresence) -> String {
        let members = presence.presentMembers.joined(separator: ", ")
        switch (members.isEmpty, presence.lightsOnCount) {
        case (false, 0):
            return "\(members) \(presence.presentMembers.count == 1 ? "is" : "are") home."
        case (false, _):
            return "\(members) \(presence.presentMembers.count == 1 ? "is" : "are") home with \(presence.lightsOnCount) lights on."
        case (true, let lights) where lights > 0:
            return "\(lights) lights are still on with no presence confirmed."
        default:
            return ""
        }
    }

    private func presenceFootnote(_ presence: AppStatePresence) -> String {
        if presence.alertCount > 0 {
            return "\(presence.alertCount) household alerts need attention"
        }
        if presence.presentMembers.isEmpty {
            return "No live presence members are confirmed right now."
        }
        return "Household presence is live."
    }

    private func loadStatus() async {
        status = try? await AppleAPIClient.shared.fetchStatus()
    }
}

// MARK: - Oracle section container

private struct OracleSection<Content: View>: View {
    let title: String
    let icon: String
    let accent: Color
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(accent)
                Text(title.uppercased())
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.0)
                    .foregroundStyle(accent.opacity(0.85))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

private func pill(_ text: String, color: Color) -> some View {
    Text(text)
        .font(.system(size: 9, weight: .black))
        .tracking(0.9)
        .foregroundStyle(.white)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(color, in: Capsule())
}

// MARK: - Row types

private struct IntelRow: View {
    let item: BriefingItem
    let gold: Color

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            // Priority accent strip
            if item.priority == "high" {
                RoundedRectangle(cornerRadius: 2)
                    .fill(gold)
                    .frame(width: 3)
                    .padding(.trailing, 10)
                    .padding(.vertical, 2)
            }

            VStack(alignment: .leading, spacing: 3) {
                Text(item.text)
                    .font(.subheadline)
                    .foregroundStyle(.white)
                if let sub = item.sub {
                    Text(sub).font(.caption).foregroundStyle(.secondary)
                }
                Text(item.agent)
                    .font(.caption2)
                    .foregroundStyle(gold.opacity(0.6))
            }
            .padding(.leading, item.priority == "high" ? 0 : 13)
        }
        .padding(.vertical, 2)
    }
}

private struct NeedsSummaryRow: View {
    let item: NeedsItem
    let onApprove: @Sendable () async -> Void

    var riskColor: Color {
        switch item.risk { case "high": .red; case "medium": .orange; default: .yellow }
    }

    @State private var isApproving = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Circle().fill(riskColor).frame(width: 7, height: 7)
                VStack(alignment: .leading, spacing: 1) {
                    Text(item.text).font(.subheadline).foregroundStyle(.white)
                    Text(item.agent).font(.caption2).foregroundStyle(.secondary)
                }
                Spacer()
                if let exp = item.expiresIn {
                    Text(exp).font(.caption2).foregroundStyle(.secondary)
                }
            }

            Button {
                Task {
                    isApproving = true
                    await onApprove()
                    isApproving = false
                }
            } label: {
                HStack(spacing: 6) {
                    if isApproving {
                        ProgressView().tint(.green)
                    } else {
                        Image(systemName: "checkmark.shield.fill")
                    }
                    Text(isApproving ? "Approving…" : "Approve")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.green)
            .disabled(isApproving)
        }
    }
}

private struct AgentRow: View {
    let item: WorkingItem

    var body: some View {
        HStack(spacing: 10) {
            // Animated blip
            Circle()
                .fill(Color.cyan)
                .frame(width: 6, height: 6)
                .symbolEffect(.pulse)
            VStack(alignment: .leading, spacing: 1) {
                Text(item.agent).font(.caption2).foregroundStyle(.cyan)
                Text(item.action).font(.subheadline).foregroundStyle(.white)
            }
        }
    }
}

private struct DriftRow: View {
    let item: DriftItem

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: item.severity == "significant" ? "exclamationmark.triangle.fill" : "circle.dotted")
                .foregroundStyle(Color(red: 1.0, green: 0.75, blue: 0.2))
                .font(.caption)
                .padding(.top, 2)
            Text(item.text).font(.subheadline).foregroundStyle(.white)
        }
    }
}

// MARK: - Now Playing card

private struct NowPlayingCard: View {
    let title:   String
    let artist:  String
    let artwork: UIImage?

    var body: some View {
        HStack(spacing: 12) {
            Group {
                if let img = artwork {
                    Image(uiImage: img).resizable().aspectRatio(contentMode: .fill)
                } else {
                    Image(systemName: "music.note")
                        .font(.title2).foregroundStyle(.purple)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .frame(width: 50, height: 50)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 3) {
                Label("Now Playing", systemImage: "waveform")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.purple.opacity(0.8))
                Text(title)
                    .font(.subheadline.bold())
                    .foregroundStyle(.white).lineLimit(1)
                Text(artist)
                    .font(.caption).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer()

            // Equalizer bars
            HStack(alignment: .bottom, spacing: 3) {
                ForEach([14.0, 20.0, 11.0, 17.0], id: \.self) { h in
                    RoundedRectangle(cornerRadius: 1.5)
                        .fill(Color.purple.opacity(0.75))
                        .frame(width: 3, height: h)
                }
            }
        }
        .padding(12)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

#Preview {
    BriefingView(viewModel: BriefingViewModel())
}
