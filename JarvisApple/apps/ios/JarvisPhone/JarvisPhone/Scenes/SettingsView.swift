import SwiftUI
import JarvisKit

// MARK: - SettingsView  "Systems"

struct SettingsView: View {

    @State private var selectedEnvironment: JARVISEnvironmentOption = .local
    @State private var customURL     = ""
    @State private var showingURLField = false
    @State private var serverOK      = false

    private let steel = Color(red: 0.55, green: 0.65, blue: 0.78)

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {

                        // ── Status banner ──────────────────────────
                        HStack(spacing: 14) {
                            ZStack {
                                Circle().fill(serverOK ? Color.green.opacity(0.15) : Color.red.opacity(0.1))
                                    .frame(width: 44, height: 44)
                                Image(systemName: serverOK ? "server.rack" : "exclamationmark.triangle.fill")
                                    .font(.system(size: 18))
                                    .foregroundStyle(serverOK ? .green : .red)
                            }
                            VStack(alignment: .leading, spacing: 2) {
                                Text(serverOK ? "SYSTEMS NOMINAL" : "CONNECTION ERROR")
                                    .font(.system(size: 10, weight: .black))
                                    .tracking(1.2)
                                    .foregroundStyle(serverOK ? .green : .red)
                                Text(JARVISEnvironment.baseURL.host ?? "—")
                                    .font(.caption2.monospaced())
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                            Spacer()
                            // Ping button
                            Button("Ping") { Task { await pingServer() } }
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(steel)
                                .glassEffect(in: Capsule())
                        }
                        .padding(14)
                        .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                        // ── Server environment ──────────────────────
                        SystemsSection(title: "Server", icon: "wifi", accent: steel) {

                            Text("Environment")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)
                            Picker("", selection: $selectedEnvironment) {
                                ForEach(JARVISEnvironmentOption.allCases) { option in
                                    Text(option.displayName).tag(option)
                                }
                            }
                            .pickerStyle(.segmented)
                            .tint(steel)
                            .onChange(of: selectedEnvironment) { _, newValue in
                                applyEnvironment(newValue)
                                showingURLField = (newValue == .custom)
                            }

                            if showingURLField {
                                Divider().opacity(0.3)
                                TextField("https://…", text: $customURL)
                                    .keyboardType(.URL)
                                    .autocorrectionDisabled()
                                    .textInputAutocapitalization(.never)
                                    .foregroundStyle(.white)
                                    .tint(steel)
                                    .onSubmit { applyCustomURL() }
                            }

                            Divider().opacity(0.3)

                            HStack {
                                Text("Base URL")
                                    .font(.caption).foregroundStyle(.secondary)
                                Spacer()
                                Text(JARVISEnvironment.baseURL.absoluteString)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(steel.opacity(0.9))
                                    .lineLimit(1)
                                    .truncationMode(.middle)
                            }
                        }

                        // ── App info ────────────────────────────────
                        SystemsSection(title: "Build", icon: "info.circle.fill", accent: steel) {
                            SysRow(label: "Version") {
                                versionChip(
                                    Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—",
                                    build: Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—"
                                )
                            }
                        }

                        // ── Links ────────────────────────────────────
                        SystemsSection(title: "Links", icon: "link", accent: steel) {
                            Link(destination: URL(string: JARVISEnvironment.baseURL.absoluteString)!) {
                                HStack {
                                    Label("Open JARVIS Web", systemImage: "safari")
                                        .foregroundStyle(steel)
                                    Spacer()
                                    Image(systemName: "arrow.up.right.square")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }

                        // ── About watermark ──────────────────────────
                        VStack(spacing: 3) {
                            Text("JARVIS")
                                .font(.system(size: 11, weight: .black))
                                .tracking(2)
                                .foregroundStyle(.white.opacity(0.3))
                            Text("JUST A RATHER VERY INTELLIGENT SYSTEM")
                                .font(.system(size: 8, weight: .medium))
                                .tracking(1)
                                .foregroundStyle(.white.opacity(0.18))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, 10)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Systems")
            .navigationBarTitleDisplayMode(.large)
            .onAppear { syncPickerFromCurrent() }
        }
    }

    // MARK: - Version chip

    private func versionChip(_ version: String, build: String) -> some View {
        Text("v\(version) · build \(build)")
            .font(.system(size: 10, weight: .semibold).monospaced())
            .foregroundStyle(steel)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(steel.opacity(0.1), in: Capsule())
    }

    // MARK: - Ping

    private func pingServer() async {
        do {
            let _: WatchStatus = try await AppleAPIClient.shared.fetchStatus()
            serverOK = true
        } catch {
            serverOK = false
        }
    }

    // MARK: - Helpers

    private func syncPickerFromCurrent() {
        let url = JARVISEnvironment.baseURL.absoluteString
        if url.contains("teambinion")        { selectedEnvironment = .production }
        else if url.contains("localhost")    { selectedEnvironment = .local }
        else if url.contains("tailscale") || url.contains("100.") { selectedEnvironment = .tailscale }
        else { selectedEnvironment = .custom; customURL = url; showingURLField = true }
    }

    private func applyEnvironment(_ option: JARVISEnvironmentOption) {
        switch option {
        case .production: JARVISEnvironment.current = .production
        case .local:      JARVISEnvironment.current = .local
        case .tailscale:  JARVISEnvironment.current = .tailscale
        case .custom:     break
        }
    }

    private func applyCustomURL() {
        guard let url = URL(string: customURL), !customURL.isEmpty else { return }
        JARVISEnvironment.current = .custom(url)
    }
}

// MARK: - Section

private struct SystemsSection<Content: View>: View {
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
                    .foregroundStyle(accent.opacity(0.8))
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Row

private struct SysRow<Trailing: View>: View {
    let label: String
    @ViewBuilder let trailing: Trailing

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline).foregroundStyle(.white)
            Spacer()
            trailing.font(.subheadline)
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Environment option enum

enum JARVISEnvironmentOption: String, CaseIterable, Identifiable {
    case production, local, tailscale, custom

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .production: return "Prod"
        case .local:      return "Local"
        case .tailscale:  return "Tailscale"
        case .custom:     return "Custom"
        }
    }
}

#Preview { SettingsView() }
