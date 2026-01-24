from flask import Flask, render_template, request, jsonify
from pyswip import Prolog
import json
from datetime import datetime

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
    prolog.assertz(":- dynamic driver_info/5")  # New: comprehensive driver info

    # --- Base violation rules ---
    prolog.assertz("violated_helmet_rule(D) :- wears_helmet(D, no)")
    prolog.assertz("violated_signal_rule(D, J) :- signal(J, red), stopped_at(D, J, no)")
    prolog.assertz("violated_speed_rule(D, J) :- speed(D, S), speed_limit(J, L), S > L")

    prolog.assertz("violation(D, 'Helmet Rule Violation') :- violated_helmet_rule(D)")
    prolog.assertz("violation(D, 'Signal Rule Violation') :- violated_signal_rule(D, _)")
    prolog.assertz("violation(D, 'Speed Limit Violation') :- violated_speed_rule(D, _)")

    # --- Enhanced rules ---
    prolog.assertz("severity(D, high) :- violated_helmet_rule(D)")
    prolog.assertz("severity(D, high) :- violated_speed_rule(D, _), overspeed_margin(D, M), M > 20")
    prolog.assertz("severity(D, medium) :- violated_signal_rule(D, _)")
    prolog.assertz("severity(D, low) :- violated_speed_rule(D, _), overspeed_margin(D, M), M =< 20")

    # --- Existing rules (keeping all your original functionality) ---
    prolog.assertz("driver_with_violation(Violation, D) :- violation(D, Violation)")
    prolog.assertz("collect_violations(D, L) :- collect_violations_aux(D, [], R), reverse(R, L)")
    prolog.assertz("collect_violations_aux(D, Acc, L) :- violation(D, V), \\+ member(V, Acc), !, collect_violations_aux(D, [V|Acc], L)")
    prolog.assertz("collect_violations_aux(_, Acc, Acc)")

    prolog.assertz("list_all_drivers(L) :- setof(D, J^H^(wears_helmet(D,H); stopped_at(D,J,_); speed(D,_)), L)")
    prolog.assertz("drivers_with_any_violation(L) :- setof(D, V^violation(D,V), L) ; L = []")
    prolog.assertz("first_violation(D, V) :- violation(D, V), !")
    prolog.assertz("safe_driver(D) :- \\+ violation(D, _)")
    prolog.assertz("overspeed_margin(D, M) :- speed(D, S), speed_limit(J, L), S > L, M is S - L")
    prolog.assertz("fine_amount(D, F) :- overspeed_margin(D, M), F is (M // 10) * 100")

    _RULES_INITIALIZED = True

@app.route("/")
def index():
    init_rules_once()
    return render_template("index.html")

@app.route("/api/stats")
def api_stats():
    """API endpoint for dashboard statistics"""
    init_rules_once()
    
    # Get total drivers
    all_drivers = list(prolog.query("list_all_drivers(L)"))
    total_drivers = len(all_drivers[0]["L"]) if all_drivers else 0
    
    # Get violators
    violators = list(prolog.query("drivers_with_any_violation(L)"))
    total_violators = len(violators["L"]) if violators else 0
    
    # Calculate safe drivers
    safe_drivers = max(0, total_drivers - total_violators)
    
    return jsonify({
        'total_drivers': total_drivers,
        'total_violations': total_violators,
        'safe_drivers': safe_drivers
    })

@app.route("/", methods=["POST"])
def process_request():
    init_rules_once()
    
    mode = request.form.get("mode", "by_driver")
    action = request.form.get("action", "")
    
    # Get form data
    driver_raw = request.form.get("driver", "")
    junction_raw = request.form.get("junction", "")
    helmet_raw = request.form.get("helmet", "no")
    signal_raw = request.form.get("signal", "red")
    stopped_raw = request.form.get("stopped", "no")
    speed_raw = request.form.get("speed", "0")
    limit_raw = request.form.get("speed_limit", "0")
    persist_choice = request.form.get("persist", "")
    
    # Process data
    driver = _to_atom(driver_raw) if driver_raw else ""
    junction = _to_atom(junction_raw) if junction_raw else ""
    wears_helmet = _to_atom(helmet_raw or "no")
    signal_color = _to_atom(signal_raw or "red")
    stopped = _to_atom(stopped_raw or "no")
    
    try:
        speed = int(speed_raw or 0)
        speed_limit = int(limit_raw or 0)
    except ValueError:
        speed = speed_limit = 0

    # Handle various actions
    if action == "list_all_drivers":
        res = list(prolog.query("list_all_drivers(L)"))
        drivers = res[0]["L"] if res else []
        return render_template("result.html", 
                             mode="list_all", 
                             driver="", 
                             violations=drivers, 
                             violation_label="All Drivers", 
                             drivers_for_violation=[])

    if action == "list_violators":
        res = list(prolog.query("drivers_with_any_violation(L)"))
        violators = res[0]["L"] if res else []
        return render_template("result.html", 
                             mode="list_all", 
                             driver="", 
                             violations=violators, 
                             violation_label="Drivers with Violations", 
                             drivers_for_violation=[])

    if action == "reset_facts":
        prolog.query("retractall(wears_helmet(_, _))")
        prolog.query("retractall(signal(_, _))")
        prolog.query("retractall(stopped_at(_, _, _))")
        prolog.query("retractall(speed(_, _))")
        prolog.query("retractall(speed_limit(_, _))")
        return render_template("result.html", 
                             mode="by_driver", 
                             driver="", 
                             violations=["✅ All facts cleared successfully"], 
                             violation_label="", 
                             drivers_for_violation=[])

    if action == "remove_driver" and driver:
        prolog.query(f"retractall(wears_helmet({driver}, _))")
        prolog.query(f"retractall(stopped_at({driver}, _, _))")
        prolog.query(f"retractall(speed({driver}, _))")
        return render_template("result.html", 
                             mode="by_driver", 
                             driver=driver_raw, 
                             violations=[f"✅ All data for {driver_raw} removed successfully"], 
                             violation_label="", 
                             drivers_for_violation=[])

    if action == "check_safe" and driver:
        res = list(prolog.query(f"safe_driver({driver})"))
        violations = ["✅ Safe Driver (No Violations Found)"] if res else ["⚠️ Driver has one or more violations"]
        return render_template("result.html", 
                             mode="negation", 
                             driver=driver_raw, 
                             violations=violations, 
                             violation_label="", 
                             drivers_for_violation=[])

    if action == "calc_fine" and driver:
        res = list(prolog.query(f"fine_amount({driver}, F)"))
        if res:
            violations = [f"💰 Fine Amount: ₹{r['F']}" for r in res]
        else:
            violations = ["✅ No Fine Required (Within Speed Limit)"]
        return render_template("result.html", 
                             mode="arithmetic", 
                             driver=driver_raw, 
                             violations=violations, 
                             violation_label="", 
                             drivers_for_violation=[])

    if action == "first_violation" and driver:
        res = list(prolog.query(f"first_violation({driver}, V)"))
        violations = [r["V"] for r in res] if res else ["No Violations Found"]
        return render_template("result.html", 
                             mode="first_violation", 
                             driver=driver_raw, 
                             violations=violations, 
                             violation_label="", 
                             drivers_for_violation=[])

    # Main processing logic
    if driver and junction:
        if persist_choice == "yes":
            # Store facts in Prolog
            prolog.assertz(f"wears_helmet({driver}, {wears_helmet})")
            prolog.assertz(f"signal({junction}, {signal_color})")
            prolog.assertz(f"stopped_at({driver}, {junction}, {stopped})")
            prolog.assertz(f"speed({driver}, {speed})")
            prolog.assertz(f"speed_limit({junction}, {speed_limit})")

        if mode == "by_driver":
            violations = [res["V"] for res in prolog.query(f"violation({driver}, V)")]
            if not violations:
                violations = ["✅ No Violations Found"]
            return render_template("result.html", 
                                 mode=mode, 
                                 driver=driver_raw, 
                                 violations=violations, 
                                 violation_label="", 
                                 drivers_for_violation=[])

        elif mode == "by_violation":
            violation_label = request.form.get("violation_label", "Helmet Rule Violation")
            drivers = [res["D"] for res in prolog.query(f"driver_with_violation('{violation_label}', D)")]
            drivers_display = [d.replace("_", " ").title() for d in sorted(set(drivers))]
            return render_template("result.html", 
                                 mode=mode, 
                                 driver="", 
                                 violations=[], 
                                 violation_label=violation_label, 
                                 drivers_for_violation=drivers_display if drivers_display else ["No drivers found"])

    # Default error response
    return render_template("result.html", 
                         mode="by_driver", 
                         driver=driver_raw or "Unknown", 
                         violations=["⚠️ Please provide complete driver and junction details"], 
                         violation_label="", 
                         drivers_for_violation=[])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
