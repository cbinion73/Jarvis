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
            .safeAreaInset(edge: .bottom, spacing: 0) {
                Color.clear.frame(height: 80)
            }

            JARVISTabBar(selected: $selectedTab, needsCount: needsVM.items.count)
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

    private func handlePendingVoiceLaunchIfNeeded() {
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
                HStack(spacing: 0) {
                    ForEach(JARVISTab.allCases) { tab in
                        tabItem(tab, proxy: proxy)
                    }
                }
                .padding(.horizontal, 6)
            }
            .padding(.top, 8)
            .padding(.bottom, bottomPad)
            .background(.ultraThinMaterial)
            .overlay(alignment: .top) {
                Rectangle().fill(.white.opacity(0.07)).frame(height: 0.5)
            }
            // Keep active tab visible whenever selection changes
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
            VStack(spacing: 4) {
                // Icon with optional badge
                ZStack(alignment: .topTrailing) {
                    Image(systemName: tab.icon)
                        .font(.system(size: isActive ? kIconSize : kIconSize - 2, weight: .semibold))
                        .foregroundStyle(isActive ? accent : .white.opacity(0.30))
                        .frame(width: 30, height: 30)
                        .scaleEffect(isActive ? 1.0 : 0.88)
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

                // Label — always visible
                Text(tab.label)
                    .font(.system(size: 9, weight: isActive ? .bold : .medium))
                    .foregroundStyle(isActive ? accent : .white.opacity(0.28))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)

                // Active pip
                Capsule()
                    .fill(isActive ? accent : .clear)
                    .frame(width: isActive ? 16 : 0, height: 2.5)
                    .animation(.spring(response: 0.26), value: isActive)
            }
            .frame(width: kTabWidth)
            .frame(minHeight: 52)
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
