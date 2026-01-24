from flask import Flask, render_template, request
from pyswip import Prolog
import heapq

app = Flask(__name__)
prolog = Prolog()

# -----------------------
# Prolog Facts & Rules
# -----------------------
prolog.assertz("violation(helmet, 'No Helmet', 500, 3)")
prolog.assertz("violation(signal, 'Signal Jump', 1000, 4)")
prolog.assertz("violation(speed, 'Over Speed', 1500, 5)")
prolog.assertz("violation(drunk, 'Drunk Driving', 5000, 8)")

prolog.assertz("driver(mathan, [helmet, speed])")
prolog.assertz("driver(arun, [signal, drunk])")
prolog.assertz("driver(kumar, [speed])")

# -----------------------
# A* Algorithm
# -----------------------
def a_star(violations):
    """
    Rank violations by fine + heuristic(priority).
    g(n) = fine, h(n) = priority weight
    """
    ranked = []
    for v in violations:
        q = list(prolog.query(f"violation({v}, Name, Fine, Priority)"))
        if q:
            data = q[0]
            g = data["Fine"]
            h = data["Priority"]
            f = g + h
            heapq.heappush(ranked, (-f, data))  # max-heap
    result = [heapq.heappop(ranked)[1] for _ in range(len(ranked))]
    return result

# -----------------------
# AO* Algorithm
# -----------------------
def ao_star(violations):
    """
    Handle AND/OR dependencies.
    Example: drunk driving + overspeed => major violation combo.
    """
    results = []
    if "drunk" in violations and "speed" in violations:
        results.append({
            "Name": "Drunk + Overspeed (Major Offense)",
            "Fine": 7000,
            "Priority": 10
        })
        violations = [v for v in violations if v not in ["drunk", "speed"]]

    for v in violations:
        q = list(prolog.query(f"violation({v}, Name, Fine, Priority)"))
        if q:
            results.append(q[0])
    return results

# -----------------------
# Flask Routes
# -----------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check", methods=["POST"])
def check():
    driver = request.form.get("driver").lower().strip()
    violations = []
    for q in prolog.query(f"driver({driver}, V)"):
        violations = q["V"]

    if not violations:
        return render_template("result.html", driver=driver, violations=[], ranked=[], ao=[])

    ranked = a_star(violations)
    ao = ao_star(violations)

    return render_template("result.html", driver=driver, violations=violations, ranked=ranked, ao=ao)

if __name__ == "__main__":
    app.run(debug=True)
