import streamlit as st
import random
import sqlite3
from datetime import datetime
from agent import ask_agent, create_pdf, silent_checkout, customer_accounts

# =============================
# Database Setup (Rooms & Bookings)
# =============================
def init_db():
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            hotel_name TEXT,
            room_type TEXT,
            check_in TEXT,
            check_out TEXT,
            cost REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_booking(user_id, hotel, room, check_in, check_out, cost):
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute("INSERT INTO bookings (user_id, hotel_name, room_type, check_in, check_out, cost, status) VALUES (?,?,?,?,?,?,?)",
              (user_id, hotel, room, check_in, check_out, cost, "BOOKED"))
    conn.commit()
    conn.close()

def get_bookings(user_id):
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute("SELECT id, hotel_name, room_type, check_in, check_out, cost, status FROM bookings WHERE user_id=? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_booking_status(booking_id, status):
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute("UPDATE bookings SET status=? WHERE id=?", (status, booking_id))
    conn.commit()
    conn.close()

# Initialize database
init_db()

# =============================
# Page Config
# =============================
st.set_page_config(
    page_title="Smart Travel Companion – Mauritius",
    page_icon="🌴",
    layout="wide"
)

st.title("🌴 Smart Travel Companion – Mauritius")

# =============================
# Sidebar: Customer Account
# =============================
st.sidebar.header("👤 Customer Account")

if "user_id" not in st.session_state:
    st.session_state["user_id"] = random.choice(list(customer_accounts.keys()))

user_id = st.sidebar.selectbox(
    "Select Account",
    list(customer_accounts.keys()),
    index=list(customer_accounts.keys()).index(st.session_state["user_id"]),
    key="account_select"
)
st.session_state["user_id"] = user_id

st.sidebar.write(f"**Name:** {customer_accounts[user_id]['name']}")
st.sidebar.write(f"**Balance:** MUR {customer_accounts[user_id]['balance']:.2f}")

# =============================
# Trip Planner
# =============================
st.header("🗺️ Trip Planner")
query = st.text_input("Enter your travel request:")
num_persons = st.number_input("Number of persons", min_value=1, step=1, value=2)
start_date = st.date_input("Check-in Date")
end_date = st.date_input("Check-out Date")

if st.button("Generate Plan") and query.strip():
    data = ask_agent(
        query,
        num_persons=num_persons,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    st.subheader("📋 Your Travel Plan")

    if "error" in data:
        st.error(f"Error: {data['error']}")
    else:
        st.markdown(data.get("response", "No response generated"))

        if "weather" in data and isinstance(data["weather"], dict):
            st.write("### 🌦️ Weather Forecast")
            for date, info in data["weather"].items():
                if isinstance(info, dict):
                    icon = "✅" if info.get("outdoor", False) else "☔"
                    st.write(f"**{date}**: {icon} {info.get('condition','')} — {info.get('advice','')}")

        if data.get("alternative_dates"):
            st.warning(data["alternative_dates"])

        create_pdf(data, "trip.pdf")
        with open("trip.pdf", "rb") as f:
            st.download_button("📥 Download Trip PDF", f, "trip.pdf")

        st.session_state["latest_trip"] = data

# =============================
# Room Booking System
# =============================
st.header("🏨 Hotel Room Booking")

if "latest_trip" in st.session_state:
    trip = st.session_state["latest_trip"]
    hotel_name = trip.get("hotel", "Hotel XYZ")
    cost = trip.get("cost", 8000)

    room_type = st.selectbox("Select Room Type", ["Standard", "Deluxe", "Suite"])
    if st.button("Book Room"):
        add_booking(user_id, hotel_name, room_type, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), cost)
        st.success(f"✅ Room booked at {hotel_name} ({room_type}) for MUR {cost:.2f}")

# Show bookings
st.subheader("📜 Your Bookings")
bookings = get_bookings(user_id)
if bookings:
    for bid, hotel, room, check_in, check_out, cost, status in bookings:
        st.write(f"**{hotel} ({room})** | {check_in} → {check_out} | MUR {cost:.2f} | Status: {status}")
else:
    st.info("No bookings yet.")

# =============================
# Silent Checkout
# =============================
st.subheader("Silent Hotel Checkout")
if st.button("Simulate Silent Checkout"):
    if not bookings:
        st.warning("⚠️ Please book a room first!")
    else:
        last_booking = bookings[0]  # most recent booking
        booking_id, hotel, room, check_in, check_out, cost, status = last_booking

        result = silent_checkout(
            user_id=user_id,
            booking_id=booking_id,
            hotel_name=hotel,
            cost=cost,
            checkout_date=end_date.strftime("%Y-%m-%d")
        )
        if result["status"] == "success":
            customer_accounts[user_id]["balance"] -= cost
            update_booking_status(booking_id, "CHECKED_OUT")
            st.success(result["message"])
            st.sidebar.write(f"**Balance:** MUR {customer_accounts[user_id]['balance']:.2f}")
        else:
            st.error(result["message"])

# =============================
# Floating Chatbot Assistant
# =============================
if "chat_visible" not in st.session_state:
    st.session_state["chat_visible"] = False

chat_toggle = st.button("💬 Toggle Travel Assistant (Popup)", key="chat_toggle")

if chat_toggle:
    st.session_state["chat_visible"] = not st.session_state["chat_visible"]

if st.session_state["chat_visible"]:
    with st.container():
        st.markdown("---")
        st.markdown("### 🤖 Your AI Travel Assistant")

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        for role, msg in st.session_state["chat_history"]:
            st.chat_message(role).write(msg)

        if prompt := st.chat_input("Ask me anything about Mauritius, hotels, or activities..."):
            st.chat_message("user").write(prompt)
            st.session_state["chat_history"].append(("user", prompt))

            reply = ask_agent(prompt, num_persons=1)
            response_text = reply.get("response", "I couldn’t find an answer, please try again.")

            st.chat_message("assistant").write(response_text)
            st.session_state["chat_history"].append(("assistant", response_text))
