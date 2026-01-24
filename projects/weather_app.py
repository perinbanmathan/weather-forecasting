import streamlit as st
import requests
from datetime import datetime
import base64

# ================= CONFIG =================
API_KEY = "8b47e9701e521d68cba0b94c8b5dd3ac"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

st.set_page_config(
    page_title="Weather Forecast",
    page_icon="🌦️",
    layout="centered"
)

def add_bg_image(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
# ================= MAC-STYLE CSS =================
st.markdown("""
<style>
            
    body {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    }
    .glass {
        background: rgba(20, 25, 35, 0.75);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border-radius: 20px;
    padding: 28px;
    margin-top: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.08);
    }
    .title {
        font-size: 40px;
        font-weight: 700;
        text-align: center;
        color: black;
    }
    .subtitle {
        text-align: center;
        color: yellow;
        margin-bottom: 25px;
    }
    .metric-label {
        color: #9ca3af;
        font-size: 14px;
    }
    .metric-value {
        color: white;
        font-size: 32px;
        font-weight: 600;
    }
            .title, .subtitle {
    text-shadow: 0 3px 10px rgba(0,0,0,0.6);
}
input {
    background-color: rgba(30, 30, 40, 0.85) !important;
    color: white !important;
}

button {
    background-color: rgba(20, 25, 35, 0.9) !important;
    color: white !important;
    border-radius: 10px !important;
}

</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Weather Forecast", page_icon="🌦️")

add_bg_image("background.jpg")  

# ================= HEADER =================
st.markdown("<div class='title'>🌦️ Weather Forecast Application</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Real-time weather </div>", unsafe_allow_html=True)

# ================= INPUT =================
city = st.text_input("Enter City Name", placeholder="Eg: Chennai, London, Tokyo")

# ================= BUTTON =================
if st.button("Get Weather"):
    if city.strip() == "":
        st.warning("⚠️ Please enter a city name")
    else:
        try:
            params = {
                "q": city,
                "appid": API_KEY,
                "units": "metric"
            }

            response = requests.get(BASE_URL, params=params, timeout=5)

            if response.status_code != 200:
                st.error("❌ City not found. Please try again.")
            else:
                data = response.json()

                # ================= DATA =================
                name = data["name"]
                country = data["sys"]["country"]
                temp = data["main"]["temp"]
                feels = data["main"]["feels_like"]
                humidity = data["main"]["humidity"]
                pressure = data["main"]["pressure"]
                wind = data["wind"]["speed"]
                condition = data["weather"][0]["description"].title()
                main_condition = data["weather"][0]["main"]
                icon = data["weather"][0]["icon"]
                time = datetime.fromtimestamp(data["dt"])

                icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png"

                # ================= UI CARD =================
                st.markdown("<div class='glass'>", unsafe_allow_html=True)

                st.success(f"📍 {name}, {country}")
                st.caption(f"🕒 Last updated: {time}")

                st.image(icon_url, width=110)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("<div class='metric-label'>🌡️ Temperature</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{temp} °C</div>", unsafe_allow_html=True)

                    st.markdown("<div class='metric-label'>💧 Humidity</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{humidity} %</div>", unsafe_allow_html=True)

                with col2:
                    st.markdown("<div class='metric-label'>🤒 Feels Like</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{feels} °C</div>", unsafe_allow_html=True)

                    st.markdown("<div class='metric-label'>💨 Wind Speed</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{wind} m/s</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.info(f"☁️ Condition: {main_condition} – {condition}")
                st.write(f"📊 Atmospheric Pressure: **{pressure} hPa**")

                st.markdown("</div>", unsafe_allow_html=True)

        except requests.exceptions.Timeout:
            st.error("⏳ Request timed out. Check your internet.")
        except requests.exceptions.ConnectionError:
            st.error("🌐 Network error.")
        except Exception as e:
            st.error(f"⚠️ Error: {e}")
