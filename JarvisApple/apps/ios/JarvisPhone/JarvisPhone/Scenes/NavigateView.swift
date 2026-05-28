import SwiftUI
import MapKit

// MARK: - NavigateView  "Navigate"
// Maria Hill · Travel Steward  (coming soon)

struct NavigateView: View {

    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.3317, longitude: -122.0307),
        span: MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05)
    )

    private let slate = Color(red: 0.4, green: 0.55, blue: 0.75)

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {

                        // ── Map preview ───────────────────────────
                        Map(coordinateRegion: $region)
                            .frame(height: 200)
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                            .overlay(
                                RoundedRectangle(cornerRadius: 16)
                                    .stroke(slate.opacity(0.3), lineWidth: 1)
                            )

                        // ── Coming soon card ─────────────────────
                        VStack(alignment: .leading, spacing: 14) {
                            HStack(spacing: 10) {
                                ZStack {
                                    Circle().fill(slate.opacity(0.12)).frame(width: 44, height: 44)
                                    Image(systemName: "map.fill")
                                        .font(.system(size: 18)).foregroundStyle(slate)
                                }
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Navigate")
                                        .font(.title3.bold()).foregroundStyle(.white)
                                    Text("Maria Hill · Travel Steward")
                                        .font(.caption2).foregroundStyle(slate.opacity(0.7))
                                }
                            }

                            Divider().opacity(0.2)

                            Text("Full travel intelligence is coming soon. Maria Hill will surface:")
                                .font(.subheadline).foregroundStyle(.white.opacity(0.7))

                            VStack(alignment: .leading, spacing: 10) {
                                ComingSoonRow(icon: "airplane.departure",    text: "Trip planning and itineraries",    color: slate)
                                ComingSoonRow(icon: "mappin.and.ellipse",    text: "Home and frequent locations",      color: slate)
                                ComingSoonRow(icon: "car.fill",              text: "Commute and traffic intelligence", color: slate)
                                ComingSoonRow(icon: "calendar.badge.clock",  text: "Travel time for upcoming events",  color: slate)
                                ComingSoonRow(icon: "cloud.bolt.rain.fill",  text: "Destination weather pre-brief",    color: slate)
                            }
                        }
                        .padding(16)
                        .glassEffect(in: RoundedRectangle(cornerRadius: 16))

                        // ── Open Maps quick action ────────────────
                        Button {
                            if let url = URL(string: "maps://") {
                                UIApplication.shared.open(url)
                            }
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: "map.fill").foregroundStyle(slate)
                                Text("Open Apple Maps")
                                    .font(.subheadline.weight(.semibold)).foregroundStyle(.white)
                                Spacer()
                                Image(systemName: "arrow.up.right.square")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            .padding(14)
                            .glassEffect(in: RoundedRectangle(cornerRadius: 14))
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(.horizontal, 16).padding(.vertical, 12)
                }
            }
            .navigationTitle("Navigate")
            .navigationBarTitleDisplayMode(.large)
        }
    }
}

// MARK: - Coming soon row

private struct ComingSoonRow: View {
    let icon: String
    let text: String
    let color: Color

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 14)).foregroundStyle(color.opacity(0.7))
                .frame(width: 22)
            Text(text)
                .font(.subheadline).foregroundStyle(.white.opacity(0.75))
        }
    }
}

#Preview { NavigateView() }
