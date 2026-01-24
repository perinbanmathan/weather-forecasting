# rl-service/app.py
from flask import Flask, request, jsonify
import numpy as np, random, requests
from statistics import mean

app = Flask(__name__)
PROLOG_URL = "http://prolog-service:5001"

A_STOP=0; A_GO=1
ACTIONS=[A_STOP,A_GO]

def get_drivers():
    r = requests.get(f"{PROLOG_URL}/drivers")
    if not r.ok:
        return []
    return r.json().get("drivers", [])

def get_driver_state(driver):
    rv = requests.get(f"{PROLOG_URL}/violations/{driver}")
    viols = rv.json().get("violations", []) if rv.ok else []
    overspeed = 1 if any("Speed Limit Violation" in v for v in viols) else 0
    signal = 0
    stopped = 0
    return (signal, stopped, overspeed)

def encode_state(t):
    s, st, ov = t
    return s*4 + st*2 + ov

@app.route("/train_rl", methods=["POST"])
def train_rl():
    episodes = int(request.json.get("episodes", 500)) if request.json else 500
    alpha = float(request.json.get("alpha", 0.6)) if request.json else 0.6
    gamma = float(request.json.get("gamma", 0.95)) if request.json else 0.95

    drivers = get_drivers()
    if not drivers:
        return jsonify({"error":"no drivers"}), 400

    dstates = {d: get_driver_state(d) for d in drivers}

    Q = np.zeros((8,2))
    eps = 1.0
    rewards_hist = []

    def reward_fn(state, action):
        signal, stopped, overspeed = state
        r=0
        if signal==0:
            if action==A_GO:
                r -= 10
            else:
                r += 5
        else:
            if action==A_GO:
                r += 5
            else:
                r -= 1
        if overspeed and action==A_GO:
            r -= 5
        return r

    for ep in range(episodes):
        total = 0
        for _ in range(1):
            d = random.choice(drivers)
            s = dstates[d]
            si = encode_state(s)
            if random.random() < eps:
                a = random.choice(ACTIONS)
            else:
                a = int(np.argmax(Q[si]))
            rwd = reward_fn(s, a)
            total += rwd
            best_next = np.max(Q[si])
            Q[si, a] = Q[si, a] + alpha*(rwd + gamma*best_next - Q[si, a])
        eps = max(0.05, eps*0.995)
        rewards_hist.append(total)

    policy = {i:int(np.argmax(Q[i])) for i in range(8)}
    return jsonify({"policy": policy, "avg_last_50": float(np.mean(rewards_hist[-50:]) if len(rewards_hist)>=1 else np.mean(rewards_hist))})

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
