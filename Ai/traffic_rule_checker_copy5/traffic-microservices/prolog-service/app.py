from flask import Flask, request, jsonify, send_file
from pyswip import Prolog
import csv, os

app = Flask(__name__)
prolog = Prolog()

def init_rules_once():
    try:
        prolog.assertz(":- dynamic wears_helmet/2")
        prolog.assertz(":- dynamic signal/2")
        prolog.assertz(":- dynamic stopped_at/3")
        prolog.assertz(":- dynamic speed/2")
        prolog.assertz(":- dynamic speed_limit/2")

        prolog.assertz("violated_helmet_rule(D) :- wears_helmet(D, no)")
        prolog.assertz("violated_signal_rule(D, J) :- signal(J, red), stopped_at(D, J, no)")
        prolog.assertz("violated_speed_rule(D, J) :- speed(D, S), speed_limit(J, L), S > L")

        prolog.assertz("violation(D, 'Helmet Rule Violation') :- violated_helmet_rule(D)")
        prolog.assertz("violation(D, 'Signal Rule Violation') :- violated_signal_rule(D, _)")
        prolog.assertz("violation(D, 'Speed Limit Violation') :- violated_speed_rule(D, _)")

        prolog.assertz("driver_with_violation(Violation, D) :- violation(D, Violation)")

        prolog.assertz("collect_violations(D, L) :- collect_violations_aux(D, [], R), reverse(R, L)")
        prolog.assertz("collect_violations_aux(D, Acc, L) :- violation(D, V), \\+ member(V, Acc), !, collect_violations_aux(D, [V|Acc], L)")
        prolog.assertz("collect_violations_aux(_, Acc, Acc)")

        prolog.assertz("list_all_drivers(L) :- setof(D, J^H^(wears_helmet(D,H); stopped_at(D,J,_); speed(D,_)), L) ; L = []")
        prolog.assertz("drivers_with_any_violation(L) :- setof(D, V^violation(D,V), L) ; L = []")

        prolog.assertz("first_violation(D, V) :- violation(D, V), !")
        prolog.assertz("safe_driver(D) :- \\+ violation(D, _)")
        prolog.assertz("overspeed_margin(D, M) :- speed(D, S), speed_limit(J, L), S > L, M is S - L")
        prolog.assertz("fine_amount(D, 500) :- violated_helmet_rule(D)")
        prolog.assertz("fine_amount(D, 1000) :- violated_signal_rule(D, _)")
        prolog.assertz("fine_amount(D, F) :- overspeed_margin(D, M), F is (M // 10) * 100, F > 0")
    except Exception as e:
        print('init error', e)

init_rules_once()

def _to_atom(s: str) -> str:
    return str(s).strip().lower().replace(" ", "_")

def collect_violations_python(driver_atom):
    res = list(prolog.query(f"collect_violations({driver_atom}, L)"))
    if res and res[0].get("L") is not None:
        return res[0]["L"]
    vs = [r["V"] for r in prolog.query(f"violation({driver_atom}, V)")]
    out = []
    for v in vs:
        if v not in out:
            out.append(v)
    return out

@app.route("/assert", methods=["POST"])
def assert_fact():
    data = request.json or {}
    fact = data.get("fact")
    if not fact:
        return jsonify({"error":"fact missing"}), 400
    try:
        prolog.assertz(fact)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})

@app.route("/retract", methods=["POST"])
def retract_facts():
    data = request.json or {}
    query = data.get("query")
    if not query:
        return jsonify({"error":"query missing"}), 400
    try:
        prolog.query(f"retractall({query})")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})

@app.route("/drivers", methods=["GET"])
def list_drivers():
    res = list(prolog.query("list_all_drivers(L)"))
    drivers = res[0]["L"] if res and res[0].get("L") else []
    return jsonify({"drivers": [str(d) for d in drivers]})

@app.route("/violations/<driver>", methods=["GET"])
def get_violations(driver):
    d = _to_atom(driver)
    try:
        res = list(prolog.query(f"collect_violations({d}, L)"))
        if res and res[0].get("L"):
            return jsonify({"driver": driver, "violations": res[0]["L"]})
        vs = [r["V"] for r in prolog.query(f"violation({d}, V)")]
        return jsonify({"driver": driver, "violations": vs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export_dataset", methods=["GET"])
def export_dataset():
    rows = []
    res = list(prolog.query("list_all_drivers(L)"))
    drivers = res[0]["L"] if res and res[0].get("L") else []
    for d in drivers:
        helmet = None
        r = list(prolog.query(f"wears_helmet({d}, H)"))
        if r: helmet = r[0]["H"]
        stopped = None; junction = None; signal = None; limit = 0
        r = list(prolog.query(f"stopped_at({d}, J, S)"))
        if r:
            junction = r[0]["J"]
            stopped = r[0]["S"]
            r2 = list(prolog.query(f"signal({junction}, C)"))
            if r2: signal = r2[0]["C"]
            r3 = list(prolog.query(f"speed_limit({junction}, L)"))
            if r3: limit = int(r3[0]["L"])
        r = list(prolog.query(f"speed({d}, SP)"))
        speed = int(r[0]["SP"]) if r else 0
        viols = collect_violations_python(d)
        viol_count = len(viols)
        fine_sum = 0
        for resf in list(prolog.query(f"findall((T,F),(violation({d},T),(fine_amount({d},F);F=0)),L)")):
            L = resf.get("L", [])
            for item in L:
                try:
                    t, f = item
                    fine_sum += int(f)
                except Exception:
                    pass
        rows.append({
            "driver": str(d),
            "helmet": str(helmet or "no"),
            "signal": str(signal or "red"),
            "stopped": str(stopped or "no"),
            "speed": speed,
            "limit": limit,
            "viol_count": viol_count,
            "a_star_score": fine_sum
        })
    path = "dataset_from_prolog.csv"
    if rows:
        keys = rows[0].keys()
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
    else:
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
    return send_file(path, as_attachment=True)

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
