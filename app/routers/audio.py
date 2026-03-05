import os
import uuid
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioRecord, Device
from app.schemas import UploadResponse

router = APIRouter(prefix="/api/audio", tags=["Audio"])

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage/audio")
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}


def _ensure_device(db: Session, device_id: str) -> Device:
    """Auto-register a device if it doesn't exist yet."""
    device = db.get(Device, device_id)
    if not device:
        device = Device(device_id=device_id)
        db.add(device)
        db.commit()
        db.refresh(device)
    return device


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_audio(
    device_id:     str        = Form(...),
    transcription: str        = Form(...),
    audio_file:    UploadFile = File(...),
    db:            Session    = Depends(get_db),
):
    # ── Validate file extension ──────────────────────────
    ext = os.path.splitext(audio_file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # ── Ensure device exists ─────────────────────────────
    _ensure_device(db, device_id)

    # ── Persist file ─────────────────────────────────────
    audio_id  = str(uuid.uuid4())
    filename  = f"{audio_id}{ext}"
    dest_dir  = os.path.join(STORAGE_PATH, device_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    # ── Save DB record ───────────────────────────────────
    record = AudioRecord(
        audio_id      = audio_id,
        device_id     = device_id,
        file_path     = dest_path,
        transcription = transcription,
        created_at    = datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()

    return UploadResponse(status="success", audio_id=audio_id)