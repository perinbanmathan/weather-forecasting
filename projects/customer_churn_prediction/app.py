import streamlit as st
import joblib
import numpy as np

# Load trained model
model = joblib.load("model/churn_model.pkl")

st.set_page_config(page_title="Customer Churn Predictor", layout="centered")

st.title("📉 Customer Churn Prediction App")
st.write("Enter customer details to predict churn")

st.divider()

# User inputs
tenure = st.slider("Tenure (months)", 0, 72, 12)
monthly_charges = st.number_input("Monthly Charges", min_value=0.0)
total_charges = st.number_input("Total Charges", min_value=0.0)

if st.button("Predict Churn"):
    input_data = np.array([[tenure, monthly_charges, total_charges]])
    prediction = model.predict(input_data)

    if prediction[0] == 1:
        st.error("❌ Customer is likely to CHURN")
    else:
        st.success("✅ Customer is likely to STAY")
