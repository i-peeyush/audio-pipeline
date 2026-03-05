from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Device ──────────────────────────────────────────────
class DeviceBase(BaseModel):
    device_id: str
    device_model: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceOut(DeviceBase):
    registered_at: datetime

    model_config = {"from_attributes": True}


# ── Audio Record ─────────────────────────────────────────
class AudioRecordOut(BaseModel):
    audio_id:      str
    device_id:     str
    transcription: str
    audio_url:     str
    timestamp:     datetime

    model_config = {"from_attributes": True}


# ── Upload Response ───────────────────────────────────────
class UploadResponse(BaseModel):
    status:   str
    audio_id: str