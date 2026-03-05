import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    device_id     = Column(String(64), primary_key=True, index=True)
    device_model  = Column(String(128), nullable=True)
    registered_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationship
    audio_records = relationship("AudioRecord", back_populates="device", cascade="all, delete")


class AudioRecord(Base):
    __tablename__ = "audio_records"

    audio_id      = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id     = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    file_path     = Column(Text, nullable=False)
    transcription = Column(Text, nullable=False)
    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationship
    device = relationship("Device", back_populates="audio_records")

    # Indexes for query performance (bonus requirement)
    __table_args__ = (
        Index("ix_audio_device_id",   "device_id"),
        Index("ix_audio_created_at",  "created_at"),
    )