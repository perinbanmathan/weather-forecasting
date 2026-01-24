from flask import Flask, render_template, request
from pyswip import Prolog

app = Flask(__name__)
prolog = Prolog()
prolog.consult("traffic.pl")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    driver = request.form.get("driver", "").strip()
    junction = request.form.get("junction", "").strip()
    helmet = request.form.get("helmet", "no")
    signal = request.form.get("signal", "red")
    stopped = request.form.get("stopped", "no")
    speed = int(request.form.get("speed", 0))
    speed_limit = int(request.form.get("speed_limit", 40))
    mode = request.form.get("mode", "by_driver")
    action = request.form.get("action")

    violations = []
    drivers_for_violation = []

    # ✅ Normal check by driver
    if action == "check":
        query = f"collect_violations_recursive([{driver}], Result)"
        res = list(prolog.query(query))
        if res:
            violations = res[0]["Result"][0] or ["No Violations"]

    # ✅ First violation
    elif action == "first_violation":
        query = f"collect_violations_recursive([{driver}], Result)"
        res = list(prolog.query(query))
        if res and res[0]["Result"][0]:
            violations = [res[0]["Result"][0][0]]
        else:
            violations = ["No Violations"]

    # ✅ Safety check (negation)
    elif action == "check_safe":
        query = f"collect_violations_recursive([{driver}], Result)"
        res = list(prolog.query(query))
        if res and not res[0]["Result"][0]:
            violations = ["Safe Driver ✅"]
        else:
            violations = ["Unsafe Driver ❌"]

    # ✅ Fine calculation (arithmetic)
    elif action == "calc_fine":
        fine = 0
        query = f"collect_violations_recursive([{driver}], Result)"
        res = list(prolog.query(query))
        if res:
            v_list = res[0]["Result"][0]
            for v in v_list:
                if "Helmet" in v:
                    fine += 500
                elif "Signal" in v:
                    fine += 1000
                elif "Speed" in v:
                    fine += 1500
        violations = [f"Total Fine: ₹{fine}" if fine > 0 else "No Fine"]

    # ✅ List all drivers
    elif action == "list_all_drivers":
        res = list(prolog.query("driver(Name, _, _, _, _, _)"))
        violations = [r["Name"] for r in res]
        mode = "list_all"
        return render_template("result.html", mode=mode, violations=violations, violation_label="All Drivers")

    # ✅ List violators
    elif action == "list_violators":
        res = list(prolog.query("helmet_violation(Name); signal_violation(Name); speed_violation(Name)"))
        violations = list({r["Name"] for r in res})
        mode = "list_all"
        return render_template("result.html", mode=mode, violations=violations, violation_label="Violators")

    return render_template("result.html", mode=mode, driver=driver, violations=violations,
                           violation_label=request.form.get("violation_label", ""),
                           drivers_for_violation=drivers_for_violation)
