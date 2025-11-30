from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests

router = APIRouter(prefix="/run", tags=["run"])

PISTON_URL = "https://emkc.org/api/v2/piston/execute"

class RunRequest(BaseModel):
    language: str
    code: str

class RunResponse(BaseModel):
    stdout: str
    stderr: str

@router.post("", response_model=RunResponse)
def run_code(req: RunRequest):
    try:
        payload = {
            "language": req.language,
            "version": "*",  # latest version
            "files": [
                {"content": req.code}
            ]
        }

        response = requests.post(PISTON_URL, json=payload)
        data = response.json()

        stdout = data.get("run", {}).get("stdout", "")
        stderr = data.get("run", {}).get("stderr", "")

        return RunResponse(stdout=stdout, stderr=stderr)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
