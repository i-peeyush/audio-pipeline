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
    # Create DB tables on startup
    Base.metadata.create_all(bind=engine)
    # Ensure storage directory exists
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

# ── Routers ──────────────────────────────────────────────
app.include_router(audio.router)
app.include_router(device.router)
app.include_router(dataset.router)


# ── Serve audio files directly ───────────────────────────
@app.get("/api/audio/file/{filename}", tags=["Audio"], summary="Stream/download a single audio file")
def serve_audio_file(filename: str):
    # Search all device sub-directories
    for root, _, files in os.walk(STORAGE_PATH):
        if filename in files:
            return FileResponse(os.path.join(root, filename))
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Audio file not found.")


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "AI Wearable Audio Pipeline is running."}