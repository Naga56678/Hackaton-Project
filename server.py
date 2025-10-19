# backend/server.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =========================
# FastAPI App Setup
# =========================
app = FastAPI()

# Allow frontend to call backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Later restrict to ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Ping Route (Health Check)
# =========================
@app.get("/ping")
async def ping():
    return {"message": "pong from FastAPI"}

# =========================
# Booking API
# =========================
class BookingRequest(BaseModel):
    room: str
    check_in: str
    check_out: str

@app.post("/check_availability")
async def check_availability(data: BookingRequest):
    return {
        "message": f"✅ {data.room} is available from {data.check_in} to {data.check_out}",
        "weather": "Sunny, 28°C",
        "plan": "Day 1: Arrival & Spa | Day 2: Beach Tour | Day 3: Silent Checkout"
    }

# =========================
# Checkout API
# =========================
class CheckoutRequest(BaseModel):
    room: str
    check_in: str
    check_out: str

@app.post("/checkout")
async def checkout(data: CheckoutRequest):
    return {
        "success": True,
        "message": f"🎉 Booking confirmed for {data.room} from {data.check_in} to {data.check_out}",
        "pdf_url": "/itinerary.pdf"  # later we can generate and return a real PDF
    }
