from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
import os

from models import CreateUserDTO, UserResponseDTO

load_dotenv()

app = FastAPI(title="Location Validation Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MongoDB connection ─────────────────────────────────────────────────────────

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client     = AsyncIOMotorClient(MONGO_URI)
db         = client["location_demo"]
users_col  = db["users"]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/api/users", response_model=UserResponseDTO, status_code=201)
async def create_user(dto: CreateUserDTO):
    # Check duplicate email
    existing = await users_col.find_one({"email": dto.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    doc = dto.model_dump()
    result = await users_col.insert_one(doc)

    return UserResponseDTO(
        id          = str(result.inserted_id),
        first_name  = dto.first_name,
        last_name   = dto.last_name,
        email       = dto.email,
        phone       = dto.phone,
        country     = dto.country,
        state       = dto.state,
        city        = dto.city,
        postal_code = dto.postal_code,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
