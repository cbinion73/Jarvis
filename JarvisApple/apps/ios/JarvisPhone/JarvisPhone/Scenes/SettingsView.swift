import SwiftUI
import JarvisKit

struct SettingsView: View {

    @State private var selectedEnvironment: JARVISEnvironmentOption = .local
    @State private var customURL = ""
    @State private var showingURLField = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {

                        // ── Server ────────────────────────────────
                        GlassSettingsSection(title: "Server", icon: "server.rack") {

                            // Environment picker row
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Environment")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                Picker("", selection: $selectedEnvironment) {
                                    ForEach(JARVISEnvironmentOption.allCases) { option in
                                        Text(option.displayName).tag(option)
                                    }
                                }
                                .pickerStyle(.segmented)
                                .onChange(of: selectedEnvironment) { _, newValue in
                                    applyEnvironment(newValue)
                                    showingURLField = (newValue == .custom)
                                }
                            }

                            if showingURLField {
                                Divider().opacity(0.3)
                                TextField("https://…", text: $customURL)
                                    .keyboardType(.URL)
                                    .autocorrectionDisabled()
                                    .textInputAutocapitalization(.never)
                                    .foregroundStyle(.white)
                                    .tint(.cyan)
                                    .onSubmit { applyCustomURL() }
                            }

                            Divider().opacity(0.3)

                            HStack {
                                Text("Base URL")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                                Text(JARVISEnvironment.baseURL.absoluteString)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.cyan.opacity(0.8))
                                    .lineLimit(1)
                                    .truncationMode(.middle)
                            }
                        }

                        // ── App Info ──────────────────────────────
                        GlassSettingsSection(title: "App", icon: "info.circle.fill") {
                            SettingsRow(label: "Version") {
                                Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "—")
                                    .foregroundStyle(.secondary)
                            }
                            Divider().opacity(0.3)
                            SettingsRow(label: "Build") {
                                Text(Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "—")
                                    .foregroundStyle(.secondary)
                            }
                        }

                        // ── Links ─────────────────────────────────
                        GlassSettingsSection(title: "Links", icon: "link") {
                            Link(destination: URL(string: JARVISEnvironment.baseURL.absoluteString)!) {
                                HStack {
                                    Label("Open JARVIS Web", systemImage: "safari")
                                        .foregroundStyle(.cyan)
                                    Spacer()
                                    Image(systemName: "arrow.up.right.square")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }

                        // ── About ─────────────────────────────────
                        VStack(spacing: 4) {
                            Text("JARVIS")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.white.opacity(0.5))
                            Text("Just A Rather Very Intelligent System")
                                .font(.caption2)
                                .foregroundStyle(.white.opacity(0.3))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.top, 8)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .onAppear { syncPickerFromCurrent() }
        }
    }

    // MARK: - Helpers

    private func syncPickerFromCurrent() {
        let url = JARVISEnvironment.baseURL.absoluteString
        if url.contains("teambinion") {
            selectedEnvironment = .production
        } else if url.contains("localhost") {
            selectedEnvironment = .local
        } else if url.contains("tailscale") || url.contains("100.") {
            selectedEnvironment = .tailscale
        } else {
            selectedEnvironment = .custom
            customURL = url
            showingURLField = true
        }
    }

    private func applyEnvironment(_ option: JARVISEnvironmentOption) {
        switch option {
        case .production:
            JARVISEnvironment.current = .production
        case .local:
            JARVISEnvironment.current = .local
        case .tailscale:
            JARVISEnvironment.current = .tailscale
        case .custom:
            break  // applied on URL submit
        }
    }

    private func applyCustomURL() {
        guard let url = URL(string: customURL), !customURL.isEmpty else { return }
        JARVISEnvironment.current = .custom(url)
    }
}

// MARK: - Glass section

private struct GlassSettingsSection<Content: View>: View {
    let title: String
    let icon: String
    var accentColor: Color = .white
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label(title, systemImage: icon)
                .font(.caption.weight(.semibold))
                .foregroundStyle(accentColor.opacity(0.7))
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .glassEffect(in: RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Settings row

private struct SettingsRow<Trailing: View>: View {
    let label: String
    @ViewBuilder let trailing: Trailing

    var body: some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.white)
            Spacer()
            trailing
                .font(.subheadline)
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Environment option enum (UI only)

enum JARVISEnvironmentOption: String, CaseIterable, Identifiable {
    case production
    case local
    case tailscale
    case custom

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .production: return "Production"
        case .local:      return "Local"
        case .tailscale:  return "Tailscale"
        case .custom:     return "Custom"
        }
    }
}

#Preview {
    SettingsView()
}
