import Foundation
import HealthKit
import JarvisKit
import JarvisKitHealth

// MARK: - HealthSyncManager

/// Full HealthKit mirror for JARVIS.
///
/// Syncs every readable HealthKit type to the JARVIS server using
/// `HKAnchoredObjectQuery` so only NEW samples are pushed after the first run.
/// Background delivery ensures the app pushes data even when not open.
///
/// Call `requestPermissionsAndSync()` once at launch.
@MainActor
final class HealthSyncManager: ObservableObject {

    static let shared = HealthSyncManager()

    @Published var lastSyncDate: Date?
    @Published var isAuthorized = false
    @Published var isSyncing = false
    @Published var syncError: String?
    @Published var lastSyncedCount = 0

    private let bridge = HealthKitBridge()
    private let client = AppleAPIClient.shared

    private init() {}

    // MARK: - Public API

    func requestPermissionsAndSync() async {
        guard HealthKitBridge.isAvailable else { return }

        do {
            try await bridge.store.requestAuthorization(
                toShare: [],
                read: Self.allReadTypes
            )
            isAuthorized = true
            await registerBackgroundDelivery()
            await syncAll()
        } catch {
            syncError = error.localizedDescription
        }
    }

    func syncAll() async {
        guard HealthKitBridge.isAvailable, isAuthorized, !isSyncing else { return }
        isSyncing = true
        syncError = nil
        var totalLogged = 0

        // Quantity types — use anchored queries
        for (identifier, unit, typeName) in Self.quantityTypes {
            let count = await syncQuantityType(identifier, unit: unit, typeName: typeName)
            totalLogged += count
        }

        // Category types
        for (identifier, typeName, encoder) in Self.categoryTypes {
            let count = await syncCategoryType(identifier, typeName: typeName, valueEncoder: encoder)
            totalLogged += count
        }

        // Workouts
        let workoutCount = await syncWorkouts()
        totalLogged += workoutCount

        if totalLogged > 0 {
            lastSyncDate = Date()
            lastSyncedCount = totalLogged
            print("[JARVIS Health] Synced \(totalLogged) new samples.")
        } else {
            lastSyncDate = Date()
            print("[JARVIS Health] No new samples since last sync.")
        }

        isSyncing = false
    }

    // MARK: - Background delivery

    private func registerBackgroundDelivery() async {
        for (identifier, _, _) in Self.quantityTypes {
            let type = HKQuantityType(identifier)
            bridge.store.enableBackgroundDelivery(for: type, frequency: .hourly) { _, _ in }
        }
    }

    // MARK: - Anchored quantity sync

    private func syncQuantityType(
        _ identifier: HKQuantityTypeIdentifier,
        unit: HKUnit,
        typeName: String
    ) async -> Int {
        let type = HKQuantityType(identifier)
        let anchorKey = "jarvis.health.anchor.\(typeName)"
        let anchor = loadAnchor(key: anchorKey)

        return await withCheckedContinuation { cont in
            let query = HKAnchoredObjectQuery(
                type: type,
                predicate: Self.thirtyDaysPredicate,
                anchor: anchor,
                limit: HKObjectQueryNoLimit
            ) { [weak self] _, samples, _, newAnchor, error in
                guard let self else { cont.resume(returning: 0); return }

                if let error {
                    print("[JARVIS Health] \(typeName): \(error.localizedDescription)")
                    cont.resume(returning: 0)
                    return
                }

                let healthSamples: [HealthSample] = (samples as? [HKQuantitySample] ?? []).map {
                    HealthSample(
                        type: typeName,
                        value: $0.quantity.doubleValue(for: unit),
                        date: ISO8601DateFormatter().string(from: $0.startDate),
                        source: $0.sourceRevision.source.name
                    )
                }

                if healthSamples.isEmpty {
                    if let newAnchor { Task { @MainActor in self.saveAnchor(newAnchor, key: anchorKey) } }
                    cont.resume(returning: 0)
                    return
                }

                Task { @MainActor [weak self] in
                    guard let self else { return }
                    do {
                        let logged = try await self.client.logHealthSamples(healthSamples)
                        if let newAnchor { self.saveAnchor(newAnchor, key: anchorKey) }
                        cont.resume(returning: logged)
                    } catch {
                        print("[JARVIS Health] Push \(typeName) failed: \(error.localizedDescription)")
                        cont.resume(returning: 0)
                    }
                }
            }
            bridge.store.execute(query)
        }
    }

    // MARK: - Anchored category sync

    private func syncCategoryType(
        _ identifier: HKCategoryTypeIdentifier,
        typeName: String,
        valueEncoder: @Sendable @escaping (HKCategorySample) -> Double?
    ) async -> Int {
        let type = HKCategoryType(identifier)
        let anchorKey = "jarvis.health.anchor.\(typeName)"
        let anchor = loadAnchor(key: anchorKey)

        return await withCheckedContinuation { cont in
            let query = HKAnchoredObjectQuery(
                type: type,
                predicate: Self.thirtyDaysPredicate,
                anchor: anchor,
                limit: HKObjectQueryNoLimit
            ) { [weak self] _, samples, _, newAnchor, error in
                guard let self else { cont.resume(returning: 0); return }

                if let error {
                    print("[JARVIS Health] \(typeName): \(error.localizedDescription)")
                    cont.resume(returning: 0)
                    return
                }

                let healthSamples: [HealthSample] = (samples as? [HKCategorySample] ?? []).compactMap { s in
                    guard let value = valueEncoder(s) else { return nil }
                    return HealthSample(
                        type: typeName,
                        value: value,
                        date: ISO8601DateFormatter().string(from: s.startDate),
                        source: s.sourceRevision.source.name
                    )
                }

                if healthSamples.isEmpty {
                    if let newAnchor { Task { @MainActor in self.saveAnchor(newAnchor, key: anchorKey) } }
                    cont.resume(returning: 0)
                    return
                }

                Task { @MainActor [weak self] in
                    guard let self else { return }
                    do {
                        let logged = try await self.client.logHealthSamples(healthSamples)
                        if let newAnchor { self.saveAnchor(newAnchor, key: anchorKey) }
                        cont.resume(returning: logged)
                    } catch {
                        print("[JARVIS Health] Push \(typeName) failed: \(error.localizedDescription)")
                        cont.resume(returning: 0)
                    }
                }
            }
            bridge.store.execute(query)
        }
    }

    // MARK: - Workout sync

    private func syncWorkouts() async -> Int {
        let anchorKey = "jarvis.health.anchor.workouts"
        let anchor = loadAnchor(key: anchorKey)

        return await withCheckedContinuation { cont in
            let query = HKAnchoredObjectQuery(
                type: HKObjectType.workoutType(),
                predicate: Self.thirtyDaysPredicate,
                anchor: anchor,
                limit: HKObjectQueryNoLimit
            ) { [weak self] _, samples, _, newAnchor, error in
                guard let self else { cont.resume(returning: 0); return }

                if let error {
                    print("[JARVIS Health] workouts: \(error.localizedDescription)")
                    cont.resume(returning: 0)
                    return
                }

                let workoutSamples: [HealthSample] = (samples as? [HKWorkout] ?? []).map { w in
                    HealthSample(
                        type: "workout_\(w.workoutActivityType.name)",
                        value: w.duration / 60, // minutes
                        date: ISO8601DateFormatter().string(from: w.startDate),
                        source: w.sourceRevision.source.name
                    )
                }

                if workoutSamples.isEmpty {
                    if let newAnchor { Task { @MainActor in self.saveAnchor(newAnchor, key: anchorKey) } }
                    cont.resume(returning: 0)
                    return
                }

                Task { @MainActor [weak self] in
                    guard let self else { return }
                    do {
                        let logged = try await self.client.logHealthSamples(workoutSamples)
                        if let newAnchor { self.saveAnchor(newAnchor, key: anchorKey) }
                        cont.resume(returning: logged)
                    } catch {
                        print("[JARVIS Health] Push workouts failed: \(error.localizedDescription)")
                        cont.resume(returning: 0)
                    }
                }
            }
            bridge.store.execute(query)
        }
    }

    // MARK: - Anchor persistence

    private func loadAnchor(key: String) -> HKQueryAnchor? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: data)
    }

    private func saveAnchor(_ anchor: HKQueryAnchor, key: String) {
        let data = try? NSKeyedArchiver.archivedData(withRootObject: anchor, requiringSecureCoding: true)
        UserDefaults.standard.set(data, forKey: key)
    }

    // MARK: - Time predicate

    private static var thirtyDaysPredicate: NSPredicate {
        let start = Calendar.current.date(byAdding: .day, value: -30, to: Date())!
        return HKQuery.predicateForSamples(withStart: start, end: nil, options: .strictStartDate)
    }

    // MARK: - All types

    static var allReadTypes: Set<HKSampleType> {
        var types = Set<HKSampleType>()
        for (id, _, _) in quantityTypes { types.insert(HKQuantityType(id)) }
        for (id, _, _) in categoryTypes { types.insert(HKCategoryType(id)) }
        types.insert(HKObjectType.workoutType())
        return types
    }

    // MARK: - Quantity type registry
    // (identifier, unit, JARVIS type name)

    static let quantityTypes: [(HKQuantityTypeIdentifier, HKUnit, String)] = [

        // ── Activity ─────────────────────────────────────────────────
        (.stepCount,                       .count(),                           "steps"),
        (.distanceWalkingRunning,          .meter(),                           "distance_walking_m"),
        (.distanceCycling,                 .meter(),                           "distance_cycling_m"),
        (.flightsClimbed,                  .count(),                           "flights_climbed"),
        (.activeEnergyBurned,              .kilocalorie(),                     "active_calories"),
        (.basalEnergyBurned,               .kilocalorie(),                     "basal_calories"),
        (.appleExerciseTime,               .minute(),                          "exercise_minutes"),
        (.appleStandTime,                  .minute(),                          "stand_minutes"),
        (.nikeFuel,                        .count(),                           "nike_fuel"),

        // ── Heart ─────────────────────────────────────────────────────
        (.heartRate,                       HKUnit.count().unitDivided(by: .minute()), "heart_rate"),
        (.restingHeartRate,                HKUnit.count().unitDivided(by: .minute()), "resting_heart_rate"),
        (.walkingHeartRateAverage,         HKUnit.count().unitDivided(by: .minute()), "walking_heart_rate"),
        (.heartRateVariabilitySDNN,        .secondUnit(with: .milli),          "hrv"),

        // ── Respiratory ───────────────────────────────────────────────
        (.oxygenSaturation,                .percent(),                         "spo2"),
        (.respiratoryRate,                 HKUnit.count().unitDivided(by: .minute()), "respiratory_rate"),

        // ── Body measurements ─────────────────────────────────────────
        (.bodyMass,                        .gramUnit(with: .kilo),             "weight_kg"),
        (.bodyMassIndex,                   .count(),                           "bmi"),
        (.bodyFatPercentage,               .percent(),                         "body_fat_pct"),
        (.leanBodyMass,                    .gramUnit(with: .kilo),             "lean_mass_kg"),
        (.height,                          .meter(),                           "height_m"),
        (.waistCircumference,              .meter(),                           "waist_m"),

        // ── Blood ─────────────────────────────────────────────────────
        (.bloodPressureSystolic,           .millimeterOfMercury(),             "bp_systolic"),
        (.bloodPressureDiastolic,          .millimeterOfMercury(),             "bp_diastolic"),
        (.bloodGlucose,                    HKUnit(from: "mg/dL"),              "blood_glucose"),

        // ── Mobility ─────────────────────────────────────────────────
        (.walkingSpeed,                    HKUnit(from: "m/s"),                "walking_speed"),
        (.walkingStepLength,               .meter(),                           "step_length_m"),
        (.walkingAsymmetryPercentage,      .percent(),                         "walking_asymmetry"),
        (.walkingDoubleSupportPercentage,  .percent(),                         "double_support_pct"),
        (.stairAscentSpeed,                HKUnit(from: "m/s"),                "stair_ascent_speed"),
        (.stairDescentSpeed,               HKUnit(from: "m/s"),                "stair_descent_speed"),

        // ── Hearing ───────────────────────────────────────────────────
        (.headphoneAudioExposure,          .decibelAWeightedSoundPressureLevel(), "headphone_db"),
        (.environmentalAudioExposure,      .decibelAWeightedSoundPressureLevel(), "env_audio_db"),

        // ── Nutrition (key macros) ────────────────────────────────────
        (.dietaryEnergyConsumed,           .kilocalorie(),                     "dietary_calories"),
        (.dietaryProtein,                  .gram(),                            "dietary_protein_g"),
        (.dietaryCarbohydrates,            .gram(),                            "dietary_carbs_g"),
        (.dietaryFatTotal,                 .gram(),                            "dietary_fat_g"),
        (.dietaryWater,                    .liter(),                           "dietary_water_l"),
        (.dietaryCaffeine,                 .gram(),                            "dietary_caffeine_g"),
    ]

    // MARK: - Category type registry
    // (identifier, JARVIS type name, value → Double? encoder)

    static let categoryTypes: [(HKCategoryTypeIdentifier, String, @Sendable (HKCategorySample) -> Double?)] = [

        // Sleep (encode duration in hours per asleep segment)
        (.sleepAnalysis, "sleep", { s in
            let asleepValues: Set<Int> = [
                HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue,
                HKCategoryValueSleepAnalysis.asleepCore.rawValue,
                HKCategoryValueSleepAnalysis.asleepDeep.rawValue,
                HKCategoryValueSleepAnalysis.asleepREM.rawValue,
            ]
            guard asleepValues.contains(s.value) else { return nil }
            return s.endDate.timeIntervalSince(s.startDate) / 3600
        }),

        // Stand hours (1 = stood, 0 = idle)
        (.appleStandHour, "stand_hour", { s in
            Double(s.value == HKCategoryValueAppleStandHour.stood.rawValue ? 1 : 0)
        }),

        // Mindful minutes (duration of session)
        (.mindfulSession, "mindful_minutes", { s in
            s.endDate.timeIntervalSince(s.startDate) / 60
        }),

        // Irregular rhythm notifications
        (.irregularHeartRhythmEvent, "irregular_rhythm", { _ in 1.0 }),

        // Low/high heart rate events
        (.highHeartRateEvent, "high_hr_event", { _ in 1.0 }),
        (.lowHeartRateEvent,  "low_hr_event",  { _ in 1.0 }),
    ]
}

// MARK: - HKWorkoutActivityType name helper

private extension HKWorkoutActivityType {
    var name: String {
        switch self {
        case .americanFootball:      return "american_football"
        case .archery:               return "archery"
        case .australianFootball:    return "australian_football"
        case .badminton:             return "badminton"
        case .baseball:              return "baseball"
        case .basketball:            return "basketball"
        case .bowling:               return "bowling"
        case .boxing:                return "boxing"
        case .climbing:              return "climbing"
        case .cricket:               return "cricket"
        case .crossTraining:         return "cross_training"
        case .curling:               return "curling"
        case .cycling:               return "cycling"
        case .dance:                 return "dance"
        case .elliptical:            return "elliptical"
        case .equestrianSports:      return "equestrian"
        case .fencing:               return "fencing"
        case .fishing:               return "fishing"
        case .functionalStrengthTraining: return "functional_strength"
        case .golf:                  return "golf"
        case .gymnastics:            return "gymnastics"
        case .handball:              return "handball"
        case .hiking:                return "hiking"
        case .hockey:                return "hockey"
        case .hunting:               return "hunting"
        case .lacrosse:              return "lacrosse"
        case .martialArts:           return "martial_arts"
        case .mindAndBody:           return "mind_and_body"
        case .mixedMetabolicCardioTraining: return "mixed_cardio"
        case .paddleSports:          return "paddle_sports"
        case .play:                  return "play"
        case .preparationAndRecovery: return "recovery"
        case .racquetball:           return "racquetball"
        case .rowing:                return "rowing"
        case .rugby:                 return "rugby"
        case .running:               return "running"
        case .sailing:               return "sailing"
        case .skatingSports:         return "skating"
        case .snowSports:            return "snow_sports"
        case .soccer:                return "soccer"
        case .softball:              return "softball"
        case .squash:                return "squash"
        case .stairClimbing:         return "stair_climbing"
        case .surfingSports:         return "surfing"
        case .swimming:              return "swimming"
        case .tableTennis:           return "table_tennis"
        case .tennis:                return "tennis"
        case .trackAndField:         return "track_and_field"
        case .traditionalStrengthTraining: return "strength_training"
        case .volleyball:            return "volleyball"
        case .walking:               return "walking"
        case .waterFitness:          return "water_fitness"
        case .waterPolo:             return "water_polo"
        case .waterSports:           return "water_sports"
        case .wrestling:             return "wrestling"
        case .yoga:                  return "yoga"
        case .barre:                 return "barre"
        case .coreTraining:          return "core_training"
        case .crossCountrySkiing:    return "cross_country_skiing"
        case .downhillSkiing:        return "downhill_skiing"
        case .flexibility:           return "flexibility"
        case .highIntensityIntervalTraining: return "hiit"
        case .jumpRope:              return "jump_rope"
        case .kickboxing:            return "kickboxing"
        case .pilates:               return "pilates"
        case .snowboarding:          return "snowboarding"
        case .stairs:                return "stairs"
        case .stepTraining:          return "step_training"
        case .wheelchairWalkPace:    return "wheelchair_walk"
        case .wheelchairRunPace:     return "wheelchair_run"
        case .taiChi:                return "tai_chi"
        case .mixedCardio:           return "mixed_cardio"
        case .handCycling:           return "hand_cycling"
        case .discSports:            return "disc_sports"
        case .fitnessGaming:         return "fitness_gaming"
        case .cardioDance:           return "cardio_dance"
        case .socialDance:           return "social_dance"
        case .pickleball:            return "pickleball"
        case .cooldown:              return "cooldown"
        default:                     return "workout_\(rawValue)"
        }
    }
}
