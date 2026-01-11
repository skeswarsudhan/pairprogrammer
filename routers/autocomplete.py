from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from groq_client import client
from database import SessionLocal
from models import Room

router = APIRouter(prefix="/autocomplete", tags=["autocomplete"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AutoRequest(BaseModel):
    code: str
    cursorPosition: int
    language: str
    room_id: str  # Added room_id to check AI autocomplete settings


class AutoResponse(BaseModel):
    suggestion: str


SYSTEM_PROMPT = """
You are a code autocomplete engine.
The user provides a partial code snippet, a cursor position, and a language (e.g. python, javascript, c, c++).
You must respond with a short, syntactically valid continuation suitable as an autocomplete suggestion
for that language.
Do NOT repeat the whole existing code; only return the new text to insert.
Return plain code only, no explanations or comments.
"""



@router.post("", response_model=AutoResponse)
def autocomplete(req: AutoRequest, db: Session = Depends(get_db)):
    # Check if room exists and AI autocomplete is enabled
    room = db.query(Room).filter(Room.id == req.room_id).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if not room.ai_autocomplete_enabled:
        raise HTTPException(
            status_code=403, 
            detail="AI autocomplete is disabled for this room"
        )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",  
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Language: {req.language}\n"
                        f"Cursor position: {req.cursorPosition}\n"
                        "Code before cursor:\n"
                        f"{req.code[:req.cursorPosition]}\n\n"
                        "Code after cursor:\n"
                        f"{req.code[req.cursorPosition:]}\n\n"
                        "Now output ONLY the suggested continuation to insert at the cursor."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=64,
        )

        suggestion_text = completion.choices[0].message.content.strip()
        return AutoResponse(suggestion=suggestion_text)
    except Exception as e:
        print("Groq autocomplete error:", e)
        raise HTTPException(status_code=500, detail="Autocomplete service error")
