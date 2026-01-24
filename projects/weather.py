import requests

API_KEY = "8b47e9701e521d68cba0b94c8b5dd3ac"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_weather(city):
    try:
        params = {
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }

        response = requests.get(BASE_URL, params=params, timeout=5)

        if response.status_code != 200:
            print("❌ City not found. Please check the city name.")
            return

        data = response.json()

        print("\n🌦️ Weather Report")
        print("------------------------")
        print(f"City        : {data['name']}")
        print(f"Temperature : {data['main']['temp']} °C")
        print(f"Feels Like  : {data['main']['feels_like']} °C")
        print(f"Humidity    : {data['main']['humidity']} %")
        print(f"Pressure    : {data['main']['pressure']} hPa")
        print(f"Condition   : {data['weather'][0]['description'].title()}")
        print(f"Wind Speed  : {data['wind']['speed']} m/s")

    except requests.exceptions.Timeout:
        print("⏳ Request timed out. Check your internet.")
    except requests.exceptions.ConnectionError:
        print("🌐 Network error. Please connect to internet.")
    except Exception as e:
        print("⚠️ Something went wrong:", e)

city = input("Enter city name: ")
get_weather(city)
