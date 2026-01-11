from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Nullable for OAuth users
    google_id = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owned_rooms = relationship("Room", back_populates="admin", cascade="all, delete-orphan")
    participations = relationship("RoomParticipant", back_populates="user", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(Text, default="")
    admin_id = Column(String, ForeignKey("users.id"), nullable=False)
    is_private = Column(Boolean, default=False)
    password_hash = Column(String, nullable=True)  # For private rooms
    ai_autocomplete_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    admin = relationship("User", back_populates="owned_rooms")
    participants = relationship("RoomParticipant", back_populates="room", cascade="all, delete-orphan")


class RoomParticipant(Base):
    __tablename__ = "room_participants"
    
    id = Column(String, primary_key=True, index=True)
    room_id = Column(String, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    room = relationship("Room", back_populates="participants")
    user = relationship("User", back_populates="participations")
    