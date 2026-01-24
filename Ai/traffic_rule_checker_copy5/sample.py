import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# Dataset
data = {
    'Helmet': [0,1,0,0,1,1,0,0,1,0],
    'Signal': [0,0,1,0,0,1,0,0,0,1],
    'Stopped': [0,1,1,0,0,1,1,0,1,1],
    'Speed': [70,40,60,90,80,45,60,85,55,70],
    'Speed_Limit': [50,50,60,60,60,50,50,60,60,60]
}
df = pd.DataFrame(data)

# Normalize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df)

# Calculate WCSS for k=1 to k=10
wcss = []
for k in range(1, 11):
    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(X_scaled)
    wcss.append(kmeans.inertia_)

# Plot Elbow Method
plt.figure(figsize=(8,5))
plt.plot(range(1, 11), wcss, marker='o')
plt.title("Elbow Method for Optimal k")
plt.xlabel("Number of clusters (k)")
plt.ylabel("WCSS")
plt.xticks(range(1,11))
plt.grid(True)
plt.show()
