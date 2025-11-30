from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Room

router = APIRouter(tags=["websocket"])


connections: Dict[str, List[WebSocket]] = {}


def get_db_session() -> Session:
    db = SessionLocal()
    return db


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    if room_id not in connections:
        connections[room_id] = []
    connections[room_id].append(websocket)

    db = get_db_session()
    try:
        room = db.query(Room).filter(Room.id == room_id).first()
        if room and room.code:
            await websocket.send_text(room.code)

        while True:
            data = await websocket.receive_text()

            room = db.query(Room).filter(Room.id == room_id).first()
            if room:
                room.code = data
                db.commit()

            for conn in connections[room_id]:
                if conn is not websocket:
                    await conn.send_text(data)

    except WebSocketDisconnect:
        connections[room_id].remove(websocket)
        if not connections[room_id]:
            del connections[room_id]
    finally:
        db.close()
