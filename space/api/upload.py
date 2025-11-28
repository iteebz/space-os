"""Upload API endpoints."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/image")
async def upload_image(file: UploadFile):
    try:
        images_dir = Path.home() / ".space" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "image.jpg").suffix
        file_id = str(uuid.uuid4())
        filepath = images_dir / f"{file_id}{suffix}"

        content = await file.read()
        filepath.write_bytes(content)

        return {"path": str(filepath).replace(str(Path.home()), "~")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
