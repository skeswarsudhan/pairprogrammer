from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from models import Room  # noqa: F401 (imported so metadata includes Room)
from routers import autocomplete, rooms, websocket, run_code

# Create tables in the database if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pair Programming Backend")

# Allow frontend (e.g., React running on localhost:5173) to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(autocomplete.router)
app.include_router(websocket.router)
app.include_router(run_code.router)



@app.get("/")
def health():
    return {"status": "ok"}
