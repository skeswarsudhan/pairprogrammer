import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Room


router = APIRouter(prefix="/rooms", tags=["rooms"])


class RoomResponse(BaseModel):
    roomId:str
    code:str
    
    class Config:
        orm_mode=True
        
def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@router.post("", response_model=RoomResponse)
def create_room(db:Session=Depends(get_db)):
    room_id=str(uuid.uuid4())[:8]
    room=Room(id=room_id, code="")
    db.add(room)
    db.commit()
    db.refresh(room)
    return RoomResponse(roomId=room.id, code=room.code)

@router.get("", response_model=list[RoomResponse])
def list_room(db: Session=Depends(get_db)):
    rooms=db.query(Room).all()
    return [RoomResponse(roomId=room.id,code=room.code) for room in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id:str, db:Session=Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse(roomId=room.id, code=room.code)