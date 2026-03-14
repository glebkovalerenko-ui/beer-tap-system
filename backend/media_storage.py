import hashlib
import os
import tempfile
import uuid
from pathlib import Path
from typing import BinaryIO


DEFAULT_MEDIA_ROOT = Path(__file__).resolve().parent / "storage" / "media-assets"
DEFAULT_MEDIA_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
ALLOWED_MEDIA_KINDS = {"background", "logo"}
ALLOWED_MEDIA_FORMATS = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
}
JPEG_START_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
}


class InvalidMediaAssetError(ValueError):
    pass


def get_media_root() -> Path:
    configured = os.getenv("MEDIA_STORAGE_ROOT", "").strip()
    root = Path(configured) if configured else DEFAULT_MEDIA_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_upload_max_bytes() -> int:
    raw_value = os.getenv("MEDIA_UPLOAD_MAX_BYTES", str(DEFAULT_MEDIA_UPLOAD_MAX_BYTES)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("MEDIA_UPLOAD_MAX_BYTES must be an integer") from exc
    return max(value, 1)


def normalize_media_kind(kind: str) -> str:
    normalized = (kind or "").strip().lower()
    if normalized not in ALLOWED_MEDIA_KINDS:
        allowed = ", ".join(sorted(ALLOWED_MEDIA_KINDS))
        raise InvalidMediaAssetError(f"Unsupported media kind. Allowed kinds: {allowed}.")
    return normalized


def _normalize_content_type(content_type: str | None) -> str:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if not normalized:
        raise InvalidMediaAssetError("Missing MIME type.")
    return normalized


def _detect_png(payload: bytes) -> tuple[str, str, int, int] | None:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(payload[16:20], "big")
    height = int.from_bytes(payload[20:24], "big")
    if width <= 0 or height <= 0:
        raise InvalidMediaAssetError("Invalid PNG dimensions.")
    return "image/png", ".png", width, height


def _detect_jpeg(payload: bytes) -> tuple[str, str, int, int] | None:
    if len(payload) < 4 or payload[0:2] != b"\xff\xd8":
        return None

    index = 2
    while index + 3 < len(payload):
        if payload[index] != 0xFF:
            index += 1
            continue

        while index < len(payload) and payload[index] == 0xFF:
            index += 1
        if index >= len(payload):
            break

        marker = payload[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue

        if index + 1 >= len(payload):
            break
        segment_length = int.from_bytes(payload[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > len(payload):
            break

        if marker in JPEG_START_MARKERS:
            if index + 7 > len(payload):
                break
            height = int.from_bytes(payload[index + 3:index + 5], "big")
            width = int.from_bytes(payload[index + 5:index + 7], "big")
            if width <= 0 or height <= 0:
                raise InvalidMediaAssetError("Invalid JPEG dimensions.")
            return "image/jpeg", ".jpg", width, height

        index += segment_length

    raise InvalidMediaAssetError("Could not read JPEG dimensions.")


def _detect_media_format(payload: bytes) -> tuple[str, str, int, int]:
    for detector in (_detect_png, _detect_jpeg):
        detected = detector(payload)
        if detected is not None:
            return detected
    raise InvalidMediaAssetError("Unsupported media format. Only PNG and JPEG are allowed.")


def _read_upload_bytes(file_obj: BinaryIO) -> bytes:
    max_bytes = get_upload_max_bytes()
    payload = file_obj.read(max_bytes + 1)
    if not payload:
        raise InvalidMediaAssetError("Uploaded file is empty.")
    if len(payload) > max_bytes:
        raise InvalidMediaAssetError(f"Uploaded file exceeds {max_bytes} bytes.")
    return payload


def validate_upload(
    file_obj: BinaryIO,
    *,
    filename: str,
    content_type: str | None,
    kind: str,
) -> dict:
    normalized_kind = normalize_media_kind(kind)
    payload = _read_upload_bytes(file_obj)
    detected_mime_type, extension, width, height = _detect_media_format(payload)
    declared_mime_type = _normalize_content_type(content_type)
    allowed_extensions = ALLOWED_MEDIA_FORMATS[detected_mime_type]
    provided_extension = Path(filename or "").suffix.lower()

    if declared_mime_type != detected_mime_type:
        raise InvalidMediaAssetError(
            f"MIME type mismatch. Declared {declared_mime_type}, detected {detected_mime_type}."
        )

    if provided_extension not in allowed_extensions:
        allowed_list = ", ".join(sorted(allowed_extensions))
        raise InvalidMediaAssetError(f"Unsupported file extension. Allowed extensions: {allowed_list}.")

    return {
        "kind": normalized_kind,
        "mime_type": detected_mime_type,
        "extension": extension,
        "width": width,
        "height": height,
        "byte_size": len(payload),
        "checksum_sha256": hashlib.sha256(payload).hexdigest(),
        "payload": payload,
    }


def save_upload(file_obj: BinaryIO, *, filename: str, content_type: str | None, asset_id: uuid.UUID, kind: str) -> dict:
    media_root = get_media_root()
    validated = validate_upload(
        file_obj,
        filename=filename,
        content_type=content_type,
        kind=kind,
    )
    storage_key = f"{asset_id}{validated['extension']}"
    target_path = media_root / storage_key

    with tempfile.NamedTemporaryFile(dir=str(media_root), delete=False) as temp_file:
        temp_file.write(validated["payload"])
        temp_path = Path(temp_file.name)
    os.replace(temp_path, target_path)

    validated.pop("payload", None)
    validated["storage_key"] = storage_key
    validated["path"] = target_path
    return validated


def resolve_storage_path(storage_key: str) -> Path:
    return get_media_root() / storage_key


def storage_path_exists(storage_key: str) -> bool:
    return resolve_storage_path(storage_key).exists()


def delete_storage_path(storage_key: str) -> None:
    path = resolve_storage_path(storage_key)
    if path.exists():
        path.unlink()
