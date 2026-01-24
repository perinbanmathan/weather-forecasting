from flask import Flask, render_template, request
from pyswip import Prolog

app = Flask(__name__)
prolog = Prolog()
prolog.consult("traffic.pl")  # contains the above Prolog KB

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/recursion", methods=["GET", "POST"])
def recursion():
    result = None
    driver_list = ""

    if request.method == "POST":
        driver_list = request.form.get("drivers_list", "").strip()

        # ✅ Add brackets if missing
        if driver_list and not driver_list.startswith("["):
            driver_list = f"[{driver_list}]"

        query = f"collect_violations({driver_list}, Results)"
        try:
            res = list(prolog.query(query))
            if res:
                result = res[0]["Results"]
        except Exception as e:
            result = f"Error: {str(e)}"

    return render_template("recursion.html", drivers=driver_list, result=result)

if __name__ == "__main__":
    app.run(debug=True)

