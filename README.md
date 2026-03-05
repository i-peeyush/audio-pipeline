# AI Wearable Audio Pipeline – Complete Code Explanation & Interview Guide

---

## Project Overview

This project is a backend system built for AI wearable glasses that continuously capture short audio commands from users. The backend receives audio files from devices, stores them on the server, saves transcriptions mapped to the audio, and allows downloading the full dataset as a ZIP file for AI model training.

---

## Tech Stack & Why Each Was Chosen

| Technology | Purpose | Why |
|---|---|---|
| FastAPI | Web framework | Fast, modern, async-ready, auto-generates Swagger docs |
| PostgreSQL | Database | Relational, scalable, supports indexing |
| Supabase | Cloud PostgreSQL host | Free, no local DB setup needed |
| SQLAlchemy | ORM (Object Relational Mapper) | Write Python instead of raw SQL |
| psycopg2-binary | PostgreSQL driver | Connects Python to PostgreSQL |
| Uvicorn | ASGI server | Runs the FastAPI application |
| python-dotenv | Environment variables | Keeps secrets out of code |
| aiofiles | Async file operations | Non-blocking file reads/writes |
| httpx | HTTP client | Used in simulator to send requests |
| Docker | Containerization | Anyone can run the project with one command |

---

## File-by-File Code Explanation

---

### 1. `requirements.txt`

```txt
fastapi==0.110.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.40
psycopg2-binary
python-multipart==0.0.9
python-dotenv==1.0.1
aiofiles==23.2.1
httpx==0.27.0
```

Every line is a Python package the project depends on.

- `fastapi` — the web framework that handles all HTTP requests and responses
- `uvicorn[standard]` — the server that runs FastAPI. The `[standard]` part installs extras like `watchfiles` for auto-reload
- `sqlalchemy` — the ORM that lets us define database tables as Python classes and query them using Python
- `psycopg2-binary` — the driver that actually connects to PostgreSQL. SQLAlchemy uses this under the hood
- `python-multipart` — required by FastAPI to handle `multipart/form-data` requests (file uploads)
- `python-dotenv` — reads the `.env` file and loads variables like `DATABASE_URL` into the environment
- `aiofiles` — allows reading/writing files without blocking the server
- `httpx` — an HTTP client used in `simulate_device.py` to send requests to the API

---

### 2. `.env`

```env
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-xxx.pooler.supabase.com:5432/postgres
STORAGE_PATH=./storage/audio
BASE_URL=http://localhost:8000
```

This file stores configuration values that should not be hardcoded in the source code.

- `DATABASE_URL` — the full connection string to the PostgreSQL database. SQLAlchemy uses this to connect
- `STORAGE_PATH` — the folder path where uploaded audio files are saved on the server
- `BASE_URL` — the base URL of the running server, used to generate audio file URLs in API responses

This file is listed in `.gitignore` so it is never pushed to GitHub, keeping credentials private.

---

### 3. `app/database.py`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/audio_pipeline")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This file is responsible for setting up the database connection.

- `load_dotenv()` — loads the `.env` file so `os.getenv()` can read the variables
- `os.getenv("DATABASE_URL", "...")` — reads `DATABASE_URL` from environment. The second argument is a fallback default value
- `create_engine(DATABASE_URL, pool_pre_ping=True)` — creates the SQLAlchemy engine which manages the database connection. `pool_pre_ping=True` means it tests the connection before using it, preventing stale connection errors
- `SessionLocal = sessionmaker(...)` — creates a factory for database sessions. Each request gets its own session
  - `autocommit=False` — changes are not saved automatically, we control when to commit
  - `autoflush=False` — SQLAlchemy won't automatically flush pending changes to the DB
  - `bind=engine` — links the session factory to our database engine
- `class Base(DeclarativeBase)` — the base class all database models inherit from. SQLAlchemy uses this to track all tables
- `get_db()` — a dependency function used by FastAPI. It creates a DB session for each request and closes it when the request is done. The `yield` makes it a generator, which FastAPI uses as a context manager

---

### 4. `app/models.py`

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Device(Base):
    __tablename__ = "devices"

    device_id     = Column(String(64), primary_key=True, index=True)
    device_model  = Column(String(128), nullable=True)
    registered_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    audio_records = relationship("AudioRecord", back_populates="device", cascade="all, delete")

class AudioRecord(Base):
    __tablename__ = "audio_records"

    audio_id      = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id     = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    file_path     = Column(Text, nullable=False)
    transcription = Column(Text, nullable=False)
    created_at    = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    device = relationship("Device", back_populates="audio_records")

    __table_args__ = (
        Index("ix_audio_device_id", "device_id"),
        Index("ix_audio_created_at", "created_at"),
    )
```

This file defines the database tables as Python classes.

- `utcnow()` — a helper function that returns the current UTC time. Used as a default value for timestamp columns
- `class Device(Base)` — represents the `devices` table in the database
  - `__tablename__ = "devices"` — sets the actual table name in PostgreSQL
  - `device_id = Column(String(64), primary_key=True)` — the unique ID for each device, max 64 characters, primary key
  - `device_model` — optional field to store the model name of the device
  - `registered_at` — auto-set to current UTC time when a device is first created
  - `audio_records = relationship(...)` — defines a one-to-many relationship. One device has many audio records. `cascade="all, delete"` means if a device is deleted, all its audio records are also deleted
- `class AudioRecord(Base)` — represents the `audio_records` table
  - `audio_id = Column(..., default=lambda: str(uuid.uuid4()))` — generates a new UUID automatically for each record
  - `device_id = Column(..., ForeignKey(..., ondelete="CASCADE"))` — links to the `devices` table. `CASCADE` means if the device is deleted, this record is also deleted
  - `file_path` — stores the path to the audio file on the server disk
  - `transcription` — stores the text version of the audio
  - `created_at` — auto-set timestamp when the record is created
  - `__table_args__` — adds database indexes on `device_id` and `created_at` columns for faster queries

---

### 5. `app/schemas.py`

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class DeviceBase(BaseModel):
    device_id: str
    device_model: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceOut(DeviceBase):
    registered_at: datetime
    model_config = {"from_attributes": True}

class AudioRecordOut(BaseModel):
    audio_id:      str
    device_id:     str
    transcription: str
    audio_url:     str
    timestamp:     datetime
    model_config = {"from_attributes": True}

class UploadResponse(BaseModel):
    status:   str
    audio_id: str
```

Schemas define the shape of data coming in and going out of the API. They are different from models — models are for the database, schemas are for the API.

- `BaseModel` — Pydantic's base class that handles data validation automatically
- `DeviceBase` — base schema with common device fields
- `DeviceCreate` — schema used when creating a device (inherits from DeviceBase, adds nothing extra)
- `DeviceOut` — schema used when returning device data in a response
- `AudioRecordOut` — defines exactly what fields are returned when audio record data is sent to the client. Notice `audio_url` is here but not in the model — it is generated dynamically
- `UploadResponse` — the response returned after a successful audio upload
- `model_config = {"from_attributes": True}` — tells Pydantic to read data from SQLAlchemy model attributes (ORM objects) instead of just dictionaries

---

### 6. `app/routers/audio.py`

```python
import os, uuid, shutil
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
    ext = os.path.splitext(audio_file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'")

    _ensure_device(db, device_id)

    audio_id  = str(uuid.uuid4())
    filename  = f"{audio_id}{ext}"
    dest_dir  = os.path.join(STORAGE_PATH, device_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)

    record = AudioRecord(
        audio_id=audio_id, device_id=device_id,
        file_path=dest_path, transcription=transcription,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()

    return UploadResponse(status="success", audio_id=audio_id)
```

This file handles the audio upload endpoint.

- `APIRouter(prefix="/api/audio", tags=["Audio"])` — creates a router. All routes defined here will start with `/api/audio`. Tags group endpoints in Swagger UI
- `ALLOWED_EXTENSIONS` — a set of valid audio file types. Using a set for O(1) lookup performance
- `_ensure_device()` — checks if the device already exists in the database. If not, it creates it automatically. This means devices don't need to be registered separately before uploading
- `@router.post("/upload", ...)` — defines the POST endpoint at `/api/audio/upload`
  - `status_code=201` — returns HTTP 201 Created on success
  - `response_model=UploadResponse` — FastAPI automatically validates and serializes the response
- `device_id = Form(...)` — reads `device_id` from form data. `...` means it is required
- `audio_file = UploadFile = File(...)` — reads the uploaded file from form data
- `db: Session = Depends(get_db)` — FastAPI dependency injection. Automatically creates and provides a DB session
- `os.path.splitext(...)` — splits the filename into name and extension (e.g. `audio.wav` → `("audio", ".wav")`)
- `raise HTTPException(status_code=400, ...)` — returns a 400 error if the file type is not allowed
- `str(uuid.uuid4())` — generates a new unique ID for the audio record
- `os.makedirs(dest_dir, exist_ok=True)` — creates the storage folder if it doesn't exist. `exist_ok=True` prevents an error if it already exists
- `shutil.copyfileobj(audio_file.file, f)` — efficiently copies the uploaded file to disk in chunks, avoiding loading the entire file into memory
- `db.add(record)` — stages the new record for insertion
- `db.commit()` — saves the record to the database

---

### 7. `app/routers/device.py`

```python
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
            audio_id=r.audio_id, device_id=r.device_id,
            transcription=r.transcription,
            audio_url=_build_audio_url(r.audio_id, r.file_path),
            timestamp=r.created_at,
        )
        for r in records
    ]
```

This file handles retrieving all audio records for a specific device.

- `/{device_id}/audio` — dynamic route. `device_id` is captured from the URL (e.g. `/api/device/device_101/audio`)
- `response_model=List[AudioRecordOut]` — tells FastAPI to return a list of `AudioRecordOut` objects
- `_build_audio_url()` — constructs a full URL for each audio file so the client can directly download or stream it
- `db.query(AudioRecord).filter(...).order_by(...).all()` — SQLAlchemy query that fetches all records for the given device, ordered by newest first
- `raise HTTPException(status_code=404, ...)` — returns 404 if no records are found for that device
- List comprehension `[AudioRecordOut(...) for r in records]` — converts each database model object into an API response schema object

---

### 8. `app/routers/dataset.py`

```python
import csv, io, os, zipfile
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AudioRecord

router = APIRouter(prefix="/api/dataset", tags=["Dataset"])

@router.get("/download", summary="Download full dataset as ZIP")
def download_dataset(db: Session = Depends(get_db)):
    records = db.query(AudioRecord).order_by(AudioRecord.created_at).all()

    if not records:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No audio records found.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:

        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["audio_file", "transcription", "device_id", "timestamp"])

        for idx, rec in enumerate(records, start=1):
            ext         = os.path.splitext(rec.file_path)[1]
            export_name = f"audio_{idx}{ext}"
            writer.writerow([export_name, rec.transcription, rec.device_id, rec.created_at.isoformat()])

            if os.path.exists(rec.file_path):
                zf.write(rec.file_path, arcname=f"dataset/{export_name}")

        zf.writestr("dataset/metadata.csv", csv_buffer.getvalue())

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=dataset.zip"},
    )
```

This is the most complex file — it generates the downloadable dataset.

- `io.BytesIO()` — creates an in-memory binary buffer. The ZIP file is built here instead of on disk, saving storage and being faster
- `zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED)` — creates a ZIP file writer inside the memory buffer. `ZIP_DEFLATED` means files are compressed
- `io.StringIO()` — creates an in-memory text buffer for building the CSV content
- `csv.writer(csv_buffer)` — a CSV writer that writes into the in-memory string buffer
- `writer.writerow(["audio_file", ...])` — writes the header row of the CSV
- `enumerate(records, start=1)` — loops through records with an index starting at 1 (so `audio_1.wav`, `audio_2.wav`, etc.)
- `zf.write(rec.file_path, arcname=f"dataset/{export_name}")` — adds the actual audio file to the ZIP. `arcname` sets the filename inside the ZIP
- `zf.writestr("dataset/metadata.csv", csv_buffer.getvalue())` — writes the CSV content as a file inside the ZIP
- `zip_buffer.seek(0)` — resets the buffer position to the beginning so it can be read from the start when sent to the client
- `StreamingResponse(...)` — streams the ZIP file to the client without loading it all into memory at once
- `Content-Disposition: attachment; filename=dataset.zip` — tells the browser to download the file instead of displaying it

---

### 9. `app/main.py`

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.database import Base, engine
from app.routers import audio, device, dataset

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage/audio")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    os.makedirs(STORAGE_PATH, exist_ok=True)
    yield

app = FastAPI(
    title="AI Wearable Audio Pipeline",
    description="Backend system to ingest, store, and export audio data from AI wearable devices.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audio.router)
app.include_router(device.router)
app.include_router(dataset.router)

@app.get("/api/audio/file/{filename}", tags=["Audio"])
def serve_audio_file(filename: str):
    for root, _, files in os.walk(STORAGE_PATH):
        if filename in files:
            return FileResponse(os.path.join(root, filename))
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Audio file not found.")

@app.get("/")
def root():
    return {"status": "ok", "message": "AI Wearable Audio Pipeline is running."}
```

This is the entry point of the application.

- `@asynccontextmanager async def lifespan(app)` — runs code on startup and shutdown. Everything before `yield` runs on startup, everything after runs on shutdown
  - `Base.metadata.create_all(bind=engine)` — creates all database tables automatically if they don't exist. This is why we don't need to manually run SQL CREATE TABLE statements
  - `os.makedirs(STORAGE_PATH, exist_ok=True)` — creates the storage folder on startup if it doesn't exist
- `FastAPI(title=..., description=..., version=...)` — creates the FastAPI app. These values appear in the Swagger UI
- `CORSMiddleware` — allows cross-origin requests. `allow_origins=["*"]` means any frontend can call this API
- `app.include_router(...)` — registers each router with the app. This connects all the endpoints defined in the router files
- `os.walk(STORAGE_PATH)` — recursively searches through all device subfolders to find the requested audio file
- `FileResponse(...)` — streams the audio file directly to the client

---

### 10. `simulate_device.py`

```python
import os, struct, wave, time, random, httpx

BASE_URL = "http://localhost:8000"
DEVICES = ["device_101", "device_102", "device_203"]
COMMANDS = ["open camera", "read this text", "take a photo", ...]

def generate_dummy_wav(path: str, duration_ms: int = 500) -> None:
    sample_rate  = 16000
    num_channels = 1
    bit_depth    = 16
    num_samples  = int(sample_rate * duration_ms / 1000)

    with wave.open(path, "w") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(bit_depth // 8)
        wf.setframerate(sample_rate)
        frames = struct.pack(f"<{num_samples}h", *[random.randint(-100, 100) for _ in range(num_samples)])
        wf.writeframes(frames)

def upload_audio(device_id, transcription, wav_path):
    with open(wav_path, "rb") as f:
        resp = httpx.post(
            f"{BASE_URL}/api/audio/upload",
            data={"device_id": device_id, "transcription": transcription},
            files={"audio_file": (os.path.basename(wav_path), f, "audio/wav")},
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()

def main():
    for i in range(1, 11):
        device_id     = random.choice(DEVICES)
        transcription = random.choice(COMMANDS)
        wav_path      = f"./tmp_sim/sim_{i}.wav"
        generate_dummy_wav(wav_path)
        result = upload_audio(device_id, transcription, wav_path)
        print(f"[{i:02d}] {device_id} | '{transcription}' | audio_id={result['audio_id']}")
        time.sleep(0.3)
```

This script simulates real wearable devices sending audio to the backend.

- `generate_dummy_wav()` — creates a valid `.wav` file with very low-amplitude random noise (simulating silence)
  - `sample_rate = 16000` — 16kHz is the standard for speech audio
  - `num_channels = 1` — mono audio (single channel)
  - `bit_depth = 16` — 16-bit audio samples
  - `struct.pack(f"<{num_samples}h", ...)` — packs random integers as little-endian 16-bit signed integers into binary data
  - `wf.writeframes(frames)` — writes the binary audio data to the WAV file
- `upload_audio()` — sends an HTTP POST request to the upload endpoint
  - `data={"device_id": ..., "transcription": ...}` — form fields
  - `files={"audio_file": (...)}` — the file upload part of the form
  - `resp.raise_for_status()` — raises an exception if the server returns an error status
- `time.sleep(0.3)` — waits 300ms between uploads to avoid overwhelming the server

---

### 11. `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p storage/audio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Defines how to build the Docker image for this project.

- `FROM python:3.11-slim` — starts from an official Python 3.11 image. `slim` means minimal size
- `WORKDIR /app` — sets the working directory inside the container to `/app`
- `COPY requirements.txt .` — copies only requirements first (before the rest of the code) so Docker can cache this layer
- `RUN pip install --no-cache-dir -r requirements.txt` — installs dependencies. `--no-cache-dir` reduces image size
- `COPY . .` — copies the rest of the project code into the container
- `RUN mkdir -p storage/audio` — creates the storage folder inside the container
- `CMD [...]` — the command that runs when the container starts. `--host 0.0.0.0` makes it accessible from outside the container

---

### 12. `docker-compose.yml`

```yaml
version: "3.9"
services:
  api:
    build: .
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./storage:/app/storage
```

Defines how to run the Docker container.

- `build: .` — builds the Docker image using the `Dockerfile` in the current directory
- `restart: always` — automatically restarts the container if it crashes
- `ports: - "8000:8000"` — maps port 8000 on your machine to port 8000 inside the container
- `env_file: - .env` — loads environment variables from the `.env` file into the container
- `volumes: - ./storage:/app/storage` — maps the local `storage` folder to the container's storage folder so uploaded files persist even if the container restarts

---

## Common Interview Questions & Answers

**Q: Why did you use FastAPI instead of Django or Flask?**

FastAPI is faster than Flask for APIs, has built-in data validation via Pydantic, auto-generates Swagger documentation, and supports async natively. Django is heavier and better suited for full web apps, not just APIs.

**Q: Why UUID for audio_id instead of auto-increment integer?**

UUIDs are globally unique across all devices and tables, making them safe if we ever merge data from multiple databases or servers. Auto-increment IDs can clash when combining datasets.

**Q: How does the dataset download work without creating temp files?**

The ZIP is built entirely in memory using `io.BytesIO()`. Audio files are read from disk and written directly into the in-memory ZIP buffer, which is then streamed to the client. No temporary files are created on disk.

**Q: What are the database indexes for?**

Indexes on `device_id` and `created_at` make queries faster. Without them, PostgreSQL would scan every row in the table. With millions of records, an index makes the query go from O(n) to O(log n).

**Q: How does auto device registration work?**

In `_ensure_device()`, before saving an audio record, we check if the device already exists in the `devices` table. If not, we create it automatically. This means the device doesn't need a separate registration step.

**Q: What is dependency injection in FastAPI?**

`Depends(get_db)` is dependency injection. Instead of creating a database session manually in every endpoint, FastAPI automatically creates it, passes it to the function, and closes it after the request is done. This keeps code clean and ensures sessions are always properly closed.

**Q: Why store files per device in separate folders?**

`storage/audio/device_101/uuid.wav` organizes files by device. This makes it easy to find, delete, or backup files for a specific device without scanning all files.

**Q: How does the system scale?**

- Database indexes handle large numbers of records efficiently
- Files are stored per device for easy management
- Streaming responses avoid loading large datasets into memory
- Docker ensures consistent deployment across any environment
- The connection pool in SQLAlchemy handles multiple simultaneous requests

**Q: What does `pool_pre_ping=True` do in SQLAlchemy?**

It tests the database connection before using it from the pool. This prevents errors when the database has closed an idle connection. It sends a lightweight ping and reconnects if needed.

**Q: Why use `shutil.copyfileobj` instead of `file.read()`?**

`shutil.copyfileobj` copies the file in chunks instead of loading the entire file into memory at once. This is important for large audio files — it keeps memory usage low regardless of file size.
