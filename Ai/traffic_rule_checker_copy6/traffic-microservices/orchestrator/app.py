# orchestrator/app.py
from flask import Flask, request, jsonify, render_template
import requests, os

app = Flask(__name__, template_folder='templates', static_folder='static')

PROLOG = "http://prolog-service:5001"
ML = "http://ml-service:5002"
RL = "http://rl-service:5003"

def to_atom(s):
    return str(s).strip().lower().replace(" ", "_")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['GET','POST'])
def result():
    # simple proxy to existing result page - keep for local UI compatibility
    return render_template('result.html', mode='info', driver='', violations=['Use orchestrator API or form to populate results.'])

@app.route("/check_and_classify", methods=["POST"])
def check_and_classify():
    data = request.json or {}
    driver_raw = data.get("driver", "")
    junction_raw = data.get("junction", "")
    helmet = data.get("helmet", "no")
    signal = data.get("signal", "red")
    stopped = data.get("stopped", "no")
    speed = int(data.get("speed", 0))
    limit = int(data.get("limit", 0))
    persist = data.get("persist", "yes")

    driver = to_atom(driver_raw) if driver_raw else ""
    junction = to_atom(junction_raw) if junction_raw else ""

    if persist == "yes" and driver:
        requests.post(f"{PROLOG}/assert", json={"fact": f"wears_helmet({driver}, {helmet})"})
        requests.post(f"{PROLOG}/assert", json={"fact": f"speed({driver}, {speed})"})
        if junction:
            requests.post(f"{PROLOG}/assert", json={"fact": f"signal({junction}, {signal})"})
            requests.post(f"{PROLOG}/assert", json={"fact": f"stopped_at({driver}, {junction}, {stopped})"})
            requests.post(f"{PROLOG}/assert", json={"fact": f"speed_limit({junction}, {limit})"})

    pv = requests.get(f"{PROLOG}/violations/{driver}") if driver else None
    prolog_res = pv.json() if pv and pv.ok else {"violations": []}

    ml_payload = {"helmet": helmet, "signal": signal, "stopped": stopped, "speed": speed, "limit": limit}
    ml = requests.post(f"{ML}/classify", json=ml_payload)
    ml_res = ml.json() if ml.ok else {"error":"ml error"}

    rl = requests.post(f"{RL}/train_rl", json={"episodes":300})
    rl_res = rl.json() if rl.ok else {"error":"rl error"}

    return jsonify({"prolog": prolog_res, "ml": ml_res, "rl": rl_res})

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    # ensure templates exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(host="0.0.0.0", port=5000)
