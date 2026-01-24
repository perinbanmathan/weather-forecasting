# ml-service/app.py
from flask import Flask, request, jsonify
import pandas as pd, io, base64
import joblib, os
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.cluster import KMeans
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, silhouette_score, davies_bouldin_score
import matplotlib.pyplot as plt
import numpy as np
import requests

app = Flask(__name__)

PROLOG_URL = "http://prolog-service:5001"

def fetch_dataset():
    r = requests.get(f"{PROLOG_URL}/export_dataset")
    if r.status_code != 200:
        return pd.DataFrame()
    return pd.read_csv(io.BytesIO(r.content))

@app.route("/train_classifiers", methods=["POST"])
def train_classifiers():
    df = fetch_dataset()
    if df.empty:
        return jsonify({"error":"empty dataset"}), 400

    le_h = LabelEncoder(); le_s = LabelEncoder(); le_st = LabelEncoder()
    df["helmet_enc"] = le_h.fit_transform(df["helmet"].astype(str))
    df["signal_enc"] = le_s.fit_transform(df["signal"].astype(str))
    df["stopped_enc"] = le_st.fit_transform(df["stopped"].astype(str))

    X = df[["helmet_enc","signal_enc","stopped_enc","speed","limit"]]
    y = (df["viol_count"] > 0).astype(int)

    models = {
        "DecisionTree": DecisionTreeClassifier(),
        "KNN": KNeighborsClassifier(n_neighbors=3),
        "Logistic": LogisticRegression(max_iter=200)
    }

    trained = {}
    for name, m in models.items():
        m.fit(X, y)
        trained[name] = m

    joblib.dump({"models":trained, "le_h":le_h, "le_s":le_s, "le_st":le_st}, "ml_models.joblib")
    return jsonify({"ok": True, "n": len(df)})

@app.route("/classify", methods=["POST"])
def classify_route():
    data = request.json or {}
    helmet = data.get("helmet","no")
    signal = data.get("signal","red")
    stopped = data.get("stopped","no")
    speed = int(data.get("speed",0))
    limit = int(data.get("limit",0))

    if not os.path.exists("ml_models.joblib"):
        return jsonify({"error":"models not trained yet (POST /train_classifiers)"}), 400
    obj = joblib.load("ml_models.joblib")
    models = obj["models"]

    h = 1 if str(helmet).lower()=="yes" else 0
    s = 1 if str(signal).lower()=="green" else 0
    st = 1 if str(stopped).lower()=="yes" else 0
    X = np.array([[h,s,st,speed,limit]])

    preds = {}
    for name, m in models.items():
        try:
            preds[name] = int(m.predict(X)[0])
        except Exception as e:
            preds[name] = str(e)
    return jsonify({"predictions": preds})

@app.route("/regression", methods=["GET"])
def regression_route():
    df = fetch_dataset()
    if df.empty:
        return jsonify({"error":"empty dataset"}), 400
    X = df[["helmet","signal","stopped","speed","limit"]].copy()
    X["helmet"] = (X["helmet"]=="yes").astype(int)
    X["signal"] = (X["signal"]=="green").astype(int)
    X["stopped"] = (X["stopped"]=="yes").astype(int)
    y = df["a_star_score"].fillna(0)

    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)

    mse = mean_squared_error(y, y_pred)
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)

    fig, ax = plt.subplots()
    ax.scatter(y, y_pred, alpha=0.6)
    ax.set_xlabel("Prolog Score")
    ax.set_ylabel("Predicted")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode()
    return jsonify({"mse": float(mse), "mae": float(mae), "r2": float(r2), "plot": img_b64})

@app.route("/clustering", methods=["GET"])
def clustering_route():
    df = fetch_dataset()
    if df.empty:
        return jsonify({"error":"empty dataset"}), 400
    X = df[["helmet","signal","stopped","speed","limit"]].copy()
    X["helmet"] = (X["helmet"]=="yes").astype(int)
    X["signal"] = (X["signal"]=="green").astype(int)
    X["stopped"] = (X["stopped"]=="yes").astype(int)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    if len(Xs) < 3:
        return jsonify({"error":"Need at least 3 drivers to cluster"}), 400

    kmeans = KMeans(n_clusters=3, random_state=42)
    labels = kmeans.fit_predict(Xs)

    sil = float(silhouette_score(Xs, labels))
    db = float(davies_bouldin_score(Xs, labels))

    res = df[["driver"]].copy()
    res["cluster"] = labels
    return jsonify({"metrics":{"silhouette": sil, "davies_bouldin": db}, "clusters": res.to_dict(orient="records")})

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
