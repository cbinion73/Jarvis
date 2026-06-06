import SwiftUI
import JarvisKit

// MARK: - Tab definition

enum JARVISTab: Int, CaseIterable, Identifiable {
    case brief, needs, health, weather, home, catalyst, chronicle,
         faith, publish, huddle, navigate, forge, voice, systems

    var id: Int { rawValue }

    var label: String {
        switch self {
        case .brief:     return "Brief"
        case .needs:     return "Needs"
        case .health:    return "Health"
        case .weather:   return "Weather"
        case .home:      return "Home"
        case .catalyst:  return "Catalyst"
        case .chronicle: return "Chronicle"
        case .faith:     return "Faith"
        case .publish:   return "Publish"
        case .huddle:    return "Huddle"
        case .navigate:  return "Navigate"
        case .forge:     return "Forge"
        case .voice:     return "Voice"
        case .systems:   return "Systems"
        }
    }

    var icon: String {
        switch self {
        case .brief:     return "sun.horizon.fill"
        case .needs:     return "exclamationmark.circle.fill"
        case .health:    return "heart.fill"
        case .weather:   return "cloud.sun.fill"
        case .home:      return "house.fill"
        case .catalyst:  return "gearshape.2.fill"
        case .chronicle: return "book.fill"
        case .faith:     return "sparkles"
        case .publish:   return "doc.richtext.fill"
        case .huddle:    return "person.3.fill"
        case .navigate:  return "map.fill"
        case .forge:     return "cube.fill"
        case .voice:     return "waveform.circle.fill"
        case .systems:   return "gearshape.fill"
        }
    }

    var accent: Color {
        switch self {
        case .brief:     return Color(red: 1.0,  green: 0.82, blue: 0.28)
        case .needs:     return .red
        case .health:    return Color(red: 0.2,  green: 0.9,  blue: 0.5)
        case .weather:   return Color(red: 0.4,  green: 0.75, blue: 1.0)
        case .home:      return .orange
        case .catalyst:  return Color(red: 0.25, green: 0.55, blue: 1.0)
        case .chronicle: return Color(red: 0.9,  green: 0.65, blue: 0.25)
        case .faith:     return Color(red: 1.0,  green: 0.85, blue: 0.35)
        case .publish:   return Color(red: 0.15, green: 0.85, blue: 0.45)
        case .huddle:    return Color(red: 0.15, green: 0.75, blue: 0.75)
        case .navigate:  return Color(red: 0.4,  green: 0.55, blue: 0.75)
        case .forge:     return Color(red: 1.0,  green: 0.55, blue: 0.15)
        case .voice:     return Color(red: 0.72, green: 0.45, blue: 1.0)
        case .systems:   return Color(red: 0.55, green: 0.65, blue: 0.78)
        }
    }
}

// MARK: - Root

struct RootTabView: View {

    @State  private var selectedTab: JARVISTab

    @StateObject private var briefingVM = BriefingViewModel()
    @StateObject private var needsVM    = NeedsViewModel()
    @StateObject private var healthVM   = HealthViewModel()
    @ObservedObject private var voiceVM = VoiceViewModel.shared
    @ObservedObject private var voiceLaunchCenter = VoiceConversationLaunchCenter.shared
    @ObservedObject private var weatherMgr = WeatherManager.shared
    @ObservedObject private var weatherLoc = WeatherLocationProvider.shared

    init() {
        _selectedTab = State(initialValue: Self.initialSelectedTab())
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            ambientBackground

            TabView(selection: $selectedTab) {
                BriefingView(viewModel: briefingVM).tag(JARVISTab.brief)
                NeedsView(viewModel: needsVM).tag(JARVISTab.needs)
                HealthView(viewModel: healthVM).tag(JARVISTab.health)
                WeatherView().tag(JARVISTab.weather)
                HomeView().tag(JARVISTab.home)
                CatalystView().tag(JARVISTab.catalyst)
                ChronicleView().tag(JARVISTab.chronicle)
                FaithView().tag(JARVISTab.faith)
                PublishView().tag(JARVISTab.publish)
                HuddleView().tag(JARVISTab.huddle)
                NavigateView().tag(JARVISTab.navigate)
                ForgeView().tag(JARVISTab.forge)
                VoiceView().tag(JARVISTab.voice)
                SettingsView().tag(JARVISTab.systems)
            }
            .toolbar(.hidden, for: .tabBar)
            .safeAreaInset(edge: .top, spacing: 0) {
                commandHeader
            }
            .safeAreaInset(edge: .bottom, spacing: 0) {
                Color.clear.frame(height: 112)
            }

            JARVISTabBar(selected: $selectedTab, needsCount: needsVM.items.count)
                .padding(.horizontal, 12)
                .padding(.bottom, 8)
        }
        .ignoresSafeArea(edges: .bottom)
        .task {
            await briefingVM.load()
            await needsVM.load()
            await healthVM.load()
            handlePendingVoiceLaunchIfNeeded()
        }
        .onChange(of: weatherMgr.current) { _, cur in
            guard let cur else { return }
            WatchSessionManager.shared.sendWeather(cur, forecast: weatherMgr.forecast)
        }
        .onChange(of: voiceLaunchCenter.pendingLaunch) { _, launch in
            guard launch != nil else { return }
            handlePendingVoiceLaunchIfNeeded()
        }
    }

    private var ambientBackground: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 0.03, green: 0.07, blue: 0.12),
                    Color(red: 0.02, green: 0.05, blue: 0.09),
                    .black,
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            Circle()
                .fill(Color(red: 0.38, green: 0.86, blue: 0.86).opacity(0.16))
                .frame(width: 320, height: 320)
                .blur(radius: 24)
                .offset(x: -110, y: -280)

            Circle()
                .fill(Color(red: 0.45, green: 0.58, blue: 1.0).opacity(0.18))
                .frame(width: 360, height: 360)
                .blur(radius: 28)
                .offset(x: 120, y: -260)

            Circle()
                .fill(Color(red: 0.42, green: 0.85, blue: 0.62).opacity(0.08))
                .frame(width: 340, height: 340)
                .blur(radius: 36)
                .offset(x: 0, y: 300)
        }
        .ignoresSafeArea()
    }

    private var commandHeader: some View {
        VStack(spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("JARVIS")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .tracking(2.4)
                        .foregroundStyle(Color(red: 0.42, green: 0.86, blue: 0.86))

                    Text(selectedTab.label)
                        .font(.system(size: 32, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)

                    Text(selectedTabSummary)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(.white.opacity(0.72))
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: 0)

                VStack(alignment: .trailing, spacing: 8) {
                    statusBadge(
                        title: voiceVM.isConversationActive ? "Voice Live" : "Voice Ready",
                        detail: voiceVM.isConversationActive ? voiceVM.conversationStatus : "Hands-free control available",
                        color: voiceVM.isConversationActive
                            ? Color(red: 0.43, green: 0.86, blue: 0.79)
                            : Color(red: 0.53, green: 0.72, blue: 1.0)
                    )
                }
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    statusPill(
                        title: "Needs",
                        detail: needsVM.items.isEmpty ? "Clear" : "\(needsVM.items.count) active",
                        color: needsVM.items.isEmpty
                            ? Color(red: 0.43, green: 0.86, blue: 0.79)
                            : Color(red: 1.0, green: 0.45, blue: 0.45)
                    )

                    if let current = weatherMgr.current {
                        statusPill(
                            title: weatherMgr.locationName.isEmpty ? "Weather" : weatherMgr.locationName,
                            detail: "\(current.tempString) · \(current.condition)",
                            color: Color(red: 0.47, green: 0.77, blue: 1.0)
                        )
                    }

                    if healthVM.summary != nil {
                        statusPill(
                            title: "Health",
                            detail: "Helen Cho + health agents live",
                            color: Color(red: 0.42, green: 0.9, blue: 0.58)
                        )
                    }

                    statusPill(
                        title: "Mode",
                        detail: selectedTab.label,
                        color: selectedTab.accent
                    )
                }
                .padding(.horizontal, 2)
            }
        }
        .padding(.horizontal, 14)
        .padding(.top, 12)
        .padding(.bottom, 10)
        .background(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(.ultraThinMaterial)
                .overlay {
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .strokeBorder(.white.opacity(0.08), lineWidth: 1)
                }
                .shadow(color: .black.opacity(0.24), radius: 22, y: 12)
        )
        .padding(.horizontal, 12)
        .padding(.top, 8)
        .background(Color.clear)
    }

    private var selectedTabSummary: String {
        switch selectedTab {
        case .brief:
            return "Morning brief, priorities, and live continuity."
        case .needs:
            return "Operator demand, approvals, and urgent follow-through."
        case .health:
            return "Helen Cho and the health stack stay within reach."
        case .weather:
            return "Forecast, risk, and family weather planning."
        case .home:
            return "Home operations and routines with real state."
        case .catalyst:
            return "Execution systems, catalysts, and momentum."
        case .chronicle:
            return "Chronicle memory, notes, and review surfaces."
        case .faith:
            return "Faith rhythms, reflection, and grounded intention."
        case .publish:
            return "Publishing workflow with seeded and live output state."
        case .huddle:
            return "Team, family, and relationship coordination."
        case .navigate:
            return "Places, routes, and live navigation continuity."
        case .forge:
            return "Forge, workshops, and build surfaces."
        case .voice:
            return "Hands-free conversation with JARVIS."
        case .systems:
            return "Settings, controls, and system truth."
        }
    }

    private func statusBadge(title: String, detail: String, color: Color) -> some View {
        VStack(alignment: .trailing, spacing: 3) {
            Text(title)
                .font(.system(size: 11, weight: .semibold, design: .rounded))
                .foregroundStyle(color)
            Text(detail)
                .font(.system(size: 11, weight: .medium, design: .rounded))
                .foregroundStyle(.white.opacity(0.76))
                .multilineTextAlignment(.trailing)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.white.opacity(0.05))
        )
    }

    private func statusPill(title: String, detail: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(color)
            Text(detail)
                .font(.system(size: 12, weight: .medium, design: .rounded))
                .foregroundStyle(.white.opacity(0.82))
                .lineLimit(1)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color.white.opacity(0.05))
                .overlay {
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .strokeBorder(color.opacity(0.16), lineWidth: 1)
                }
        )
    }

    private func handlePendingVoiceLaunchIfNeeded() {
        if Self.hasExplicitTabOverride(), selectedTab != .voice {
            _ = voiceLaunchCenter.consumePendingLaunch()
            return
        }
        guard let launch = voiceLaunchCenter.consumePendingLaunch() else { return }
        selectedTab = .voice
        Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(250))
            voiceVM.activateConversation(launch: launch)
        }
    }

    private static func initialSelectedTab() -> JARVISTab {
        let args = ProcessInfo.processInfo.arguments
        if let index = args.firstIndex(of: "--jarvis-tab"), args.indices.contains(index + 1) {
            let requested = args[index + 1].trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            if let match = JARVISTab.allCases.first(where: { $0.label.lowercased() == requested }) {
                return match
            }
        }

        if let requested = ProcessInfo.processInfo.environment["JARVIS_INITIAL_TAB"]?
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased(),
           let match = JARVISTab.allCases.first(where: { $0.label.lowercased() == requested }) {
            return match
        }

        return .brief
    }

    private static func hasExplicitTabOverride() -> Bool {
        let args = ProcessInfo.processInfo.arguments
        if let index = args.firstIndex(of: "--jarvis-tab"), args.indices.contains(index + 1) {
            return !args[index + 1].trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }

        if let requested = ProcessInfo.processInfo.environment["JARVIS_INITIAL_TAB"]?
            .trimmingCharacters(in: .whitespacesAndNewlines),
           !requested.isEmpty {
            return true
        }

        return false
    }
}

// MARK: - Scrollable tab bar
// 14 tabs — scroll horizontally. Every tab shows icon + label.
// Active tab is full-brightness accent; inactive dims to 30%.
// ScrollViewReader keeps the active pill in view automatically.

private let kTabWidth: CGFloat  = 68
private let kIconSize: CGFloat  = 26

struct JARVISTabBar: View {

    @Binding var selected: JARVISTab
    let needsCount: Int

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(JARVISTab.allCases) { tab in
                        tabItem(tab, proxy: proxy)
                    }
                }
                .padding(.horizontal, 10)
            }
            .padding(.top, 10)
            .padding(.bottom, bottomPad + 4)
            .background(
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color.black.opacity(0.72),
                                Color(red: 0.04, green: 0.09, blue: 0.15).opacity(0.9),
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .overlay {
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .strokeBorder(.white.opacity(0.08), lineWidth: 1)
                    }
                    .shadow(color: .black.opacity(0.28), radius: 22, y: 10)
            )
            .onChange(of: selected) { _, tab in
                withAnimation(.spring(response: 0.32, dampingFraction: 0.8)) {
                    proxy.scrollTo(tab.id, anchor: .center)
                }
            }
        }
    }

    @ViewBuilder
    private func tabItem(_ tab: JARVISTab, proxy: ScrollViewProxy) -> some View {
        let isActive = selected == tab
        let accent   = tab.accent

        Button {
            withAnimation(.spring(response: 0.26, dampingFraction: 0.74)) {
                selected = tab
            }
        } label: {
            VStack(spacing: 6) {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: tab.icon)
                        .font(.system(size: isActive ? kIconSize - 1 : kIconSize - 3, weight: .semibold))
                        .foregroundStyle(isActive ? Color.black.opacity(0.86) : .white.opacity(0.46))
                        .frame(width: 34, height: 34)
                        .background(
                            Circle()
                                .fill(isActive ? accent : Color.white.opacity(0.05))
                        )
                        .scaleEffect(isActive ? 1.0 : 0.92)
                        .animation(.spring(response: 0.26, dampingFraction: 0.7), value: isActive)

                    if tab == .needs && needsCount > 0 {
                        Text("\(min(needsCount, 9))")
                            .font(.system(size: 7, weight: .black))
                            .foregroundStyle(.white)
                            .padding(2.5)
                            .background(.red, in: Circle())
                            .offset(x: 7, y: -4)
                    }
                }

                Text(tab.label)
                    .font(.system(size: 10, weight: isActive ? .bold : .semibold, design: .rounded))
                    .foregroundStyle(isActive ? .white : .white.opacity(0.42))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)

                Capsule()
                    .fill(isActive ? accent : .clear)
                    .frame(width: isActive ? 18 : 0, height: 3)
                    .animation(.spring(response: 0.26), value: isActive)
            }
            .frame(width: kTabWidth + (isActive ? 4 : 0))
            .frame(minHeight: 58)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(isActive ? accent.opacity(0.18) : Color.clear)
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .id(tab.id)
    }

    private var bottomPad: CGFloat {
        let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene
        let inset = scene?.windows.first?.safeAreaInsets.bottom ?? 0
        return max(inset, 6)
    }
}

#Preview {
    RootTabView()
}
