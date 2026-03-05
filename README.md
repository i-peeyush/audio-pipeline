# AI Wearable Audio Data Pipeline

A production-ready backend for ingesting, storing, and exporting audio data from AI wearable devices — built with **FastAPI**, **PostgreSQL (Supabase)**, and **local storage**.

---

## System Architecture

```
+---------------------+        HTTP (multipart/form-data)
|  Wearable Device /  | ─────────────────────────────────►
|  Simulation Script  |                                   |
+---------------------+                                   ▼
                                            +------------------------+
                                            |    FastAPI Backend     |
                                            |  +------------------+  |
                                            |  |  /api/audio      |  |
                                            |  |  /api/device     |  |
                                            |  |  /api/dataset    |  |
                                            |  +--------+---------+  |
                                            +-----------|------------+
                                                        |
                              +-------------------------+------------------+
                              ▼                                            ▼
                   +--------------------+                   +---------------------+
                   |   PostgreSQL DB    |                   |   Local Filesystem  |
                   |    (Supabase)      |                   |   storage/audio/    |
                   |  +--------------+  |                   |   +-- device_101/   |
                   |  |   devices    |  |                   |       +-- uuid.wav  |
                   |  +--------------+  |                   |   +-- device_102/   |
                   |  | audio_records|  |                   |       +-- uuid.wav  |
                   |  +--------------+  |                   +---------------------+
                   +--------------------+
```

---

## Database Schema

### devices
| Column        | Type         | Notes                    |
|---------------|--------------|--------------------------|
| device_id     | VARCHAR(64)  | Primary Key              |
| device_model  | VARCHAR(128) | Optional                 |
| registered_at | TIMESTAMPTZ  | Auto set on first upload |

### audio_records
| Column        | Type        | Notes                  |
|---------------|-------------|------------------------|
| audio_id      | VARCHAR(36) | UUID Primary Key       |
| device_id     | VARCHAR(64) | FK → devices.device_id |
| file_path     | TEXT        | Absolute path on disk  |
| transcription | TEXT        | Text mapped to audio   |
| created_at    | TIMESTAMPTZ | Auto set on upload     |

Indexes are applied on `device_id` and `created_at` for query performance.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- A free Supabase account: https://supabase.com

---

### Option A – Run with Docker (Recommended)

**Step 1 – Clone the repo**
```bash
git clone https://github.com/i-peeyush/audio-pipeline.git
cd audio-pipeline
```

**Step 2 – Create `.env` file**
```env
DATABASE_URL=postgresql://your-supabase-connection-string
STORAGE_PATH=./storage/audio
BASE_URL=http://localhost:8000
```

> Get your Supabase connection string from:
> Supabase Dashboard → Your Project → Connect → Session Pooler URI

**Step 3 – Run with Docker**
```bash
docker compose up --build
```

API is live at: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

---

### Option B – Run Locally

**Step 1 – Clone the repo**
```bash
git clone https://github.com/i-peeyush/audio-pipeline.git
cd audio-pipeline
```

**Step 2 – Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

**Step 3 – Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 4 – Create `.env` file**
```env
DATABASE_URL=postgresql://your-supabase-connection-string
STORAGE_PATH=./storage/audio
BASE_URL=http://localhost:8000
```

**Step 5 – Run the server**
```bash
uvicorn app.main:app --reload
```

**Step 6 – (Optional) Run device simulator**
```bash
python simulate_device.py
```

---

## API Reference

### POST `/api/audio/upload`
Upload audio from a device.

| Field         | Type | Required |
|---------------|------|----------|
| device_id     | str  | Yes |
| transcription | str  | Yes |
| audio_file    | file | Yes (.wav/.mp3/.ogg/.flac/.m4a) |

**Response:**
```json
{ "status": "success", "audio_id": "550e8400-e29b-41d4-a716-446655440000" }
```

---

### GET `/api/device/{device_id}/audio`
Get all audio records for a device.

**Response:**
```json
[
  {
    "audio_id": "550e8400-...",
    "device_id": "device_101",
    "transcription": "open camera",
    "audio_url": "http://localhost:8000/api/audio/file/550e8400-....wav",
    "timestamp": "2026-03-03T10:22:00Z"
  }
]
```

---

### GET `/api/dataset/download`
Download the full dataset as a ZIP archive.

**ZIP contents:**
```
dataset/
  audio_1.wav
  audio_2.wav
  ...
  metadata.csv
```

**metadata.csv:**
```
audio_file,transcription,device_id,timestamp
audio_1.wav,open camera,device_101,2026-03-03T10:22:00
audio_2.wav,read this text,device_203,2026-03-03T10:23:00
```

---

## Dataset Generation Logic

1. All audio records are fetched from the database ordered by `created_at`.
2. Each file is renamed sequentially (`audio_1.wav`, `audio_2.wav`, ...) to avoid conflicts.
3. Files are streamed into a ZIP archive in memory — no temporary files are written to disk.
4. A `metadata.csv` mapping filenames to transcriptions, device IDs, and timestamps is appended.
5. The ZIP is returned as a streaming HTTP response, making it memory-efficient for large datasets.

---

## API Documentation

Full interactive API documentation is available via Swagger UI at:

```
http://localhost:8000/docs
```

---

## Bonus Features Implemented

- DB indexes on `device_id` and `created_at`
- Docker and docker-compose support
- Auto device registration on first upload
- Streaming ZIP download (memory-efficient)
- Device simulation script with real WAV file generation
- Auto-generated Swagger / OpenAPI documentation
