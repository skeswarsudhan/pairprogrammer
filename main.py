from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from models import Room, User, RoomParticipant
from routers import autocomplete, rooms, websocket, run_code, auth


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pair Programming Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(autocomplete.router)
app.include_router(websocket.router)
app.include_router(run_code.router)



@app.get("/")
def health():
    return {"status": "ok"}
