from sqlalchemy import Column, DateTime, String, Text, func
from database import Base


class Room(Base):
    __tablename__="rooms"
    
    id = Column(String, primary_key=True, index=True)
    code=Column(Text, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    