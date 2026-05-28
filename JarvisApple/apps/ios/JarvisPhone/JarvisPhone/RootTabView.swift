import SwiftUI
import JarvisKit

// MARK: - Tab definition

enum JARVISTab: Int, CaseIterable, Identifiable {
    case brief, needs, health, weather, home, voice, systems

    var id: Int { rawValue }

    var label: String {
        switch self {
        case .brief:   return "Brief"
        case .needs:   return "Needs"
        case .health:  return "Health"
        case .weather: return "Weather"
        case .home:    return "Home"
        case .voice:   return "Voice"
        case .systems: return "Systems"
        }
    }

    var icon: String {
        switch self {
        case .brief:   return "sun.horizon.fill"
        case .needs:   return "exclamationmark.circle.fill"
        case .health:  return "heart.fill"
        case .weather: return "cloud.sun.fill"
        case .home:    return "house.fill"
        case .voice:   return "waveform.circle.fill"
        case .systems: return "gearshape.fill"
        }
    }

    var accent: Color {
        switch self {
        case .brief:   return Color(red: 1.0, green: 0.82, blue: 0.28)
        case .needs:   return .red
        case .health:  return Color(red: 0.2, green: 0.9, blue: 0.5)
        case .weather: return Color(red: 0.4, green: 0.75, blue: 1.0)
        case .home:    return .orange
        case .voice:   return Color(red: 0.72, green: 0.45, blue: 1.0)
        case .systems: return Color(red: 0.55, green: 0.65, blue: 0.78)
        }
    }
}

// MARK: - Root

struct RootTabView: View {

    @State  private var selectedTab: JARVISTab = .brief

    @StateObject private var briefingVM = BriefingViewModel()
    @StateObject private var needsVM    = NeedsViewModel()
    @StateObject private var healthVM   = HealthViewModel()
    @StateObject private var weatherMgr = WeatherManager.shared
    @StateObject private var weatherLoc = WeatherLocationProvider.shared

    var body: some View {
        ZStack(alignment: .bottom) {
            TabView(selection: $selectedTab) {
                BriefingView(viewModel: briefingVM)
                    .tag(JARVISTab.brief)
                NeedsView(viewModel: needsVM)
                    .tag(JARVISTab.needs)
                HealthView(viewModel: healthVM)
                    .tag(JARVISTab.health)
                WeatherView()
                    .tag(JARVISTab.weather)
                HomeView()
                    .tag(JARVISTab.home)
                VoiceView()
                    .tag(JARVISTab.voice)
                SettingsView()
                    .tag(JARVISTab.systems)
            }
            .toolbar(.hidden, for: .tabBar)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                Color.clear.frame(height: 82)
            }

            JARVISTabBar(selected: $selectedTab, needsCount: needsVM.items.count)
        }
        .ignoresSafeArea(edges: .bottom)
        .task {
            await briefingVM.load()
            await needsVM.load()
            await healthVM.load()
        }
        .onChange(of: weatherMgr.current) { _, cur in
            guard let cur else { return }
            WatchSessionManager.shared.sendWeather(cur, forecast: weatherMgr.forecast)
        }
    }
}

// MARK: - Custom tab bar

struct JARVISTabBar: View {

    @Binding var selected: JARVISTab
    let needsCount: Int

    var body: some View {
        HStack(spacing: 0) {
            ForEach(JARVISTab.allCases) { tab in
                tabItem(tab)
            }
        }
        .padding(.horizontal, 2)
        .padding(.top, 10)
        .padding(.bottom, bottomPad)
        .background(.ultraThinMaterial)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(.white.opacity(0.08))
                .frame(height: 0.5)
        }
        .gesture(
            DragGesture(minimumDistance: 40, coordinateSpace: .local)
                .onEnded { value in
                    guard abs(value.translation.height) < abs(value.translation.width) else { return }
                    if value.translation.width < -50 { advance(by: 1) }
                    else if value.translation.width >  50 { advance(by: -1) }
                }
        )
    }

    @ViewBuilder
    private func tabItem(_ tab: JARVISTab) -> some View {
        let isActive = selected == tab
        let accent   = tab.accent

        Button {
            withAnimation(.spring(response: 0.28, dampingFraction: 0.72)) {
                selected = tab
            }
        } label: {
            VStack(spacing: 2) {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: tab.icon)
                        .font(.system(size: 20, weight: .medium))
                        .foregroundStyle(isActive ? accent : .white.opacity(0.4))
                        .frame(width: 28, height: 26)

                    if tab == .needs && needsCount > 0 {
                        Text("\(min(needsCount, 99))")
                            .font(.system(size: 8, weight: .black))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 3.5)
                            .padding(.vertical, 1.5)
                            .background(.red, in: Capsule())
                            .offset(x: 6, y: -4)
                    }
                }

                Text(tab.label)
                    .font(.system(size: 9, weight: isActive ? .semibold : .regular))
                    .foregroundStyle(isActive ? accent : .white.opacity(0.4))

                Capsule()
                    .fill(isActive ? accent : .clear)
                    .frame(width: isActive ? 18 : 0, height: 2)
                    .animation(.spring(response: 0.28, dampingFraction: 0.72), value: selected)
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private var bottomPad: CGFloat {
        let scenes = UIApplication.shared.connectedScenes
        let windowScene = scenes.first as? UIWindowScene
        let bottom = windowScene?.windows.first?.safeAreaInsets.bottom ?? 0
        return max(bottom, 8)
    }

    private func advance(by delta: Int) {
        let tabs = JARVISTab.allCases
        guard let idx = tabs.firstIndex(where: { $0 == selected }) else { return }
        let next = max(0, min(tabs.count - 1, idx + delta))
        withAnimation(.spring(response: 0.28, dampingFraction: 0.72)) {
            selected = tabs[next]
        }
    }
}

#Preview {
    RootTabView()
}
