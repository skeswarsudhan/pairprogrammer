"""Room management endpoints with authentication and admin controls."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Room, RoomParticipant, User
from utils.auth_utils import get_current_user, get_current_user_optional, get_password_hash, verify_password


router = APIRouter(prefix="/rooms", tags=["rooms"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Request/Response Models
class CreateRoomRequest(BaseModel):
    name: str
    is_private: bool = False
    password: Optional[str] = None
    ai_autocomplete_enabled: bool = True


class UpdateRoomRequest(BaseModel):
    name: Optional[str] = None
    is_private: Optional[bool] = None
    password: Optional[str] = None
    ai_autocomplete_enabled: Optional[bool] = None


class JoinRoomRequest(BaseModel):
    password: Optional[str] = None


class RoomResponse(BaseModel):
    roomId: str
    name: str
    code: str
    admin_id: str
    is_private: bool
    ai_autocomplete_enabled: bool
    admin_username: str
    
    class Config:
        from_attributes = True


class UserInRoomResponse(BaseModel):
    id: str
    username: str
    email: str
    joined_at: str
    
    class Config:
        from_attributes = True


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    request: CreateRoomRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new room (requires authentication)."""
    # Validate password for private rooms
    if request.is_private and not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for private rooms"
        )
    
    # Generate room ID
    room_id = str(uuid.uuid4())[:8]
    
    # Hash password if provided
    password_hash = None
    if request.password:
        password_hash = get_password_hash(request.password)
    
    # Create room
    room = Room(
        id=room_id,
        name=request.name,
        code="",
        admin_id=current_user.id,
        is_private=request.is_private,
        password_hash=password_hash,
        ai_autocomplete_enabled=request.ai_autocomplete_enabled
    )
    
    db.add(room)
    db.commit()
    db.refresh(room)
    
    # Add creator as participant
    participant = RoomParticipant(
        id=str(uuid.uuid4()),
        room_id=room.id,
        user_id=current_user.id
    )
    db.add(participant)
    db.commit()
    
    return RoomResponse(
        roomId=room.id,
        name=room.name,
        code=room.code,
        admin_id=room.admin_id,
        is_private=room.is_private,
        ai_autocomplete_enabled=room.ai_autocomplete_enabled,
        admin_username=current_user.username
    )


@router.get("", response_model=List[RoomResponse])
def list_rooms(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """List all public rooms and user's own rooms (if authenticated)."""
    try:
        print(f"[DEBUG] Fetching rooms. Authenticated: {current_user is not None}")
        
        # Get all public rooms
        public_rooms = db.query(Room).filter(Room.is_private == False).all()
        print(f"[DEBUG] Found {len(public_rooms)} public rooms")
        
        # If authenticated, also get user's own rooms (both public and private)
        if current_user:
            user_rooms = db.query(Room).filter(Room.admin_id == current_user.id).all()
            print(f"[DEBUG] Found {len(user_rooms)} user rooms for {current_user.username}")
            
            # Combine and deduplicate (in case user has public rooms)
            all_rooms = {room.id: room for room in public_rooms}
            for room in user_rooms:
                all_rooms[room.id] = room
            
            rooms_to_return = list(all_rooms.values())
        else:
            # If not authenticated, only return public rooms
            rooms_to_return = public_rooms
        
        print(f"[DEBUG] Returning {len(rooms_to_return)} total rooms")
        
        # Filter out invalid rooms (with None name or admin_id)
        valid_rooms = [r for r in rooms_to_return if r.name is not None and r.admin_id is not None]
        print(f"[DEBUG] After filtering invalid rooms: {len(valid_rooms)} valid rooms")
        
        return [
            RoomResponse(
                roomId=room.id,
                name=room.name,
                code=room.code,
                admin_id=room.admin_id,
                is_private=room.is_private,
                ai_autocomplete_enabled=room.ai_autocomplete_enabled,
                admin_username=room.admin.username if room.admin else "Unknown"
            )
            for room in valid_rooms
        ]
    except Exception as e:
        import traceback
        print(f"[ERROR] Error fetching rooms: {e}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        # Return empty list if there's an error
        return []


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: str, db: Session = Depends(get_db)):
    """Get room details by ID."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return RoomResponse(
        roomId=room.id,
        name=room.name,
        code=room.code,
        admin_id=room.admin_id,
        is_private=room.is_private,
        ai_autocomplete_enabled=room.ai_autocomplete_enabled,
        admin_username=room.admin.username
    )


@router.post("/{room_id}/join")
def join_room(
    room_id: str,
    request: JoinRoomRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a room (with password if private)."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if already a participant
    existing = db.query(RoomParticipant).filter(
        RoomParticipant.room_id == room_id,
        RoomParticipant.user_id == current_user.id
    ).first()
    
    if existing:
        return {"message": "Already a participant", "roomId": room_id}
    
    # Validate password for private rooms
    if room.is_private:
        if not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password required for private room"
            )
        
        if not room.password_hash or not verify_password(request.password, room.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )
    
    # Add user as participant
    participant = RoomParticipant(
        id=str(uuid.uuid4()),
        room_id=room_id,
        user_id=current_user.id
    )
    db.add(participant)
    db.commit()
    
    return {"message": "Joined room successfully", "roomId": room_id}


@router.post("/{room_id}/leave")
def leave_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave a room."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if admin
    if room.admin_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room admin cannot leave. Delete the room instead."
        )
    
    # Remove participant
    participant = db.query(RoomParticipant).filter(
        RoomParticipant.room_id == room_id,
        RoomParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a participant of this room"
        )
    
    db.delete(participant)
    db.commit()
    
    return {"message": "Left room successfully"}


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: str,
    request: UpdateRoomRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update room settings (admin only)."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is admin
    if room.admin_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room admin can update settings"
        )
    
    # Update fields
    if request.name is not None:
        room.name = request.name
    
    if request.is_private is not None:
        room.is_private = request.is_private
    
    if request.password is not None:
        room.password_hash = get_password_hash(request.password)
    
    if request.ai_autocomplete_enabled is not None:
        room.ai_autocomplete_enabled = request.ai_autocomplete_enabled
    
    db.commit()
    db.refresh(room)
    
    return RoomResponse(
        roomId=room.id,
        name=room.name,
        code=room.code,
        admin_id=room.admin_id,
        is_private=room.is_private,
        ai_autocomplete_enabled=room.ai_autocomplete_enabled,
        admin_username=room.admin.username
    )


@router.delete("/{room_id}")
def delete_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a room (admin only)."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user is admin
    if room.admin_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only room admin can delete the room"
        )
    
    db.delete(room)
    db.commit()
    
    return {"message": "Room deleted successfully"}


@router.get("/{room_id}/users", response_model=List[UserInRoomResponse])
def get_room_users(room_id: str, db: Session = Depends(get_db)):
    """Get list of users in a room."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    participants = db.query(RoomParticipant).filter(
        RoomParticipant.room_id == room_id
    ).all()
    
    return [
        UserInRoomResponse(
            id=p.user.id,
            username=p.user.username,
            email=p.user.email,
            joined_at=p.joined_at.isoformat()
        )
        for p in participants
    ]