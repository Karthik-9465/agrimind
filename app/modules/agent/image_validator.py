import base64
import io
from PIL import Image

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024 # 10 MB limit
ALLOWED_FORMATS = {"JPEG", "PNG"}

def validate_and_decode_image(image_b64: str) -> bytes:
    """
    Decodes and validates a Base64 encoded image string using Pillow (PIL).
    Returns decoded raw image bytes.
    Raises ValueError on validation failure.
    """
    if not image_b64 or not image_b64.strip():
        raise ValueError("Image payload is empty.")

    # Strip data URL prefix if present (e.g. data:image/png;base64,...)
    clean_b64 = image_b64.strip()
    if "," in clean_b64:
        clean_b64 = clean_b64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(clean_b64, validate=True)
    except Exception as e:
        raise ValueError("Invalid Base64 image string encoding.") from e

    if not image_bytes:
        raise ValueError("Decoded image content is 0 bytes.")

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"Image file size ({len(image_bytes) / (1024*1024):.2f} MB) exceeds maximum permitted limit of 10 MB.")

    try:
        # Load and verify image with Pillow
        stream = io.BytesIO(image_bytes)
        img = Image.open(stream)
        img.verify()

        # Re-open stream for format inspection after verify()
        stream.seek(0)
        img = Image.open(stream)
        fmt = (img.format or "").upper()

        if fmt not in ALLOWED_FORMATS:
            raise ValueError(f"Unsupported image format '{fmt}'. Only JPEG and PNG formats are accepted.")

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Corrupted or invalid image structure: {str(e)}") from e

    return image_bytes
