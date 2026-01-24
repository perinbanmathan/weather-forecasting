
from flask import Flask, render_template, request, jsonify
from pyswip import Prolog
import heapq
import pandas as pd
import os

# sklearn imports
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

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
    # ensure uniqueness while preserving order
    out = []
    for v in vs:
        if v not in out:
            out.append(v)
    return out


def fines_for_driver(driver_atom):
    """Return list of (Type, Fine) tuples for driver."""
    res = list(prolog.query(
        f"findall((Type,F), (violation({driver_atom}, Type), (fine_amount({driver_atom}, F) ; F = 0)), L)"))
    if not res:
        return []
    raw = res[0]["L"]
    fines = []
    for item in raw:
        try:
            t, f = item
        except Exception:
            continue
        try:
            fines.append((t, int(f)))
        except Exception:
            fines.append((t, 0))
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
        combined_fine = fine_map.get("Signal Rule Violation", 0) + fine_map.get("Speed Limit Violation", 0) + 200
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
# ML: Export / Train / Predict
# -----------------------
def export_dataset():
    """
    Export Prolog facts (helmet, signal, stopped, speed, speed_limit)
    into a structured pandas DataFrame and save dataset.csv
    """
    rows = []

    res = list(prolog.query("list_all_drivers(L)"))
    driver_list = res[0]["L"] if res and res[0].get("L") is not None else []

    for d in driver_list:
        # defaults
        helmet = "no"
        signal = "red"
        stopped = "no"
        speed = 0
        limit = 0

        r = list(prolog.query(f"wears_helmet({d}, H)"))
        if r:
            helmet = str(r[0]["H"])

        # Try to find a junction where this driver has a stopped_at fact; if found, also collect signal & speed_limit for that junction.
        r = list(prolog.query(f"stopped_at({d}, J, S)"))
        junction_for_driver = None
        if r:
            junction_for_driver = r[0]["J"]
            stopped = str(r[0]["S"])

            # signal at that junction
            r2 = list(prolog.query(f"signal({junction_for_driver}, C)"))
            if r2:
                signal = str(r2[0]["C"])

            r3 = list(prolog.query(f"speed_limit({junction_for_driver}, L)"))
            if r3:
                limit = int(r3[0]["L"])

        # speed fact (driver-level)
        r = list(prolog.query(f"speed({d}, SP)"))
        if r:
            try:
                speed = int(r[0]["SP"])
            except Exception:
                speed = 0

        violations = collect_violations_python(d)
        label = "Safe" if len(violations) == 0 else "Violation"

        rows.append({
            "driver": str(d),
            "helmet": helmet,
            "signal": signal,
            "stopped": stopped,
            "speed": int(speed),
            "limit": int(limit),
            "label": label
        })

    df = pd.DataFrame(rows)
    # save CSV
    if not df.empty:
        df.to_csv("dataset.csv", index=False)
    else:
        # ensure we remove old dataset if no facts present
        try:
            if os.path.exists("dataset.csv"):
                os.remove("dataset.csv")
        except Exception:
            pass
    return df


def train_ml_models():
    """
    Train ML models on exported dataset.
    Automatically handles the case where dataset has only 1 class.
    """
    df = export_dataset()
    if df.empty:
        return None, "Dataset empty — add some driver facts first."

    le_helmet = LabelEncoder()
    le_signal = LabelEncoder()
    le_stopped = LabelEncoder()
    le_label = LabelEncoder()

    df["helmet_enc"] = le_helmet.fit_transform(df["helmet"])
    df["signal_enc"] = le_signal.fit_transform(df["signal"])
    df["stopped_enc"] = le_stopped.fit_transform(df["stopped"])
    df["label_enc"] = le_label.fit_transform(df["label"])

    X = df[["helmet_enc", "signal_enc", "stopped_enc", "speed", "limit"]]
    y = df["label_enc"]

    unique_classes = df["label_enc"].unique()
    
    # ------------------------------
    # ⚠ FIX: Dataset has only one class
    # ------------------------------
    if len(unique_classes) == 1:
        return "single_class", {
            "encoders": {
                "helmet": le_helmet,
                "signal": le_signal,
                "stopped": le_stopped,
                "label": le_label
            },
            "class_value": unique_classes[0]
        }

    # ------------------------------
    # Normal training (2+ classes)
    # ------------------------------
    models = {
        "DecisionTree": DecisionTreeClassifier().fit(X, y),
        "KNN": KNeighborsClassifier(n_neighbors=3).fit(X, y),
        "LogisticRegression": LogisticRegression(max_iter=300).fit(X, y)
    }

    return models, {
        "helmet": le_helmet,
        "signal": le_signal,
        "stopped": le_stopped,
        "label": le_label
    }


def ml_predict(models, encoders, helmet, signal, stopped, speed, limit):
    """
    Predict using trained models OR single-class fallback.
    """

    # If models == "single_class" then ML result is trivial
    if models == "single_class":
        class_value = encoders["class_value"]
        label = encoders["encoders"]["label"].inverse_transform([class_value])[0]
        return {
            "DecisionTree": label,
            "KNN": label,
            "LogisticRegression": label
        }

    # Normal ML prediction
    h = encoders["helmet"].transform([helmet])[0] if helmet in encoders["helmet"].classes_ else 0
    s = encoders["signal"].transform([signal])[0] if signal in encoders["signal"].classes_ else 0
    st = encoders["stopped"].transform([stopped])[0] if stopped in encoders["stopped"].classes_ else 0

    X = [[h, s, st, int(speed), int(limit)]]

    results = {}
    for name, model in models.items():
        pred = model.predict(X)[0]
        results[name] = encoders["label"].inverse_transform([pred])[0]

    return results



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


@app.route("/classify", methods=["POST"])
def classify_case():

    init_rules_once()

    driver_raw = request.form.get("driver", "").strip()
    junction_raw = request.form.get("junction", "").strip()
    helmet = request.form.get("helmet", "no")
    signal = request.form.get("signal", "red")
    stopped = request.form.get("stopped", "no")
    speed = int(request.form.get("speed", 0))
    limit = int(request.form.get("speed_limit", 0))

    driver = _to_atom(driver_raw) if driver_raw else ""
    junction = _to_atom(junction_raw) if junction_raw else ""

    # Insert temporary facts
    if driver:
        prolog.query(f"retractall(wears_helmet({driver}, _))")
        prolog.query(f"retractall(stopped_at({driver}, _, _))")
        prolog.query(f"retractall(speed({driver}, _))")

    if junction:
        prolog.query(f"retractall(signal({junction}, _))")
        prolog.query(f"retractall(speed_limit({junction}, _))")

    if driver:
        prolog.assertz(f"wears_helmet({driver}, {helmet})")
        prolog.assertz(f"stopped_at({driver}, {junction or 'j0'}, {stopped})")
        prolog.assertz(f"speed({driver}, {speed})")

    if junction:
        prolog.assertz(f"signal({junction}, {signal})")
        prolog.assertz(f"speed_limit({junction}, {limit})")

    # Prolog reasoning
    violations = collect_violations_python(driver)
    prolog_label = "Safe" if len(violations) == 0 else "Violation"

    # ML training
    models, enc = train_ml_models()

    # ML prediction
    ml_results = ml_predict(models, enc, helmet, signal, stopped, speed, limit)

    return jsonify({
        "driver": driver_raw,
        "input": {
            "helmet": helmet,
            "signal": signal,
            "stopped": stopped,
            "speed": speed,
            "speed_limit": limit
        },
        "prolog_reasoning": prolog_label,
        "ml_predictions": ml_results
    })


from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np
import matplotlib.pyplot as plt
import io, base64
from tabulate import tabulate


@app.route("/regression")
def regression_results():
    """
    Regression module for Traffic Rule Violation Checker.
    Predicts continuous A* scores using ML regression
    and compares them with Prolog A* scores.
    """

    init_rules_once()

    # 1. Collect all drivers
    res = list(prolog.query("list_all_drivers(L)"))
    if not res or not res[0]["L"]:
        return "<h3>No driver facts available. Add drivers first.</h3>"

    drivers = res[0]["L"]

    # Dataset containers
    X = []       # features
    y = []       # target (A* score)
    table_rows = []

    for d in drivers:
        # Fetch helmet
        r = list(prolog.query(f"wears_helmet({d}, H)"))
        helmet = 1 if (r and r[0]["H"] == "yes") else 0

        # Fetch junction-specific facts
        r = list(prolog.query(f"stopped_at({d}, J, S)"))
        if r:
            junction = r[0]["J"]
            stopped = 1 if r[0]["S"] == "yes" else 0

            # signal
            r2 = list(prolog.query(f"signal({junction}, C)"))
            signal = 1 if (r2 and r2[0]["C"] == "green") else 0

            # speed limit
            r3 = list(prolog.query(f"speed_limit({junction}, L)"))
            limit = int(r3[0]["L"]) if r3 else 0
        else:
            junction = None
            stopped = 0
            signal = 0
            limit = 0

        # speed
        r = list(prolog.query(f"speed({d}, SP)"))
        speed = int(r[0]["SP"]) if r else 0

        # Compute Prolog A* cost (top violation)
        ranked = a_star_rank(d)
        if ranked:
            prolog_score = ranked[0]["score"]
        else:
            prolog_score = 0

        # Add to dataset
        X.append([helmet, signal, stopped, speed, limit])
        y.append(prolog_score)

        table_rows.append([d, helmet, signal, stopped, speed, limit, prolog_score])

    # Convert to numpy
    X = np.array(X)
    y = np.array(y)

    # Train regression model
    model = LinearRegression()
    model.fit(X, y)

    # Predictions
    y_pred = model.predict(X)

    # Metrics
    mae = mean_absolute_error(y, y_pred)
    mse = mean_squared_error(y, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y, y_pred)

    # Plot Regression vs Prolog Score
    fig, ax = plt.subplots()
    ax.scatter(y, y_pred, color='blue', alpha=0.7, label="Predictions")
    m, b = np.polyfit(y, y_pred, 1)
    x_line = np.linspace(min(y), max(y), 100)
    y_line = m * x_line + b
    ax.plot(x_line, y_line, color='red', linewidth=2, label=f"Fit Line: y={m:.2f}x+{b:.2f}")

    ax.set_xlabel("Prolog A* Score")
    ax.set_ylabel("Predicted Score")
    ax.set_title("Regression Model vs Prolog A* Score")
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plot_data = base64.b64encode(buf.read()).decode()
    plt.close(fig)

    # Build HTML output
    table_html = tabulate(
        [[row[0], row[6], round(y_pred[i], 3)] for i, row in enumerate(table_rows)],
        headers=["Driver", "Prolog Score", "ML Prediction"],
        tablefmt="html"
    )

    html = f"""
    <h2>Regression Analysis — A* Score Prediction</h2>
    <h3>Model Used: Linear Regression</h3>

    <h4>Metrics</h4>
    <ul>
        <li><strong>MAE:</strong> {mae:.4f}</li>
        <li><strong>RMSE:</strong> {rmse:.4f}</li>
        <li><strong>MSE:</strong> {mse:.4f}</li>
        <li><strong>R² Score:</strong> {r2:.4f}</li>
    </ul>

    <h4>Comparison Table</h4>
    {table_html}

    <h4>Regression Plot</h4>
    <img src="data:image/png;base64,{plot_data}" />

    <br><br>
    <a href="/" style="font-size:18px;">⬅ Back</a>
    """
    return html
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    adjusted_rand_score,
    normalized_mutual_info_score
)
import numpy as np
import matplotlib.pyplot as plt
import io, base64
from tabulate import tabulate

@app.route("/classification_ui")
def classification_ui():
    return render_template("classification.html")

@app.route("/clustering")
def clustering_module():

    init_rules_once()

    # Fetch all drivers
    res = list(prolog.query("list_all_drivers(L)"))
    if not res or not res[0]["L"]:
        return "<h3>No drivers found. Add facts first.</h3>"

    drivers = res[0]["L"]

    X = []   # features
    Y = []   # symbolic groups
    rows = []

    for d in drivers:

        # Extract helmet
        r = list(prolog.query(f"wears_helmet({d}, H)"))
        helmet = 1 if (r and r[0]["H"] == "yes") else 0

        # Stopped, signal, limit info
        r = list(prolog.query(f"stopped_at({d}, J, S)"))
        if r:
            junction = r[0]["J"]
            stopped = 1 if r[0]["S"] == "yes" else 0

            r2 = list(prolog.query(f"signal({junction}, C)"))
            signal = 1 if (r2 and r2[0]["C"] == "green") else 0

            r3 = list(prolog.query(f"speed_limit({junction}, L)"))
            limit = int(r3[0]["L"]) if r3 else 0
        else:
            stopped = 0
            signal = 0
            limit = 0

        # Speed
        r = list(prolog.query(f"speed({d}, SP)"))
        speed = int(r[0]["SP"]) if r else 0

        # Count violations (symbolic grouping)
        viols = collect_violations_python(d)
        viol_count = len(viols)

        # Symbolic label:
        # 0 = safe, 1 = minor, 2 = major
        if viol_count == 0:
            group = 0
        elif viol_count == 1:
            group = 1
        else:
            group = 2

        # Add to dataset
        X.append([helmet, signal, stopped, speed, limit, viol_count])
        Y.append(group)
        rows.append([d, helmet, signal, stopped, speed, limit, viol_count, group])

    X = np.array(X)
    Y = np.array(Y)

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K-Means clustering
    n_clusters = 3
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)

    # Metrics
    sil = silhouette_score(X_scaled, cluster_labels)
    db = davies_bouldin_score(X_scaled, cluster_labels)
    ari = adjusted_rand_score(Y, cluster_labels)
    nmi = normalized_mutual_info_score(Y, cluster_labels)

    # PCA for 2D visualization
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    fig, ax = plt.subplots(figsize=(7,6))

    colors = ['red', 'blue', 'green']
    markers = ['o', 's', '^']

    # ML clusters
    for i in range(n_clusters):
        pts = X_pca[cluster_labels == i]
        ax.scatter(pts[:, 0], pts[:, 1],
                   c=colors[i], s=60, alpha=0.6, label=f"Cluster {i}")

    # Overlay symbolic groups (Prolog group)
    for g in np.unique(Y):
        pts = X_pca[Y == g]
        ax.scatter(pts[:, 0], pts[:, 1],
                   facecolors='none', edgecolors='black',
                   marker=markers[g], s=120, linewidths=1.5,
                   label=f"Symbolic Group {g}")

    # Centroids
    centroids = pca.transform(kmeans.cluster_centers_)
    ax.scatter(centroids[:, 0], centroids[:, 1],
               c='yellow', s=200, marker='X', label='Centroids')

    ax.set_title("Clustering vs Prolog Symbolic Grouping (PCA 2D)")
    ax.set_xlabel("Component 1")
    ax.set_ylabel("Component 2")
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plot_data = base64.b64encode(buf.read()).decode()
    plt.close(fig)

    # Comparison table
    table = []
    for i, r in enumerate(rows):
        table.append([r[0], Y[i], cluster_labels[i]])

    table_html = tabulate(
        table,
        headers=["Driver", "Symbolic Group", "Cluster ID"],
        tablefmt="html"
    )

    html = f"""
    <h2>Clustering Analysis — Traffic Rule Violation Checker</h2>

    <p><strong>Algorithm:</strong> K-Means (k={n_clusters})</p>
    <p><strong>Silhouette Score:</strong> {sil:.4f}</p>
    <p><strong>Davies-Bouldin Index:</strong> {db:.4f}</p>
    <p><strong>Adjusted Rand Index (vs symbolic):</strong> {ari:.4f}</p>
    <p><strong>Normalized Mutual Info (vs symbolic):</strong> {nmi:.4f}</p>

    <h3>Cluster Visualization</h3>
    <img src="data:image/png;base64,{plot_data}" />

    <h3>Comparison Table</h3>
    {table_html}

    <br><br>
    <a href="/" style="font-size:18px;">⬅ Back</a>
    """

    return html

# ===== Reinforcement Learning (Q-Learning) Integration for Traffic Project =====
import numpy as np
import random
import matplotlib.pyplot as plt
import io, base64
from collections import defaultdict
from statistics import mean

# Q-Learning hyperparameters (tune if needed)
Q_ALPHA = 0.6        # learning rate
Q_GAMMA = 0.95       # discount factor
Q_EPS_START = 1.0    # exploration start
Q_EPS_END = 0.05     # exploration end
Q_EPS_DECAY = 0.995  # per-episode decay
NUM_EPISODES = 800   # number of episodes to train
STEPS_PER_EP = 1     # steps per episode (state is instantaneous here)

# Actions
A_STOP = 0
A_GO = 1
ACTIONS = [A_STOP, A_GO]

def _state_tuple_from_driver(driver_atom):
    """
    Extract a discrete state tuple for a driver from Prolog:
    - signal: 0=red, 1=green
    - stopped: 0=no, 1=yes
    - overspeed: 0=no, 1=yes (speed > limit)
    """
    # default
    signal = 0
    stopped = 0
    overspeed = 0

    # stopped_at(driver, junction, yes/no)
    r = list(prolog.query(f"stopped_at({driver_atom}, J, S)"))
    if r:
        stopped = 1 if str(r[0]["S"]) == "yes" else 0
        junction = r[0]["J"]
        # check signal at that junction
        r2 = list(prolog.query(f"signal({junction}, C)"))
        if r2:
            signal = 1 if str(r2[0]["C"]) == "green" else 0
        # speed limit
        r3 = list(prolog.query(f"speed_limit({junction}, L)"))
        limit = int(r3[0]["L"]) if r3 else 0
    else:
        # if no stopped_at, try to probe a junction for speed_limit and signal
        junction = None
        limit = 0

    # driver speed
    r4 = list(prolog.query(f"speed({driver_atom}, SP)"))
    speed = int(r4[0]["SP"]) if r4 else 0

    if limit > 0 and speed > limit:
        overspeed = 1
    else:
        overspeed = 0

    return (signal, stopped, overspeed)


def symbolic_decision(driver_atom):
    """
    A simple Prolog-style symbolic policy:
    - If signal is red -> STOP
    - If signal is green -> GO
    - If overspeed -> STOP (symbolic safety)
    """
    s, stopped, overspeed = _state_tuple_from_driver(driver_atom)
    if overspeed == 1:
        return A_STOP
    if s == 0:  # red
        return A_STOP
    return A_GO


def reward_fn(state_tuple, action):
    """
    Reward design:
    - If action==GO on red -> big negative (-10)
    - If action==STOP on red -> positive (+5)
    - If action==GO on green -> positive (+5)
    - If action==STOP on green -> small negative (-1)
    - If overspeed and action==GO -> additional negative (-5)
    - This reward encourages obeying signals and avoiding overspeeding while keeping simple dynamics.
    """
    signal, stopped, overspeed = state_tuple
    r = 0
    if signal == 0:  # red
        if action == A_GO:
            r -= 10
        else:
            r += 5
    else:  # green
        if action == A_GO:
            r += 5
        else:
            r -= 1
    if overspeed == 1 and action == A_GO:
        r -= 5
    return r


def encode_state(state_tuple):
    """Map state tuple to an integer index for Q table"""
    # each element small: signal {0,1}, stopped {0,1}, overspeed {0,1} => 8 states
    signal, stopped, overspeed = state_tuple
    return signal * 4 + stopped * 2 + overspeed


@app.route("/reinforcement")
def reinforcement_module():
    """
    Train a Q-Learning agent based on current Prolog facts and compare with symbolic Prolog policy.
    Returns an HTML page with training curve, table of per-driver comparison, and summary metrics.
    """
    init_rules_once()

    # gather drivers
    res = list(prolog.query("list_all_drivers(L)"))
    if not res or not res[0].get("L"):
        return "<h3>No drivers available. Add driver facts (Persist Facts = Yes) then try again.</h3>"

    drivers = res[0]["L"]
    num_drivers = len(drivers)

    # Build state set (drivers can be used to sample states)
    driver_states = {d: _state_tuple_from_driver(d) for d in drivers}

    # Initialize Q-table: shape (n_states=8, n_actions=2)
    n_states = 8
    n_actions = len(ACTIONS)
    Q = np.zeros((n_states, n_actions), dtype=float)

    eps = Q_EPS_START
    avg_rewards_per_episode = []

    # Training loop
    for ep in range(NUM_EPISODES):
        # sample a driver randomly to produce a starting state
        total_reward = 0.0
        for step in range(STEPS_PER_EP):
            d = random.choice(drivers)
            state_tuple = driver_states[d]
            s_idx = encode_state(state_tuple)
            # epsilon-greedy
            if random.random() < eps:
                action = random.choice(ACTIONS)
            else:
                action = int(np.argmax(Q[s_idx]))
            # reward
            r = reward_fn(state_tuple, action)
            total_reward += r
            # For simplicity: next state is same (stateless short episodes)
            ns_idx = s_idx
            # Q-update
            best_next = np.max(Q[ns_idx])
            Q[s_idx, action] = Q[s_idx, action] + Q_ALPHA * (r + Q_GAMMA * best_next - Q[s_idx, action])

        # decay eps
        eps = max(Q_EPS_END, eps * Q_EPS_DECAY)
        avg_rewards_per_episode.append(total_reward)

    # Post-training: compute policy
    policy = {s: int(np.argmax(Q[s])) for s in range(n_states)}

    # Evaluate on drivers: collect Q-agent action vs symbolic decision
    driver_results = []
    q_actions = []
    sym_actions = []
    agreement_count = 0
    rewards = []
    for d in drivers:
        state_tuple = driver_states[d]
        s_idx = encode_state(state_tuple)
        q_act = policy[s_idx]
        sym_act = symbolic_decision(d)
        driver_results.append([d, state_tuple, ("STOP" if q_act == A_STOP else "GO"), ("STOP" if sym_act == A_STOP else "GO")])
        q_actions.append(q_act)
        sym_actions.append(sym_act)
        if q_act == sym_act:
            agreement_count += 1
        rewards.append(reward_fn(state_tuple, q_act))

    agreement_rate = agreement_count / len(drivers)
    avg_reward = mean(avg_rewards_per_episode[-50:]) if len(avg_rewards_per_episode) >= 1 else mean(avg_rewards_per_episode)

    # Make training plot
    fig, ax = plt.subplots(figsize=(7,3.5))
    ax.plot(np.convolve(avg_rewards_per_episode, np.ones(20)/20, mode='valid'))
    ax.set_title("Q-Learning: Smoothed Episode Rewards (window=20)")
    ax.set_xlabel("Episode (smoothed)")
    ax.set_ylabel("Total Reward")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_data = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    # build comparison table html
    table_rows = []
    for row in driver_results:
        driver_name = str(row[0]).replace("_", " ").title()
        st = f"signal={row[1][0]}, stopped={row[1][1]}, overspeed={row[1][2]}"
        q_act = row[2]
        sym_act = row[3]
        table_rows.append([driver_name, st, q_act, sym_act])

    table_html = "<table class='table table-striped'><thead><tr><th>Driver</th><th>State</th><th>Q-Agent</th><th>Symbolic</th></tr></thead><tbody>"
    for r in table_rows:
        table_html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"
    table_html += "</tbody></table>"

    html = f"""
    <div style="font-family:Inter, Arial, sans-serif; padding:18px; max-width:1100px; margin:18px auto;">
      <h2>Reinforcement Learning (Q-Learning) Report</h2>
      <p><strong>Episodes:</strong> {NUM_EPISODES} &nbsp; <strong>Alpha:</strong> {Q_ALPHA} &nbsp; <strong>Gamma:</strong> {Q_GAMMA}</p>
      <h4>Training Curve</h4>
      <img src="data:image/png;base64,{img_data}" style="max-width:100%;" />
      <h4>Evaluation Summary</h4>
      <ul>
        <li><strong>Drivers evaluated:</strong> {len(drivers)}</li>
        <li><strong>Agreement rate (Q vs Symbolic):</strong> {agreement_rate:.3f}</li>
        <li><strong>Average recent episode reward (smoothed):</strong> {avg_reward:.3f}</li>
        <li><strong>Average per-driver Q-action reward:</strong> {round(mean(rewards),3)}</li>
      </ul>

      <h4>Per-driver action comparison</h4>
      {table_html}
      <br><a href="/" style="font-size:16px;">⬅ Back</a>
    </div>
    """
    return html


if __name__ == "__main__":
    app.run(debug=True)
