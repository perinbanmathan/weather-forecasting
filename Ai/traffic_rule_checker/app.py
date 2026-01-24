from flask import Flask, render_template, request
from pyswip import Prolog

app = Flask(__name__)

def setup_prolog():
    prolog = Prolog()

    #Base Rules
    prolog.assertz("violated_helmet_rule(D) :- wears_helmet(D, no)")
    prolog.assertz("violated_signal_rule(D, J) :- signal(J, red), stopped_at(D, J, no)")
    prolog.assertz("violated_speed_rule(D, J) :- speed(D, S), speed_limit(J, L), S > L")

    #Backtracking: Multiple choices for violation/2 
    prolog.assertz("violation(D, 'Helmet Rule Violation') :- violated_helmet_rule(D)")
    prolog.assertz("violation(D, 'Signal Rule Violation') :- violated_signal_rule(D, _)")
    prolog.assertz("violation(D, 'Speed Limit Violation') :- violated_speed_rule(D, _)")

    #Recursion: Collect all violations into a list
    prolog.assertz("all_violations(D, [V|Rest]) :- violation(D, V), retract(violation(D, V)), all_violations(D, Rest)")
    prolog.assertz("all_violations(_, [])")

    return prolog


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        driver = request.form["driver"]
        wears_helmet = request.form["helmet"]
        junction = request.form["junction"]
        signal_color = request.form["signal"]
        stopped = request.form["stopped"]
        speed = int(request.form["speed"])
        speed_limit = int(request.form["speed_limit"])

        # Setup Prolog
        prolog = setup_prolog()

        # Insert facts
        prolog.assertz(f"wears_helmet({driver}, {wears_helmet})")
        prolog.assertz(f"signal({junction}, {signal_color})")
        prolog.assertz(f"stopped_at({driver}, {junction}, {stopped})")
        prolog.assertz(f"speed({driver}, {speed})")
        prolog.assertz(f"speed_limit({junction}, {speed_limit})")

        #Backtracking: collect violations one by one
        violations = []
        for result in prolog.query(f"violation({driver}, V)"):
            violations.append(result["V"])

        #Recursion: if you want to collect as a list directly
        if not violations:
            for result in prolog.query(f"all_violations({driver}, L)"):
                violations = result["L"]

        if not violations:
            violations.append("No Violations ✅")

        return render_template("result.html", driver=driver, violations=violations)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
