from pathlib import Path
from backend.app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def validate_file(
    file_path: str | Path,
    max_mb: int = settings.MAX_UPLOAD_MB,
    allowed_extensions: set[str] | None = None,
) -> tuple[bool, str]:
    path = Path(file_path)
    allowed = allowed_extensions or ALLOWED_EXTENSIONS

    if not path.exists():
        return False, f"File does not exist: {path.name}"

    if not path.is_file():
        return False, f"Path is not a regular file: {path.name}"

    suffix = path.suffix.lower()
    if suffix not in allowed:
        return (
            False,
            f"Unsupported file format '{suffix}'. Allowed: {', '.join(sorted(allowed))}",
        )

    file_size = path.stat().st_size
    if file_size == 0:
        return False, f"File is empty (0 bytes): {path.name}"

    max_bytes = max_mb * 1024 * 1024
    if file_size > max_bytes:
        return (
            False,
            f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit of {max_mb} MB",
        )

    return True, ""
