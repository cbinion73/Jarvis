/// Wraps a non-Sendable value for safe transfer across concurrency boundaries
/// when the caller knows the usage is actually safe.
struct UncheckedSendable<T>: @unchecked Sendable {
    let value: T
    init(_ value: T) { self.value = value }
}
