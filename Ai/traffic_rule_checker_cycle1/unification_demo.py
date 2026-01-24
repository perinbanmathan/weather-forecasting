from pyswip import Prolog

# Initialize Prolog
prolog = Prolog()

# --- Dynamic predicates ---
prolog.assertz(":- dynamic wears_helmet/2")
prolog.assertz(":- dynamic signal/2")
prolog.assertz(":- dynamic stopped_at/3")
prolog.assertz(":- dynamic speed/2")
prolog.assertz(":- dynamic speed_limit/2")

# --- Base violation rules ---
prolog.assertz("violated_helmet_rule(D) :- wears_helmet(D, no)")
prolog.assertz("violated_signal_rule(D, J) :- signal(J, red), stopped_at(D, J, no)")
prolog.assertz("violated_speed_rule(D, J) :- speed(D, S), speed_limit(J, L), S > L")

prolog.assertz("violation(D, 'Helmet Rule Violation') :- violated_helmet_rule(D)")
prolog.assertz("violation(D, 'Signal Rule Violation') :- violated_signal_rule(D, _)")
prolog.assertz("violation(D, 'Speed Limit Violation') :- violated_speed_rule(D, _)")

# --- Unification rule ---
prolog.assertz("driver_with_violation(Violation, D) :- violation(D, Violation)")

# === Example Facts ===
prolog.assertz("wears_helmet(driver1, no)")
prolog.assertz("signal(junction1, red)")
prolog.assertz("stopped_at(driver1, junction1, no)")
prolog.assertz("speed(driver1, 80)")
prolog.assertz("speed_limit(junction1, 60)")

prolog.assertz("wears_helmet(driver2, yes)")
prolog.assertz("signal(junction1, red)")
prolog.assertz("stopped_at(driver2, junction1, yes)")
prolog.assertz("speed(driver2, 50)")
prolog.assertz("speed_limit(junction1, 60)")

# === Queries ===
print("🔹 Violations for each driver (using unification):")
for result in prolog.query("driver_with_violation(V, D)"):
    print(f"Driver: {result['D']} → Violation: {result['V']}")

print("\n🔹 Violations of driver1 only:")
for result in prolog.query("violation(driver1, V)"):
    print("driver1 →", result["V"])

print("\n🔹 Drivers who violated the Signal Rule:")
for result in prolog.query("driver_with_violation('Signal Rule Violation', D)"):
    print("Driver:", result["D"])
