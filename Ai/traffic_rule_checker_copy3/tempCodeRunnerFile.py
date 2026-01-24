from flask import Flask, render_template, request
from pyswip import Prolog

app = Flask(__name__)

prolog = Prolog()
_RULES_INITIALIZED = False


def _to_atom(s: str) -> str:
    return str(s).strip().lower().replace(" ", "_")


def init_rules_once():
    global _RULES_INITIALIZED
    if _RULES_INITIALIZED:
        return

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

    # --- Unification ---
    prolog.assertz("driver_with_violation(Violation, D) :- violation(D, Violation)")

    # --- Recursion-based collector (Prolog side) ---
    prolog.assertz("collect_violations(D, L) :- collect_violations_aux(D, [], R), reverse(R, L)")
    prolog.assertz("collect_violations_aux(D, Acc, L) :- violation(D, V), \\+ member(V, Acc), !, collect_violations_aux(D, [V|Acc], L)")
    prolog.assertz("collect_violations_aux(_, Acc, Acc)")

    # --- List Operations ---
    prolog.assertz("list_all_drivers(L) :- setof(D, J^H^(wears_helmet(D,H); stopped_at(D,J,_); speed(D,_)), L)")
    prolog.assertz("drivers_with_any_violation(L) :- setof(D, V^violation(D,V), L) ; L = []")

    # --- Cut Operation Example ---
    prolog.assertz("first_violation(D, V) :- violation(D, V), !")

    # --- Negation Example ---
    prolog.assertz("safe_driver(D) :- \\+ violation(D, _)")

    # --- Arithmetic / Fine Calculation ---
    prolog.assertz("overspeed_margin(D, M) :- speed(D, S), speed_limit(J, L), S > L, M is S - L")
    prolog.assertz("fine_amount(D, 500) :- violated_helmet_rule(D)")
    prolog.assertz("fine_amount(D, 1000) :- violated_signal_rule(D, _)")
    prolog.assertz("fine_amount(D, F) :- overspeed_margin(D, M), F is (M // 10) * 100")

    _RULES_INITIALIZED = True


# --- Recursive Function  ---

def all_violation(driver, violation_list=None):
   
    if violation_list is None:
        violation_list = []

    # Query next violation
    res = list(prolog.query(f"violation({driver}, V)"))
    if not res:
        return violation_list  # Base case: no more violations

    for r in res:
        v = r["V"]
        if v not in violation_list:
            # Recurse with updated list
            return all_violation(driver, violation_list + [v])

    return violation_list  # if all already collected



@app.route("/", methods=["GET", "POST"])
def index():
    init_rules_once()

    if request.method == "POST":
        mode = request.form.get("mode", "by_driver")
        action = request.form.get("action", "")

        driver_raw = request.form.get("driver", "")
        junction_raw = request.form.get("junction", "")
        helmet_raw = request.form.get("helmet", "no")
        signal_raw = request.form.get("signal", "red")
        stopped_raw = request.form.get("stopped", "no")
        speed_raw = request.form.get("speed", "0")
        limit_raw = request.form.get("speed_limit", "0")
        persist_choice = request.form.get("persist", "yes")

        driver = _to_atom(driver_raw) if driver_raw else ""
        junction = _to_atom(junction_raw) if junction_raw else ""
        wears_helmet = _to_atom(helmet_raw or "no")
        signal_color = _to_atom(signal_raw or "red")
        stopped = _to_atom(stopped_raw or "no")

        try:
            speed = int(speed_raw or 0)
        except ValueError:
            speed = 0
        try:
            speed_limit = int(limit_raw or 0)
        except ValueError:
            speed_limit = 0

        # --- Handle list operations ---
        if action == "list_all_drivers":
            res = list(prolog.query("list_all_drivers(L)"))
            drivers = res[0]["L"] if res else []
            return render_template("result.html", mode="list_all", driver="", violations=drivers, violation_label="All Drivers", drivers_for_violation=[])

        if action == "list_violators":
            res = list(prolog.query("drivers_with_any_violation(L)"))
            violators = res[0]["L"] if res else []
            return render_template("result.html", mode="list_all", driver="", violations=violators, violation_label="Drivers with Violations", drivers_for_violation=[])

        # --- Reset facts ---
        if action == "reset_facts":
            prolog.query("retractall(wears_helmet(_, _))")
            prolog.query("retractall(signal(_, _))")
            prolog.query("retractall(stopped_at(_, _, _))")
            prolog.query("retractall(speed(_, _))")
            prolog.query("retractall(speed_limit(_, _))")
            return render_template("result.html", mode="by_driver", driver="", violations=["All facts cleared ✅"], violation_label="", drivers_for_violation=[])

        if action == "remove_driver" and driver:
            prolog.query(f"retractall(wears_helmet({driver}, _))")
            prolog.query(f"retractall(stopped_at({driver}, _, _))")
            prolog.query(f"retractall(speed({driver}, _))")
            return render_template("result.html", mode="by_driver", driver=driver_raw, violations=[f"Facts for {driver_raw} removed ✅"], violation_label="", drivers_for_violation=[])
        
        if action == "check_safe" and driver:
            res = list(prolog.query(f"safe_driver({driver})"))
            violations = ["✅ Safe Driver (No Violations)"] if res else ["❌ Driver has violations"]
            return render_template("result.html", mode="negation", driver=driver_raw, violations=violations, violation_label="", drivers_for_violation=[])
        
        if action == "calc_fine" and driver:
            res = list(prolog.query(f"findall((Type,F), (violation({driver}, Type), fine_amount({driver}, F)), L)"))
            if res and res[0]["L"]:
                fines = res[0]["L"]
                total = sum(f for (_, f) in fines)
                violations = [{"type": v, "fine": f} for (v, f) in fines]
            else:
                violations = []
                total = 0
            return render_template("result.html", mode="arithmetic", driver=driver_raw, violations=violations, total_fine=total, violation_label="", drivers_for_violation=[])

        # --- By Driver Mode ---
        if mode == "by_driver" and driver and junction:
            if persist_choice == "yes":
                prolog.query(f"retractall(wears_helmet({driver}, _))")
                prolog.query(f"retractall(stopped_at({driver}, {junction}, _))")
                prolog.query(f"retractall(speed({driver}, _))")
                prolog.query(f"retractall(speed_limit({junction}, _))")
                prolog.query(f"retractall(signal({junction}, _))")

                prolog.assertz(f"wears_helmet({driver}, {wears_helmet})")
                prolog.assertz(f"signal({junction}, {signal_color})")
                prolog.assertz(f"stopped_at({driver}, {junction}, {stopped})")
                prolog.assertz(f"speed({driver}, {speed})")
                prolog.assertz(f"speed_limit({junction}, {speed_limit})")

            # ✅ Use Python recursive function here
            violations = all_violation(driver)
            if not violations:
                violations = ["No Violations ✅"]

            return render_template("result.html", mode=mode, driver=driver_raw, violations=violations, violation_label="", drivers_for_violation=[])

        # --- By Violation Mode ---
        elif mode == "by_violation":
            violation_label = request.form.get("violation_label", "Helmet Rule Violation")

            if persist_choice == "yes" and driver and junction:
                prolog.query(f"retractall(wears_helmet({driver}, _))")
                prolog.query(f"retractall(stopped_at({driver}, {junction}, _))")
                prolog.query(f"retractall(speed({driver}, _))")
                prolog.query(f"retractall(speed_limit({junction}, _))")
                prolog.query(f"retractall(signal({junction}, _))")

                prolog.assertz(f"wears_helmet({driver}, {wears_helmet})")
                prolog.assertz(f"signal({junction}, {signal_color})")
                prolog.assertz(f"stopped_at({driver}, {junction}, {stopped})")
                prolog.assertz(f"speed({driver}, {speed})")
                prolog.assertz(f"speed_limit({junction}, {speed_limit})")

            drivers = [res["D"] for res in prolog.query(f"driver_with_violation('{violation_label}', D)")]
            drivers_display = [d.replace("_", " ").title() for d in sorted(set(drivers))]

            return render_template("result.html", mode=mode, driver="", violations=[], violation_label=violation_label, drivers_for_violation=drivers_display if drivers_display else ["None found"])

        return render_template("result.html", mode="by_driver", driver=driver_raw or "(missing)", violations=["Please provide driver & junction details."], violation_label="", drivers_for_violation=[])

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
