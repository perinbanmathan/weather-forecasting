from flask import Flask, render_template, request
from pyswip import Prolog
import heapq

app = Flask(__name__)
prolog = Prolog()
_RULES_INITIALIZED = False


def _to_atom(s: str) -> str:
    return str(s).strip().lower().replace(" ", "_")


def init_rules_once():
    """
    Initialize dynamic predicates, base violations, utility rules,
    and fine calculation rules. Runs once per app lifetime.
    """
    global _RULES_INITIALIZED
    if _RULES_INITIALIZED:
        return

    # dynamic predicates
    prolog.assertz(":- dynamic wears_helmet/2")
    prolog.assertz(":- dynamic signal/2")
    prolog.assertz(":- dynamic stopped_at/3")
    prolog.assertz(":- dynamic speed/2")
    prolog.assertz(":- dynamic speed_limit/2")

    # base violation rules
    prolog.assertz("violated_helmet_rule(D) :- wears_helmet(D, no)")
    prolog.assertz("violated_signal_rule(D, J) :- signal(J, red), stopped_at(D, J, no)")
    prolog.assertz("violated_speed_rule(D, J) :- speed(D, S), speed_limit(J, L), S > L")

    prolog.assertz("violation(D, 'Helmet Rule Violation') :- violated_helmet_rule(D)")
    prolog.assertz("violation(D, 'Signal Rule Violation') :- violated_signal_rule(D, _)")
    prolog.assertz("violation(D, 'Speed Limit Violation') :- violated_speed_rule(D, _)")

    # unification helper
    prolog.assertz("driver_with_violation(Violation, D) :- violation(D, Violation)")

    # collect violations (backtracking + recursion)
    prolog.assertz("collect_violations(D, L) :- collect_violations_aux(D, [], R), reverse(R, L)")
    prolog.assertz("collect_violations_aux(D, Acc, L) :- violation(D, V), \\+ member(V, Acc), !, collect_violations_aux(D, [V|Acc], L)")
    prolog.assertz("collect_violations_aux(_, Acc, Acc)")

    # list operations
    prolog.assertz("list_all_drivers(L) :- setof(D, J^H^(wears_helmet(D,H); stopped_at(D,J,_); speed(D,_)), L) ; L = []")
    prolog.assertz("drivers_with_any_violation(L) :- setof(D, V^violation(D,V), L) ; L = []")

    # cut example
    prolog.assertz("first_violation(D, V) :- violation(D, V), !")

    # negation example
    prolog.assertz("safe_driver(D) :- \\+ violation(D, _)")

    # arithmetic / fine calculation
    prolog.assertz("overspeed_margin(D, M) :- speed(D, S), speed_limit(J, L), S > L, M is S - L")
    prolog.assertz("fine_amount(D, 500) :- violated_helmet_rule(D)")
    prolog.assertz("fine_amount(D, 1000) :- violated_signal_rule(D, _)")
    # speed-based fine: each 10km over -> 100
    prolog.assertz("fine_amount(D, F) :- overspeed_margin(D, M), F is (M // 10) * 100, F > 0")

    _RULES_INITIALIZED = True


# -----------------------
# Python helpers: Prolog wrappers
# -----------------------
def collect_violations_python(driver_atom):
    """Return list of violations for driver using Prolog collector (keeps ordering & uniqueness)."""
    res = list(prolog.query(f"collect_violations({driver_atom}, L)"))
    if res and res[0].get("L") is not None:
        return res[0]["L"]
    # fallback: probe violation/2 results (may duplicate)
    vs = [r["V"] for r in prolog.query(f"violation({driver_atom}, V)")]
    return list(dict.fromkeys(vs))


def fines_for_driver(driver_atom):
    """Return list of (Type, Fine) tuples for driver."""
    res = list(prolog.query(f"findall((Type,F), (violation({driver_atom}, Type), (fine_amount({driver_atom}, F) ; F = 0)), L)"))
    if not res:
        return []
    raw = res[0]["L"]
    # raw is list of tuples; ensure python-friendly format
    fines = []
    for item in raw:
        # PySWIP may give tuples as (b'Helmet Rule Violation', 500) or plain strings
        try:
            t, f = item
        except Exception:
            continue
        fines.append((t, int(f)))
    return fines


# -----------------------
# A* (ranking) and AO* (AND/OR combos) implementations
# -----------------------
VIOLATION_PRIORITY = {
    "Helmet Rule Violation": 2,
    "Signal Rule Violation": 4,
    "Speed Limit Violation": 3
}


def a_star_rank(driver_atom):
    """
    Rank violations by cost = fine + priority weight.
    Return list sorted descending by cost (major first) with dict entries.
    """
    violations = collect_violations_python(driver_atom)
    if not violations:
        return []

    fines = fines_for_driver(driver_atom)
    fine_map = {t: f for (t, f) in fines}

    ranked = []
    for v in violations:
        fine = fine_map.get(v, 0)
        priority = VIOLATION_PRIORITY.get(v, 1)
        cost = fine + priority
        ranked.append({"type": v, "fine": fine, "priority": priority, "score": cost})

    # sort descending by score (major offense first)
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def ao_star_suggest(driver_atom):
    """
    Handle simple AND/OR dependencies and return a list of suggested actions
    and an optimized/aggregated fine decision.
    Example rule: if Signal violation + Speed violation -> Major combined offense.
    (This is a demonstration AO* style combination, not a full AO* search tree.)
    """
    violations = collect_violations_python(driver_atom)
    if not violations:
        return [], 0

    fines = fines_for_driver(driver_atom)
    fine_map = {t: f for (t, f) in fines}
    suggestions = []
    used = set()

    # Example dependency: Signal + Speed -> Combined Major Offense
    if ("Signal Rule Violation" in violations) and ("Speed Limit Violation" in violations):
        # create combined node
        combined_fine = fine_map.get("Signal Rule Violation", 0) + fine_map.get("Speed Limit Violation", 0) + 200  # extra penalty
        suggestions.append({"type": "Signal+Speed Combined Offense", "fine": combined_fine, "note": "Combined penalty (AO*)"})
        used.update({"Signal Rule Violation", "Speed Limit Violation"})

    # add remaining individual violations
    for v in violations:
        if v in used:
            continue
        suggestions.append({"type": v, "fine": fine_map.get(v, 0), "note": "Individual"})

    total = sum(s["fine"] for s in suggestions)
    return suggestions, total


# -----------------------
# Routes
# -----------------------
@app.route("/", methods=["GET", "POST"])
def index():
    init_rules_once()

    if request.method == "POST":
        # read form inputs
        mode = request.form.get("mode", "by_driver")
        action = request.form.get("action", "check")

        driver_raw = request.form.get("driver", "").strip()
        junction_raw = request.form.get("junction", "").strip()
        helmet_raw = request.form.get("helmet", "no")
        signal_raw = request.form.get("signal", "red")
        stopped_raw = request.form.get("stopped", "no")
        speed_raw = request.form.get("speed", "0")
        limit_raw = request.form.get("speed_limit", "0")
        persist_choice = request.form.get("persist", "yes")
        violation_label = request.form.get("violation_label", "Helmet Rule Violation")

        driver = _to_atom(driver_raw) if driver_raw else ""
        junction = _to_atom(junction_raw) if junction_raw else ""

        # sanitize ints
        try:
            speed = int(speed_raw or 0)
        except ValueError:
            speed = 0
        try:
            speed_limit = int(limit_raw or 0)
        except ValueError:
            speed_limit = 0

        # List all drivers
        if action == "list_all_drivers":
            res = list(prolog.query("list_all_drivers(L)"))
            drivers = res[0]["L"] if res else []
            drivers_display = [d.replace("_", " ").title() for d in drivers]
            return render_template("result.html",
                                   mode="list_all",
                                   driver="",
                                   violations=drivers_display,
                                   violation_label="All Drivers",
                                   drivers_for_violation=[])

        # List drivers with violations
        if action == "list_violators":
            res = list(prolog.query("drivers_with_any_violation(L)"))
            violators = res[0]["L"] if res else []
            drivers_display = [d.replace("_", " ").title() for d in violators]
            return render_template("result.html",
                                   mode="list_all",
                                   driver="",
                                   violations=drivers_display,
                                   violation_label="Drivers with Violations",
                                   drivers_for_violation=[])

        # Reset facts
        if action == "reset_facts":
            prolog.query("retractall(wears_helmet(_, _))")
            prolog.query("retractall(signal(_, _))")
            prolog.query("retractall(stopped_at(_, _, _))")
            prolog.query("retractall(speed(_, _))")
            prolog.query("retractall(speed_limit(_, _))")
            return render_template("result.html",
                                   mode="info",
                                   driver="",
                                   violations=["All facts cleared "],
                                   violation_label="",
                                   drivers_for_violation=[])

        # Remove single driver facts
        if action == "remove_driver" and driver:
            prolog.query(f"retractall(wears_helmet({driver}, _))")
            prolog.query(f"retractall(stopped_at({driver}, _, _))")
            prolog.query(f"retractall(speed({driver}, _))")
            return render_template("result.html",
                                   mode="info",
                                   driver=driver_raw,
                                   violations=[f"Facts for {driver_raw} removed "],
                                   violation_label="",
                                   drivers_for_violation=[])

        # Check safe driver (negation)
        if action == "check_safe" and driver:
            res = list(prolog.query(f"safe_driver({driver})"))
            violations_out = [" Safe Driver (No Violations)"] if res else [" Driver has violations"]
            return render_template("result.html",
                                   mode="negation",
                                   driver=driver_raw,
                                   violations=violations_out,
                                   violation_label="",
                                   drivers_for_violation=[])

        # Calculate fines (arithmetic)
        if action == "calc_fine" and driver:
            res = list(prolog.query(f"findall((Type,F), (violation({driver}, Type), (fine_amount({driver}, F) ; F = 0)), L)"))
            fine_list = []
            total = 0
            if res and res[0].get("L"):
                for (t, f) in res[0]["L"]:
                    try:
                        ff = int(f)
                    except Exception:
                        ff = 0
                    fine_list.append({"type": t, "fine": ff})
                    total += ff
            return render_template("result.html",
                                   mode="arithmetic",
                                   driver=driver_raw,
                                   violations=fine_list,
                                   total_fine=total,
                                   violation_label="",
                                   drivers_for_violation=[])

        # First violation (cut)
        if action == "first_violation" and driver:
            res = list(prolog.query(f"first_violation({driver}, V)"))
            vlist = [r["V"] for r in res] if res else ["None found"]
            return render_template("result.html",
                                   mode="first_violation",
                                   driver=driver_raw,
                                   violations=vlist,
                                   violation_label="",
                                   drivers_for_violation=[])

        # By violation mode: list drivers with that violation
        if mode == "by_violation":
            if persist_choice == "yes" and driver and junction:
                # persist facts for future queries
                prolog.query(f"retractall(wears_helmet({driver}, _))")
                prolog.query(f"retractall(stopped_at({driver}, {junction}, _))")
                prolog.query(f"retractall(speed({driver}, _))")
                prolog.query(f"retractall(speed_limit({junction}, _))")
                prolog.query(f"retractall(signal({junction}, _))")

                prolog.assertz(f"wears_helmet({driver}, {helmet_raw or 'no'})")
                prolog.assertz(f"signal({junction}, {signal_raw or 'red'})")
                prolog.assertz(f"stopped_at({driver}, {junction}, {stopped_raw or 'no'})")
                prolog.assertz(f"speed({driver}, {speed})")
                prolog.assertz(f"speed_limit({junction}, {speed_limit})")

            # query drivers for chosen violation label
            # note: violation_label is a string with spaces -> wrap in single quotes for Prolog
            qlabel = "'" + violation_label + "'"
            drivers = [res["D"] for res in prolog.query(f"driver_with_violation({qlabel}, D)")]
            drivers_display = [d.replace("_", " ").title() for d in sorted(set(drivers))] if drivers else ["None found"]
            return render_template("result.html",
                                   mode="by_violation",
                                   driver="",
                                   violations=[],
                                   violation_label=violation_label,
                                   drivers_for_violation=drivers_display)

        # By driver mode: persist facts if requested, then compute violations
        if mode == "by_driver":
            if driver and junction and persist_choice == "yes":
                prolog.query(f"retractall(wears_helmet({driver}, _))")
                prolog.query(f"retractall(stopped_at({driver}, {junction}, _))")
                prolog.query(f"retractall(speed({driver}, _))")
                prolog.query(f"retractall(speed_limit({junction}, _))")
                prolog.query(f"retractall(signal({junction}, _))")

                prolog.assertz(f"wears_helmet({driver}, {helmet_raw or 'no'})")
                prolog.assertz(f"signal({junction}, {signal_raw or 'red'})")
                prolog.assertz(f"stopped_at({driver}, {junction}, {stopped_raw or 'no'})")
                prolog.assertz(f"speed({driver}, {speed})")
                prolog.assertz(f"speed_limit({junction}, {speed_limit})")

            # default action = check violations
            if action == "check" or action == "":
                violations = collect_violations_python(driver)
                if not violations:
                    violations = ["No Violations "]
                return render_template("result.html",
                                       mode="by_driver",
                                       driver=driver_raw,
                                       violations=violations,
                                       violation_label="",
                                       drivers_for_violation=[])

            # A* major violation
            if action == "a_star":
                ranked = a_star_rank(driver)
                if not ranked:
                    msg = ["No Violations "]
                    return render_template("result.html",
                                           mode="ai_a_star",
                                           driver=driver_raw,
                                           violations=msg,
                                           ranked=[],
                                           violation_label="",
                                           drivers_for_violation=[])
                # major is first
                major = ranked[0]
                return render_template("result.html",
                                       mode="ai_a_star",
                                       driver=driver_raw,
                                       violations=[],
                                       ranked=ranked,
                                       violation_label="",
                                       drivers_for_violation=[])

            # AO* suggestion / optimization
            if action == "ao_star":
                suggestions, total = ao_star_suggest(driver)
                if not suggestions:
                    suggestions = [{"type": "No Violations ", "fine": 0, "note": ""}]
                return render_template("result.html",
                                       mode="ai_ao_star",
                                       driver=driver_raw,
                                       violations=suggestions,
                                       total_fine=total,
                                       violation_label="",
                                       drivers_for_violation=[])

        # fallback - missing inputs
        return render_template("result.html",
                               mode="info",
                               driver=driver_raw or "(missing)",
                               violations=["Please provide driver & junction details or choose an action."],
                               violation_label="",
                               drivers_for_violation=[])

    # GET default
    return render_template("index.html")



if __name__ == "__main__":
    app.run(debug=True)
