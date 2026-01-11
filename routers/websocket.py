import uuid
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Room, RoomParticipant, User
from utils.auth_utils import decode_access_token

router = APIRouter(tags=["websocket"])


# Track WebSocket connections with user info
connections: Dict[str, List[dict]] = {}  # room_id -> [{"ws": WebSocket, "user_id": str}]


def get_db_session() -> Session:
    db = SessionLocal()
    return db


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = Query(None)):
    await websocket.accept()
    
    db = get_db_session()
    user_id = None
    
    try:
        # Authenticate user from token
        if token:
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
        
        # Verify room exists
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            await websocket.send_json({"error": "Room not found"})
            await websocket.close()
            return
        
        # Initialize connections for this room
        if room_id not in connections:
            connections[room_id] = []
        
        # Add connection
        connection_info = {"ws": websocket, "user_id": user_id}
        connections[room_id].append(connection_info)
        
        # Add user to participants if authenticated and not already a participant
        if user_id:
            existing_participant = db.query(RoomParticipant).filter(
                RoomParticipant.room_id == room_id,
                RoomParticipant.user_id == user_id
            ).first()
            
            if not existing_participant:
                participant = RoomParticipant(
                    id=str(uuid.uuid4()),
                    room_id=room_id,
                    user_id=user_id
                )
                db.add(participant)
                db.commit()
            
            # Get user info
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                # Broadcast user joined event
                join_message = {
                    "type": "user_joined",
                    "user_id": user_id,
                    "username": user.username
                }
                for conn in connections[room_id]:
                    if conn["ws"] is not websocket:
                        try:
                            await conn["ws"].send_json(join_message)
                        except:
                            pass
        
        # Send current code to new connection
        if room.code:
            await websocket.send_json({"type": "code", "content": room.code})
        
        # Main message loop
        while True:
            data = await websocket.receive_text()
            
            # Update room code
            room = db.query(Room).filter(Room.id == room_id).first()
            if room:
                room.code = data
                db.commit()
            
            # Broadcast to other connections
            for conn in connections[room_id]:
                if conn["ws"] is not websocket:
                    try:
                        await conn["ws"].send_json({"type": "code", "content": data})
                    except:
                        pass
    
    except WebSocketDisconnect:
        pass
    finally:
        # Remove connection
        if room_id in connections:
            connections[room_id] = [
                conn for conn in connections[room_id] 
                if conn["ws"] is not websocket
            ]
            
            if not connections[room_id]:
                del connections[room_id]
        
        # Broadcast user left event if authenticated
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user and room_id in connections:
                leave_message = {
                    "type": "user_left",
                    "user_id": user_id,
                    "username": user.username
                }
                for conn in connections[room_id]:
                    try:
                        await conn["ws"].send_json(leave_message)
                    except:
                        pass
        
        db.close()
