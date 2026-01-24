from flask import Flask, render_template, request, redirect, url_for
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
    prolog.assertz(":- dynamic wears_helmet/2")       # wears_helmet(Driver, yes/no)
    prolog.assertz(":- dynamic signal/2")             # signal(Junction, red/green)
    prolog.assertz(":- dynamic stopped_at/3")         # stopped_at(Driver, Junction, yes/no)
    prolog.assertz(":- dynamic speed/3")              # speed(Driver, Junction, Speed)  <-- changed to /3
    prolog.assertz(":- dynamic speed_limit/2")        # speed_limit(Junction, Limit)

    # --- Base violation rules (junction-aware) ---
    prolog.assertz("violated_helmet_rule(D) :- wears_helmet(D, no)")
    prolog.assertz("violated_signal_rule(D, J) :- signal(J, red), stopped_at(D, J, no)")
    prolog.assertz("violated_speed_rule(D, J) :- speed(D, J, S), speed_limit(J, L), S > L")

    # Unified violation names (for quick checks, not for fines)
    prolog.assertz("violation(D, 'Helmet Rule Violation') :- violated_helmet_rule(D)")
    prolog.assertz("violation(D, 'Signal Rule Violation') :- violated_signal_rule(D, _)")
    prolog.assertz("violation(D, 'Speed Limit Violation') :- violated_speed_rule(D, _)")

    # Unification helper
    prolog.assertz("driver_with_violation(Violation, D) :- violation(D, Violation)")

    # List ops
    prolog.assertz("list_all_drivers(L) :- setof(D, (H^J^S^(wears_helmet(D,H); stopped_at(D,J,_); speed(D,J,S))), L)")
    prolog.assertz("drivers_with_any_violation(L) :- setof(D, V^violation(D,V), L) ; L = []")

    # Negation
    prolog.assertz("safe_driver(D) :- \\+ violation(D, _)")

    # Overspeed margin per junction
    prolog.assertz("overspeed_margin(D, J, M) :- speed(D, J, S), speed_limit(J, L), S > L, M is S - L")

    # ---- Fine items (accurate & junction-aware) ----
    # Helmet fine is applied at most once if the driver violates helmet rule.
    prolog.assertz("fine_item(D, 'Helmet Rule Violation', 500) :- violated_helmet_rule(D), !")

    # Signal fine: Rs.1000 per red-signal run, per junction.
    prolog.assertz("""
    fine_item(D, helmet, 1000) :-
        drives(D, V), not(wears_helmet(D, V)).

    fine_item(D, signal, 1500) :-
        drives(D, V), signal(J, red), not(stopped_at(D, V, J)).

    fine_item(D, speed, F) :-
        drives(D, V), speed(V, S), speed_limit(V, L), S > L,
        Overspeed is S - L,
        F is Overspeed * 100.
""")


    # Overspeed fine: (margin // 10) * 100 per junction where S>L
    prolog.assertz("""fine_item(D, T, F) :-
        violated_speed_rule(D, J),
        speed(D, J, S),
        speed_limit(J, L),
        M is S - L,
        F is (M // 10) * 100,
        atom_concat('Overspeed @ ', J, T)
    """)

    # Sum list helper (portable)
    prolog.assertz("sum_list([], 0)")
    prolog.assertz("sum_list([H|T], S) :- sum_list(T, R), S is R + H")

    # Total fine for a driver
    prolog.assertz(\"\"\"total_fine(D, Total) :-
        findall(F, fine_item(D, _, F), Fs),
        sum_list(Fs, Total)
    \"\"\")

    _RULES_INITIALIZED = True


# ---------------- Home ----------------
@app.route("/")
def home():
    init_rules_once()
    return render_template("home.html")


# ---------------- By Driver (event logging & check) ----------------
@app.route("/by-driver", methods=["GET", "POST"])
def by_driver():
    init_rules_once()
    if request.method == "GET":
        return render_template("by_driver.html")

    # POST
    driver_raw = request.form.get("driver", "")
    junction_raw = request.form.get("junction", "")
    helmet_raw = request.form.get("helmet", "no")
    signal_raw = request.form.get("signal", "red")
    stopped_raw = request.form.get("stopped", "no")
    speed_raw = request.form.get("speed", "0")
    limit_raw = request.form.get("speed_limit", "0")
    persist = request.form.get("persist", "add")  # add | overwrite

    if not driver_raw or not junction_raw:
        return render_template("by_driver_result.html", driver=driver_raw or "(missing)", violations=["Please provide driver & junction."], info=[])

    driver = _to_atom(driver_raw)
    junction = _to_atom(junction_raw)
    helmet = _to_atom(helmet_raw)
    signal_c = _to_atom(signal_raw)
    stopped = _to_atom(stopped_raw)

    try:
        speed = int(speed_raw or 0)
    except ValueError:
        speed = 0
    try:
        limit = int(limit_raw or 0)
    except ValueError:
        limit = 0

    # Overwrite event for that (driver, junction) if chosen
    if persist == "overwrite":
        prolog.query(f"retractall(stopped_at({driver}, {junction}, _))")
        prolog.query(f"retractall(speed({driver}, {junction}, _))")
        prolog.query(f"retractall(signal({junction}, _))")
        prolog.query(f"retractall(speed_limit({junction}, _))")

    # Keep only one helmet fact per driver (latest known status)
    prolog.query(f"retractall(wears_helmet({driver}, _))")
    prolog.assertz(f"wears_helmet({driver}, {helmet})")

    # Assert junction facts for this event
    prolog.assertz(f"signal({junction}, {signal_c})")
    prolog.assertz(f"stopped_at({driver}, {junction}, {stopped})")
    if speed > 0:
        prolog.assertz(f"speed({driver}, {junction}, {speed})")
    if limit > 0:
        prolog.assertz(f"speed_limit({junction}, {limit})")

    # Gather violations for the driver
    violations = [r["V"] for r in prolog.query(f"violation({driver}, V)")]
    if not violations:
        violations = ["No Violations ✅"]

    # Also prepare short info lines for what was recorded
    info = []
    info.append(f"Helmet: {helmet_raw}")
    info.append(f"Signal at {junction_raw}: {signal_raw}")
    info.append(f"Stopped at {junction_raw}: {stopped_raw}")
    if speed > 0:  info.append(f"Speed @ {junction_raw}: {speed}")
    if limit > 0:  info.append(f"Limit @ {junction_raw}: {limit}")

    return render_template("by_driver_result.html", driver=driver_raw, violations=violations, info=info)


# ---------------- By Violation (list drivers for a type) ----------------
@app.route("/by-violation", methods=["GET", "POST"])
def by_violation():
    init_rules_once()
    if request.method == "GET":
        return render_template("by_violation.html")

    violation_label = request.form.get("violation_label", "Helmet Rule Violation")
    drivers = [r["D"] for r in prolog.query(f"driver_with_violation('{violation_label}', D)")]
    drivers_display = [d.replace("_", " ").title() for d in sorted(set(drivers))]
    if not drivers_display:
        drivers_display = ["None found"]
    return render_template("by_violation_result.html", violation_label=violation_label, drivers=drivers_display)


# ---------------- List: All Drivers ----------------
@app.route("/drivers")
def list_drivers():
    init_rules_once()
    res = list(prolog.query("list_all_drivers(L)"))
    drivers = res[0]["L"] if res else []
    drivers_display = [d.replace("_", " ").title() for d in drivers]
    return render_template("list_drivers.html", drivers=drivers_display)


# ---------------- List: Violators ----------------
@app.route("/violators")
def list_violators():
    init_rules_once()
    res = list(prolog.query("drivers_with_any_violation(L)"))
    drivers = res[0]["L"] if res else []
    drivers_display = [d.replace("_", " ").title() for d in drivers]
    return render_template("list_violators.html", drivers=drivers_display)


# ---------------- Safe Check ----------------
@app.route("/safe-check", methods=["GET", "POST"])
def safe_check():
    init_rules_once()
    if request.method == "GET":
        return render_template("safe_check.html")

    driver_raw = request.form.get("driver", "")
    if not driver_raw:
        return render_template("safe_check_result.html", driver="(missing)", message="Please provide a driver name.", safe=None)

    driver = _to_atom(driver_raw)
    res = list(prolog.query(f"safe_driver({driver})"))
    if res:
        return render_template("safe_check_result.html", driver=driver_raw, message="✅ Safe Driver (No Violations)", safe=True)
    else:
        return render_template("safe_check_result.html", driver=driver_raw, message="❌ Driver has violations", safe=False)


# ---------------- Calculate Fine ----------------
@app.route("/calc-fine", methods=["GET", "POST"])
def calc_fine():
    init_rules_once()
    if request.method == "GET":
        return render_template("calc_fine.html")

    driver_raw = request.form.get("driver", "")
    if not driver_raw:
        return render_template("calc_fine_result.html", driver="(missing)", items=[], total=0)

    driver = _to_atom(driver_raw)

    # Get all fine items (Type, Fine)
    res_items = list(prolog.query(f"findall((T,F), fine_item({driver}, T, F), L)"))
    items = []
    if res_items and res_items[0]["L"]:
        for (t, f) in res_items[0]["L"]:
            items.append({"type": t, "fine": int(f)})

    # Compute total
    res_total = list(prolog.query(f"total_fine({driver}, Total)"))
    total = int(res_total[0]["Total"]) if res_total else 0

    return render_template("calc_fine_result.html", driver=driver_raw, items=items, total=total)


# ---------------- Remove Driver ----------------
@app.route("/remove-driver", methods=["GET", "POST"])
def remove_driver():
    init_rules_once()
    if request.method == "GET":
        return render_template("remove_driver.html")

    driver_raw = request.form.get("driver", "")
    if not driver_raw:
        return render_template("remove_done.html", message="Please provide a driver name.")
    driver = _to_atom(driver_raw)
    prolog.query(f"retractall(wears_helmet({driver}, _))")
    prolog.query(f"retractall(stopped_at({driver}, _, _))")
    prolog.query(f"retractall(speed({driver}, _, _))")
    return render_template("remove_done.html", message=f"Facts for '{driver_raw}' removed ✅")


# ---------------- Reset All Facts ----------------
@app.route("/reset", methods=["POST"])
def reset():
    init_rules_once()
    prolog.query("retractall(wears_helmet(_, _))")
    prolog.query("retractall(signal(_, _))")
    prolog.query("retractall(stopped_at(_, _, _))")
    prolog.query("retractall(speed(_, _, _))")
    prolog.query("retractall(speed_limit(_, _))")
    return render_template("reset_done.html")


if __name__ == "__main__":
    app.run(debug=True)
