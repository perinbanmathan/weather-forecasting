from flask import Flask, render_template, request, redirect, url_for, flash
from pyswip import Prolog

app = Flask(__name__)
app.secret_key = "dev-secret"  # for flash messages

prolog = Prolog()
prolog.consult("knowledge_base.pl")

def q(query):
    """Helper to run a Prolog query and return list(dict)."""
    return list(prolog.query(query))

@app.route("/")
def index():
    # List vehicles and overall stats
    vehicles = [row["V"] for row in q("vehicle(V)")]
    offenders = [row["V"] for row in q("(vehicle(V), violation(V,_))")]
    offenders = sorted(set(offenders))
    exists_any = bool(q("exists_any_violation"))
    all_ok = bool(q("all_follow_speed_limits"))
    return render_template(
        "index.html",
        vehicles=vehicles,
        offenders=offenders,
        exists_any=exists_any,
        all_ok=all_ok,
    )

@app.route("/vehicle/<vid>")
def vehicle(vid):
    # Violations
    vlist = q(f"violation({vid}, T)")
    violations = [row["T"] for row in vlist]

    # Detailed pairs (Type, Amount)
    pairs = q(f"violations_with_amounts({vid}, Pairs)")
    detailed = []
    if pairs:
        for (t, a) in pairs[0]["Pairs"]:
            detailed.append((t, a))

    # Totals & priority fine
    total = q(f"total_fine({vid}, Total)")
    total_fine = total[0]["Total"] if total else 0

    pf = q(f"priority_fine({vid}, F)")
    priority = pf[0]["F"] if pf else 0

    # Owner & speed context
    owner = q(f"owner({vid}, O)")
    owner_name = owner[0]["O"] if owner else "unknown"

    speed = q(f"speed({vid}, S)")
    speed_val = speed[0]["S"] if speed else None

    atj = q(f"at_junction({vid}, J)")
    junction = atj[0]["J"] if atj else None

    limit = q(f"(at_junction({vid}, J), speed_limit(J, L))")
    speed_limit_val = limit[0]["L"] if limit else None

    law = bool(q(f"law_abiding({vid})"))

    return render_template(
        "vehicle.html",
        vid=vid,
        owner=owner_name,
        violations=violations,
        detailed=detailed,
        total_fine=total_fine,
        priority_fine=priority,
        speed=speed_val,
        junction=junction,
        speed_limit=speed_limit_val,
        law_abiding=law,
    )

@app.route("/update", methods=["POST"])
def update():
    vid = request.form.get("vehicle").strip()
    field = request.form.get("field")
    value = request.form.get("value").strip()

    if not q(f"vehicle({vid})"):
        flash(f"Vehicle {vid} does not exist.")
        return redirect(url_for("index"))

    if field == "helmet":
        if value not in ("yes", "no"):
            flash("Helmet value must be yes/no.")
        else:
            q(f"set_helmet({vid}, {value})")
            flash(f"Updated helmet_worn({vid}, {value}).")
    elif field == "signal":
        if value not in ("yes", "no"):
            flash("Signal value must be yes/no.")
        else:
            q(f"set_signal({vid}, {value})")
            flash(f"Updated signal_respected({vid}, {value}).")
    elif field == "speed":
        try:
            sval = int(value)
            q(f"set_speed({vid}, {sval})")
            flash(f"Updated speed({vid}, {sval}).")
        except:
            flash("Speed must be an integer.")
    elif field == "junction":
        q(f"set_at_junction({vid}, {value})")
        flash(f"Updated at_junction({vid}, {value}).")
    elif field == "limit":
        # Update speed limit for the vehicle's junction (if set)
        j = q(f"at_junction({vid}, J)")
        if j:
            J = j[0]["J"]
            try:
                lval = int(value)
                q(f"set_speed_limit({J}, {lval})")
                flash(f"Updated speed_limit({J}, {lval}).")
            except:
                flash("Limit must be an integer.")
        else:
            flash("Vehicle has no junction set; set junction first.")
    else:
        flash("Unknown field.")

    return redirect(url_for("vehicle", vid=vid))

@app.route("/predict/<vid>")
def predict(vid):
    # Use Prolog's prediction print (side-effect); also show flash
    res = q(f"predict_speed_violation({vid})")
    if res:
        flash(f"{vid}: likely to overspeed soon (near limit).")
    else:
        flash(f"{vid}: not close to overspeed threshold.")
    return redirect(url_for("vehicle", vid=vid))

if __name__ == "__main__":
    app.run(debug=True)
