import uuid
from pathlib import Path

from fastapi import UploadFile


class InvalidAudioFile(ValueError):
    pass


class AudioStorage:
    def __init__(self, root: Path, max_bytes: int) -> None:
        self.root = root
        self.max_bytes = max_bytes

    async def save_mp3(self, upload: UploadFile, organization_id: uuid.UUID) -> Path:
        filename = upload.filename or ""
        if Path(filename).suffix.lower() != ".mp3":
            raise InvalidAudioFile("Only MP3 files are supported")
        if upload.content_type not in {"audio/mpeg", "audio/mp3", "application/octet-stream"}:
            raise InvalidAudioFile("Unsupported content type")

        target_dir = self.root / str(organization_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{uuid.uuid4()}.mp3"
        size = 0

        try:
            with target.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise InvalidAudioFile("File exceeds the upload limit")
                    destination.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        if size == 0:
            target.unlink(missing_ok=True)
            raise InvalidAudioFile("Audio file is empty")
        return target
