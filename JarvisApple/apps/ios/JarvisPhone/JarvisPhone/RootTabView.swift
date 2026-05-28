import SwiftUI
import JarvisKit

// MARK: - Tab definition

enum JARVISTab: Int, CaseIterable, Identifiable {
    case brief, needs, health, weather, home, catalyst, chronicle, faith, publish, huddle, navigate, voice, systems

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
        case .voice:     return "waveform.circle.fill"
        case .systems:   return "gearshape.fill"
        }
    }

    var accent: Color {
        switch self {
        case .brief:     return Color(red: 1.0, green: 0.82, blue: 0.28)
        case .needs:     return .red
        case .health:    return Color(red: 0.2, green: 0.9, blue: 0.5)
        case .weather:   return Color(red: 0.4, green: 0.75, blue: 1.0)
        case .home:      return .orange
        case .catalyst:  return Color(red: 0.25, green: 0.55, blue: 1.0)
        case .chronicle: return Color(red: 0.9, green: 0.65, blue: 0.25)
        case .faith:     return Color(red: 1.0, green: 0.85, blue: 0.35)
        case .publish:   return Color(red: 0.15, green: 0.85, blue: 0.45)
        case .huddle:    return Color(red: 0.15, green: 0.75, blue: 0.75)
        case .navigate:  return Color(red: 0.4, green: 0.55, blue: 0.75)
        case .voice:     return Color(red: 0.72, green: 0.45, blue: 1.0)
        case .systems:   return Color(red: 0.55, green: 0.65, blue: 0.78)
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
                VoiceView().tag(JARVISTab.voice)
                SettingsView().tag(JARVISTab.systems)
            }
            .toolbar(.hidden, for: .tabBar)
            .safeAreaInset(edge: .bottom, spacing: 0) {
                Color.clear.frame(height: 76)
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
// 13 tabs — icons only for inactive, icon+label for active.
// Swipe left/right on the bar to advance.

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
        .padding(.top, 8)
        .padding(.bottom, bottomPad)
        .background(.ultraThinMaterial)
        .overlay(alignment: .top) {
            Rectangle().fill(.white.opacity(0.07)).frame(height: 0.5)
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
            withAnimation(.spring(response: 0.26, dampingFraction: 0.74)) {
                selected = tab
            }
        } label: {
            VStack(spacing: 1) {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: tab.icon)
                        .font(.system(size: isActive ? 18 : 16, weight: .medium))
                        .foregroundStyle(isActive ? accent : .white.opacity(0.35))
                        .frame(width: 22, height: 22)
                        .animation(.spring(response: 0.26), value: isActive)

                    if tab == .needs && needsCount > 0 {
                        Text("\(min(needsCount, 9))")
                            .font(.system(size: 7, weight: .black))
                            .foregroundStyle(.white)
                            .padding(2.5)
                            .background(.red, in: Circle())
                            .offset(x: 5, y: -4)
                    }
                }

                // Label: only active tab shows it
                if isActive {
                    Text(tab.label)
                        .font(.system(size: 8.5, weight: .semibold))
                        .foregroundStyle(accent)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .transition(.opacity.combined(with: .scale(0.8)))
                }

                // Active pip
                Capsule()
                    .fill(isActive ? accent : .clear)
                    .frame(width: isActive ? 14 : 0, height: 2)
                    .animation(.spring(response: 0.26), value: isActive)
            }
            .frame(maxWidth: .infinity)
            .frame(minHeight: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .animation(.spring(response: 0.26, dampingFraction: 0.74), value: isActive)
    }

    private var bottomPad: CGFloat {
        let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene
        let inset = scene?.windows.first?.safeAreaInsets.bottom ?? 0
        return max(inset, 6)
    }

    private func advance(by delta: Int) {
        let tabs = JARVISTab.allCases
        guard let idx = tabs.firstIndex(where: { $0 == selected }) else { return }
        let next = max(0, min(tabs.count - 1, idx + delta))
        withAnimation(.spring(response: 0.26, dampingFraction: 0.74)) {
            selected = tabs[next]
        }
    }
}

#Preview {
    RootTabView()
}
