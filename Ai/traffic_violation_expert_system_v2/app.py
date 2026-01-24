from flask import Flask, render_template, request, redirect, url_for, flash
from pyswip import Prolog

app = Flask(__name__)
app.secret_key = "super-secret-key"

# Consult the new, enhanced knowledge base
prolog = Prolog()
prolog.consult("knowledge_base_v2.pl")

def q(query):
    """Helper to run a Prolog query and return a list of results."""
    return list(prolog.query(query))

@app.route("/")
def index():
    # Fetch vehicles with their types
    vehicles_q = q("vehicle(V, Type)")
    vehicles = [{"id": r["V"], "type": r["Type"]} for r in vehicles_q]

    # Fetch all unique owners
    owners_q = q("owner(_, O)")
    owners = sorted(list(set(r["O"] for r in owners_q)))

    # Fetch owners whose licenses are at risk
    at_risk_q = q("all_owners_at_risk(Owners)")
    owners_at_risk = at_risk_q[0]["Owners"] if at_risk_q else []
    
    # Calculate total points for each owner
    owner_points = {}
    for owner in owners:
        points_q = q(f"total_points_for_owner('{owner}', TotalPoints)")
        if points_q:
            owner_points[owner] = points_q[0]["TotalPoints"]

    return render_template(
        "index.html",
        vehicles=vehicles,
        owners=owners,
        owner_points=owner_points,
        owners_at_risk=owners_at_risk
    )

@app.route("/vehicle/<vid>")
def vehicle(vid):
    # Basic vehicle info
    owner_q = q(f"owner({vid}, O)")
    owner = owner_q[0]["O"] if owner_q else "Unknown"
    
    type_q = q(f"vehicle({vid}, Type)")
    v_type = type_q[0]["Type"] if type_q else "Unknown"

    # Get all violations with full details (Type, Amount, Severity, Points)
    details_q = q(f"violations_with_details({vid}, Details)")
    violations_details = []
    if details_q and details_q[0]["Details"]:
        # PySWIP returns a list of Functors; we convert them
        for detail_func in details_q[0]["Details"]:
            violations_details.append({
                "type": detail_func.args[0],
                "amount": detail_func.args[1],
                "severity": detail_func.args[2],
                "points": detail_func.args[3]
            })

    # Calculate total fine and points for this specific vehicle
    total_fine_q = q(f"findall(A, (violation({vid}, T), fine(T, A, _, _)), Am), sum_list(Am, Total)")
    total_fine = total_fine_q[0]["Total"] if total_fine_q else 0
    
    total_points_q = q(f"total_points_for_vehicle({vid}, TotalPoints)")
    total_points = total_points_q[0]["TotalPoints"] if total_points_q else 0
    
    # Check owner's overall license status
    license_risk_q = q(f"license_at_risk('{owner}')")
    is_at_risk = bool(license_risk_q)

    return render_template(
        "vehicle.html",
        vid=vid,
        owner=owner,
        v_type=v_type,
        violations_details=violations_details,
        total_fine=total_fine,
        total_points=total_points,
        is_at_risk=is_at_risk
    )

# A simplified update route for demonstration
@app.route("/update_status", methods=["POST"])
def update_status():
    vid = request.form.get("vid")
    status_type = request.form.get("status_type")
    new_value = request.form.get("new_value")

    # This is a simplified handler. A real app would have more robust validation.
    if vid and status_type and new_value:
        # Retract old fact and assert new one
        prolog.retractall(f"{status_type}({vid}, _)")
        prolog.assertz(f"{status_type}({vid}, {new_value})")
        flash(f"Updated {status_type} for {vid} to {new_value}.", "success")
    else:
        flash("Invalid update data.", "error")

    return redirect(url_for("vehicle", vid=vid))


if __name__ == "__main__":
    app.run(debug=True)