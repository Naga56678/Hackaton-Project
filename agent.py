import os
import requests
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import chromadb
from dotenv import load_dotenv

# =========================
# Load Environment
# =========================
load_dotenv()

CHROMA_PATH   = os.getenv("CHROMA_PATH", "chroma_db")
OLLAMA_API    = os.getenv("OLLAMA_API", "http://127.0.0.1:11434/api/generate")
MODEL         = os.getenv("OLLAMA_MODEL", "llama3:latest")
OPENWEATHER   = os.getenv("OPENWEATHER_API_KEY")
WEATHER_URL   = "https://api.openweathermap.org/data/2.5/forecast"

# =========================
# Database & Accounts
# =========================
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection("travel")

customer_accounts = {
    "User001": {"name": "Madeven Payanee", "balance": 10000.0},
}


# =========================
# Weather Helpers
# =========================
def _daily_buckets(list3h):
    """Group 3-hour forecast data into daily buckets."""
    daily = {}
    for row in list3h:
        d = row["dt_txt"].split(" ")[0]
        daily.setdefault(d, []).append(row)
    return daily


def check_weather_by_dates(location="Mauritius", start_date=None, end_date=None):
    """
    Fetch weather forecast from OpenWeather and filter between dates.
    Returns (forecast dict, alternative_dates tip).
    """
    if not OPENWEATHER:
        return {"error": "Missing OPENWEATHER_API_KEY in .env"}, None

    try:
        params = {"q": location, "appid": OPENWEATHER, "units": "metric"}
        resp = requests.get(WEATHER_URL, params=params, timeout=20).json()
    except Exception as e:
        return {"error": f"Weather API request failed: {e}"}, None

    if "list" not in resp:
        return {"error": resp.get("message", "Invalid weather response")}, None

    daily = _daily_buckets(resp["list"])
    forecast, rainy_days = {}, 0

    for day, items in daily.items():
        if start_date and end_date and not (start_date <= day <= end_date):
            continue

        temps = [x["main"]["temp"] for x in items]
        conds = [x["weather"][0]["main"].lower() for x in items]

        avg_temp = round(sum(temps) / len(temps), 1)
        rain_like = any(c in ["rain", "storm", "thunderstorm", "drizzle"] for c in conds)

        if rain_like:
            cond = "Rainy"
            advice = "Plan indoor experiences ☔"
        elif any(c in ["clear", "clouds"] for c in conds):
            cond = "Clear/Clouds"
            advice = "Great for outdoor activities 🌞"
        else:
            cond = items[0]["weather"][0]["main"]
            advice = "Enjoy your day!"

        forecast[day] = {
            "condition": cond,
            "avg_temp": avg_temp,
            "advice": advice,
            "outdoor": not rain_like
        }

        if rain_like:
            rainy_days += 1

    # Suggest alternative months if too rainy
    alt = None
    n = len(forecast)
    if n and rainy_days >= 0.6 * n:
        alt = (
            "🌤️ Consider April–May or September–November for steadier skies, "
            "warm seas (≈24–27°C), and fewer cyclones."
        )

    return forecast, alt


# =========================
# LLM Agent
# =========================
def llm_complete(prompt: str) -> str:
    """Send a prompt to Ollama LLM and return the response."""
    try:
        r = requests.post(
            OLLAMA_API,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json().get("response", "").strip()
        return f"LLM error: {r.text}"
    except Exception:
        return "Planner currently unavailable. Please try again."


def ask_agent(query, num_persons=1, start_date=None, end_date=None):
    """Generate a travel plan using local DB + weather + LLM."""
    weather, alt_dates = check_weather_by_dates(
        start_date=start_date, end_date=end_date
    )

    results = collection.query(query_texts=[query], n_results=3)
    docs = " ".join(results.get("documents", [[]])[0])

    # Weather summary
    if isinstance(weather, dict) and "error" not in weather:
        wsum = "\n".join(
            [f"- {d}: {v['condition']} {v['avg_temp']}°C — {v['advice']}"
             for d, v in weather.items()]
        )
    else:
        wsum = str(weather)

    prompt = f"""
You are a Mauritius travel assistant.

User request: {query}
Travellers: {num_persons}
Dates: {start_date} → {end_date}

Local knowledge:
{docs}

Weather on selected dates:
{wsum}

Write a clear markdown itinerary by Day (morning/afternoon/evening).
- Prefer outdoor items on good days; switch to indoor on rainy days.
- Recommend 1–2 hotels with prices in MUR (ballpark).
- Keep hotel and dates consistent for checkout later.
- Close with a budget summary in MUR.
"""
    text = llm_complete(prompt)

    # Demo placeholder (can be parsed from LLM in future)
    hotel = "Hotel XYZ"
    cost = 8000.0

    return {
        "response": text,
        "weather": weather,
        "alternative_dates": alt_dates,
        "hotel": hotel,
        "cost": cost,
    }


# =========================
# Checkout & PDF
# =========================
def silent_checkout(user_id, booking_id, hotel_name, cost, checkout_date):
    """Simulate a silent checkout transaction."""
    acc = customer_accounts.get(user_id)
    if not acc:
        return {"status": "error", "message": "User not found"}
    if acc["balance"] < cost:
        return {"status": "error", "message": "Insufficient funds"}

    acc["balance"] -= cost
    when = (datetime.now() + timedelta(minutes=2)).strftime("%H:%M:%S")

    return {
        "status": "success",
        "message": (
            f"Silent checkout scheduled for {hotel_name} on {checkout_date}. "
            f"Charged MUR {cost}. Remaining balance: MUR {acc['balance']:.2f}. "
            f"Expected completion: {when}"
        ),
    }


def create_pdf(plan: dict, filename="trip.pdf"):
    """Create a simple PDF summary of the itinerary."""
    c = canvas.Canvas(filename, pagesize=letter)
    W, H = letter
    y = H - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(60, y, "Mauritius Travel Plan")
    y -= 30

    c.setFont("Helvetica", 11)
    for line in plan.get("response", "(no plan)").splitlines():
        if not line.strip():
            y -= 8
            continue
        if y < 60:
            c.showPage()
            y = H - 50
            c.setFont("Helvetica", 11)
        c.drawString(60, y, line[:100])
        y -= 16

    c.save()
    return filename
