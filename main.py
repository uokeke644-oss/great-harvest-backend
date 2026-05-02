from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import uvicorn

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserTable(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------

app = FastAPI(title="Great Harvest API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static data — shaped to match api.ts interfaces exactly
# ---------------------------------------------------------------------------

# State interface: slug, name, tagline, propertyCount, image
STATES = [
    {
        "slug": "lagos",
        "name": "Lagos",
        "tagline": "Nigeria's commercial capital",
        "propertyCount": 1,
        "image": "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800",
    },
    {
        "slug": "kano",
        "name": "Kano",
        "tagline": "The ancient city of commerce",
        "propertyCount": 1,
        "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
    },
]

# Property interface:
#   id (string), title, state, location (string), price, pricePerPlot,
#   totalPlots, remainingPlots, coverImage, gallery (string[]),
#   coordinates: { lat, lng }, description, features (string[])
PROPERTIES = {
    "101": {
        "id": "101",
        "title": "Great Harvest Lagos Estate",
        "state": "lagos",
        "location": "Ibeju-Lekki, Lagos State",
        "price": 15000000,
        "pricePerPlot": 15000000,
        "totalPlots": 3,
        "remainingPlots": 3,
        "coverImage": "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800",
        "gallery": [
            "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800",
            "https://images.unsplash.com/photo-1507089947368-19c1da9775ae?w=800",
        ],
        "coordinates": {"lat": 6.4281, "lng": 3.4219},
        "description": "Premium plots in the heart of Lagos. A serene and well-planned estate with modern infrastructure and easy access to major roads.",
        "features": [
            "Perimeter fencing",
            "Gated community",
            "Good road network",
            "Electricity supply",
            "Water supply",
            "C of O title",
        ],
    },
    "201": {
        "id": "201",
        "title": "Great Harvest Kano Estate",
        "state": "kano",
        "location": "Kano Municipal, Kano State",
        "price": 6000000,
        "pricePerPlot": 6000000,
        "totalPlots": 3,
        "remainingPlots": 3,
        "coverImage": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
        "gallery": [
            "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=800",
            "https://images.unsplash.com/photo-1523217582562-09d0def993a6?w=800",
            "https://images.unsplash.com/photo-1480074568708-e7b720bb3f09?w=800",
        ],
        "coordinates": {"lat": 12.0022, "lng": 8.5920},
        "description": "Affordable prime plots in Kano. Strategically located with excellent road access and essential infrastructure already in place.",
        "features": [
            "Perimeter fencing",
            "Gated community",
            "Good road network",
            "Electricity supply",
            "Water supply",
            "C of O title",
        ],
    },
}

# Plot interface: id (string), label, row, col, status, price, size
PLOTS = {
    "101": {
        "plots": [
            {"id": "LG-001", "label": "A1", "row": 0, "col": 0, "status": "available", "price": 15000000, "size": "500 sqm"},
            {"id": "LG-002", "label": "A2", "row": 0, "col": 1, "status": "available", "price": 22000000, "size": "750 sqm"},
            {"id": "LG-003", "label": "A3", "row": 0, "col": 2, "status": "available", "price": 30000000, "size": "1000 sqm"},
        ],
        "remaining": 3,
        "total": 3,
    },
    "201": {
        "plots": [
            {"id": "KN-001", "label": "A1", "row": 0, "col": 0, "status": "available", "price": 6000000,  "size": "500 sqm"},
            {"id": "KN-002", "label": "A2", "row": 0, "col": 1, "status": "available", "price": 9000000,  "size": "750 sqm"},
            {"id": "KN-003", "label": "A3", "row": 0, "col": 2, "status": "available", "price": 12000000, "size": "1000 sqm"},
        ],
        "remaining": 3,
        "total": 3,
    },
}

# In-memory stores for bookings and investments (replace with DB tables in production)
BOOKINGS_STORE: list = []
INVESTMENTS_STORE: list = []


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    fullName: str
    email: str
    phone: Optional[str] = None
    password: str


class SigninRequest(BaseModel):
    email: str
    password: str


class BookingViewingRequest(BaseModel):
    propertyId: str
    date: str
    time: str
    name: str
    phone: str
    email: str


class BookingConsultationRequest(BaseModel):
    service: str
    name: str
    phone: str
    email: str
    notes: str


class PaymentRequest(BaseModel):
    plotId: Optional[str] = None
    amount: Optional[float] = None
    email: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/api/auth/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(UserTable).filter(UserTable.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    new_user = UserTable(
        name=payload.fullName,
        email=payload.email,
        password=payload.password,  # hash in production
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "token": f"mock-token-{new_user.id}",
        "user": {
            "id": str(new_user.id),
            "email": new_user.email,
            "fullName": new_user.name,
            "phone": None,
            "role": "user",
        },
    }


@app.post("/api/auth/signin")
def signin(payload: SigninRequest, db: Session = Depends(get_db)):
    user = db.query(UserTable).filter(UserTable.email == payload.email).first()
    if not user or user.password != payload.password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "token": f"mock-token-{user.id}",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "fullName": user.name,
            "phone": None,
            "role": "user",
        },
    }


@app.get("/api/auth/me")
def get_me():
    raise HTTPException(status_code=401, detail="Not authenticated.")


# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------

@app.get("/api/states")
def get_states():
    return STATES


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@app.get("/api/properties")
def list_properties(state: Optional[str] = None):
    props = list(PROPERTIES.values())
    if state:
        props = [p for p in props if p["state"].lower() == state.lower()]
    return props


@app.get("/api/properties/{property_id}")
def get_property(property_id: str):
    prop = PROPERTIES.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found.")
    return prop


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

@app.get("/api/properties/{property_id}/plots")
def get_plots(property_id: str):
    data = PLOTS.get(property_id)
    if not data:
        raise HTTPException(status_code=404, detail="Property not found.")
    return data


@app.post("/api/properties/{property_id}/plots/{plot_id}/reserve")
def reserve_plot(property_id: str, plot_id: str):
    data = PLOTS.get(property_id)
    if not data:
        raise HTTPException(status_code=404, detail="Property not found.")
    plot = next((p for p in data["plots"] if p["id"] == plot_id), None)
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found.")
    if plot["status"] != "available":
        raise HTTPException(status_code=409, detail="Plot is not available.")
    plot["status"] = "reserved"
    data["remaining"] = max(0, data["remaining"] - 1)
    return {"reservationId": f"RES-{property_id}-{plot_id}"}


# ---------------------------------------------------------------------------
# Booking routes
# ---------------------------------------------------------------------------

@app.post("/api/bookings/viewing")
def book_viewing(payload: BookingViewingRequest):
    booking_id = f"VIEW-{payload.propertyId}-{len(BOOKINGS_STORE) + 1}"
    prop = PROPERTIES.get(payload.propertyId)
    new_booking = {
        "id": booking_id,
        "propertyId": payload.propertyId,
        "propertyTitle": prop["title"] if prop else "Property Viewing",
        "date": payload.date,
        "time": payload.time,
        "name": payload.name,
        "email": payload.email,
        "phone": payload.phone,
        "status": "confirmed",
    }
    BOOKINGS_STORE.append(new_booking)
    return {"id": booking_id}


@app.post("/api/bookings/consultation")
def book_consultation(payload: BookingConsultationRequest):
    return {"id": f"CONSULT-{payload.service}-{payload.email}"}


# ---------------------------------------------------------------------------
# Account routes — powers My Investments & My Bookings pages
# ---------------------------------------------------------------------------

@app.get("/api/account/investments")
def get_my_investments():
    # Returns investments stored in memory (populated after payments)
    return INVESTMENTS_STORE


@app.get("/api/account/bookings")
def get_my_bookings():
    # Returns all bookings stored in memory
    return BOOKINGS_STORE


# ---------------------------------------------------------------------------
# Payment routes
# ---------------------------------------------------------------------------

@app.post("/api/payments/initialize")
def initialize_payment(payload: PaymentRequest):
    reference = f"PSK-REF-{payload.plotId or 'UNKNOWN'}"
    # Record as an investment when payment is initialized
    if payload.plotId and payload.amount and payload.email:
        property_id = payload.plotId.split("-")[0].replace("LG", "101").replace("KN", "201")
        prop = PROPERTIES.get(property_id)
        investment = {
            "id": f"INV-{len(INVESTMENTS_STORE) + 1}",
            "plotId": payload.plotId,
            "plotLabel": payload.plotId,
            "propertyTitle": prop["title"] if prop else "Great Harvest Estate",
            "propertyLocation": prop["location"] if prop else "Nigeria",
            "amount": payload.amount,
            "paidAt": "2025-01-01T00:00:00Z",
            "status": "active",
        }
        INVESTMENTS_STORE.append(investment)
    return {
        "reference": reference,
        "authorizationUrl": f"https://checkout.paystack.com/mock/{reference}",
    }


@app.get("/api/payments/verify/{reference}")
def verify_payment(reference: str):
    return {
        "status": "success",
        "receipt": {
            "reference": reference,
            "amount": 0,
            "currency": "NGN",
            "paidAt": "2025-01-01T00:00:00Z",
            "customer": {"name": "Test User", "email": "test@example.com"},
            "property": {"title": "Great Harvest Estate", "location": "Nigeria"},
            "plot": {"label": "A1", "size": "500 sqm"},
        },
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)