import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import AudioRecord
from app.schemas import AudioRecordOut

router = APIRouter(prefix="/api/device", tags=["Device"])

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _build_audio_url(audio_id: str, file_path: str) -> str:
    ext = os.path.splitext(file_path)[1]
    return f"{BASE_URL}/api/audio/file/{audio_id}{ext}"


@router.get("/{device_id}/audio", response_model=List[AudioRecordOut])
def get_device_audio(device_id: str, db: Session = Depends(get_db)):
    records = (
        db.query(AudioRecord)
        .filter(AudioRecord.device_id == device_id)
        .order_by(AudioRecord.created_at.desc())
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail=f"No audio records found for device '{device_id}'")

    return [
        AudioRecordOut(
            audio_id      = r.audio_id,
            device_id     = r.device_id,
            transcription = r.transcription,
            audio_url     = _build_audio_url(r.audio_id, r.file_path),
            timestamp     = r.created_at,
        )
        for r in records
    ]