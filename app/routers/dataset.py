import csv
import io
import os
import zipfile
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioRecord

router = APIRouter(prefix="/api/dataset", tags=["Dataset"])


@router.get("/download", summary="Download full dataset as ZIP")
def download_dataset(db: Session = Depends(get_db)):
    """
    Returns a ZIP archive containing:
      - All audio files renamed sequentially  (audio_1.wav, audio_2.wav …)
      - metadata.csv  (audio_file, transcription, device_id, timestamp)
    """
    records = db.query(AudioRecord).order_by(AudioRecord.created_at).all()

    if not records:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No audio records found.")

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ── metadata.csv ─────────────────────────────────
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["audio_file", "transcription", "device_id", "timestamp"])

        for idx, rec in enumerate(records, start=1):
            ext          = os.path.splitext(rec.file_path)[1]
            export_name  = f"audio_{idx}{ext}"

            # Write row
            writer.writerow([export_name, rec.transcription, rec.device_id, rec.created_at.isoformat()])

            # Add audio file to ZIP
            if os.path.exists(rec.file_path):
                zf.write(rec.file_path, arcname=f"dataset/{export_name}")

        zf.writestr("dataset/metadata.csv", csv_buffer.getvalue())

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=dataset.zip"},
    )