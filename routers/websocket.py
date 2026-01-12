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
        
        # Check if user is a participant or admin (must join via API first for private rooms)
        if user_id:
            existing_participant = db.query(RoomParticipant).filter(
                RoomParticipant.room_id == room_id,
                RoomParticipant.user_id == user_id
            ).first()
            
            is_admin = room.admin_id == user_id
            
            # For private rooms, user must be a participant or admin
            if room.is_private and not existing_participant and not is_admin:
                await websocket.close(code=4001, reason="Must join room first")
                return
            
            # Get user info for broadcasting
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
            await websocket.send_text(room.code)
        
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
                        await conn["ws"].send_text(data)
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
