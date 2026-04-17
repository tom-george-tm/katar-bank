from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image, ImageOps

DESKEW_THRESHOLD_DEGREES = 1.5  # rotate when skew > 1.5°
DESKEW_MAX_ABS_DEGREES = 20.0
PDF_RENDER_DPI = 300
PDF_NATIVE_MIN_WORDS = 20
PDF_NATIVE_MIN_TEXT_CHARS = 40
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LINE_SKEW_MIN_SAMPLES = 5

GAMMA_TARGET_BRIGHTNESS = 180   # target mean brightness for a clean document
GAMMA_MIN = 0.7                 # never brighten more aggressively than this
GAMMA_MAX = 1.1                 # never darken more than this
GAMMA_SKIP_TOLERANCE = 10       # skip gamma if mean is within this range of target


def preprocess_for_ocr(file_content: bytes, mime_type: str) -> tuple[bytes, str, dict]:
    """Top-level entry: route files to the appropriate preprocessing path based on MIME type."""
    if mime_type == "application/pdf":
        return preprocess_pdf_for_ocr(file_content)
    if mime_type.startswith("image/"):
        return preprocess_image_for_ocr(file_content)
    return file_content, mime_type, build_preprocessing_metadata(mime_type, False)


def preprocess_image_for_ocr(file_content: bytes) -> tuple[bytes, str, dict]:
    """Preprocess a single image (deskew, enhance) and return PNG bytes plus metadata."""
    source_image = Image.open(BytesIO(file_content))
    processed_image, deskew_applied = preprocess_pil_image(source_image)
    processed_image = enhance_for_ocr(processed_image)

    output_buffer = BytesIO()
    processed_image.save(output_buffer, format="PNG")
    return (
        output_buffer.getvalue(),
        "image/png",
        build_preprocessing_metadata("image/png", deskew_applied),
    )


def preprocess_pdf_for_ocr(file_content: bytes) -> tuple[bytes, str, dict]:
    """Preprocess a PDF by detecting native vs scanned and rasterizing + enhancing when needed."""
    document = fitz.open(stream=file_content, filetype="pdf")
    pdf_type = detect_pdf_type(document)
    if pdf_type == "native":
        document.close()
        return (
            file_content,
            "application/pdf",
            build_preprocessing_metadata(
                "application/pdf",
                False,
                pdf_type=pdf_type,
                rasterization_applied=False,
            ),
        )

    processed_pages: list[Image.Image] = []
    deskew_applied = False

    for page in document:
        pixmap = page.get_pixmap(dpi=PDF_RENDER_DPI, colorspace=fitz.csGRAY, alpha=False)
        page_image = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
        processed_page, page_deskew_applied = preprocess_pil_image(page_image)
        processed_page = enhance_for_ocr(processed_page)
        processed_pages.append(processed_page.convert("RGB"))
        deskew_applied = deskew_applied or page_deskew_applied

    if not processed_pages:
        document.close()
        return (
            file_content,
            "application/pdf",
            build_preprocessing_metadata(
                "application/pdf",
                False,
                pdf_type=pdf_type,
                rasterization_applied=False,
            ),
        )

    output_buffer = BytesIO()
    first_page, *remaining_pages = processed_pages
    first_page.save(
        output_buffer,
        format="PDF",
        save_all=bool(remaining_pages),
        append_images=remaining_pages,
        resolution=PDF_RENDER_DPI,
    )
    document.close()
    return (
        output_buffer.getvalue(),
        "application/pdf",
        build_preprocessing_metadata(
            "application/pdf",
            deskew_applied,
            pdf_type=pdf_type,
            rasterization_applied=True,
        ),
    )


def preprocess_pil_image(source_image: Image.Image) -> tuple[Image.Image, bool]:
    """Normalize orientation/alpha, then optionally deskew the image; returns processed image and flag."""
    normalized_image = normalize_image(source_image)  # RGB
    gray = np.array(normalized_image.convert("L"))
    skew_angle = detect_skew_angle(gray)
    if abs(skew_angle) <= DESKEW_THRESHOLD_DEGREES:
        return normalized_image, False  # keep RGB when no deskew (preserves color for OCR)
    return deskew_image(normalized_image.convert("L"), skew_angle), True  # deskew uses grayscale


def build_preprocessing_metadata(
    input_mime: str,
    deskew_applied: bool,
    pdf_type: str | None = None,
    rasterization_applied: bool = False,
) -> dict:
    """Build a metadata dict describing how the document image was preprocessed."""
    metadata = {
        "input_mime": input_mime,
        "deskew_applied": deskew_applied,
        "rasterization_applied": rasterization_applied,
    }
    if pdf_type is not None:
        metadata["pdf_type"] = pdf_type
    return metadata


def detect_pdf_type(document: fitz.Document) -> str:
    """Heuristically decide whether a PDF is 'native' text or a scanned image-only PDF."""
    for page in document:
        words = page.get_text("words")
        text = page.get_text("text").strip()
        if len(words) >= PDF_NATIVE_MIN_WORDS or len(text) >= PDF_NATIVE_MIN_TEXT_CHARS:
            return "native"
    return "scanned"


def get_extension_for_mime_type(mime_type: str) -> str:
    """Return a reasonable file extension for a given MIME type (fallback to .bin)."""
    extension_map = {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
    }
    return extension_map.get(mime_type, ".bin")


def normalize_image(source_image: Image.Image) -> Image.Image:
    """Normalize EXIF orientation and alpha, returning an RGB image suitable for subsequent OCR steps."""
    image = ImageOps.exif_transpose(source_image)

    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGBA", image.size, "white")
        background.alpha_composite(image.convert("RGBA"))
        image = background.convert("RGB")
    elif image.mode == "P":
        image = image.convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        background.alpha_composite(image)
        image = background.convert("RGB")
    else:
        image = image.convert("RGB")

    return image


def detect_skew_angle(grayscale_array: np.ndarray) -> float:
    """Estimate overall skew angle of a page using line-based and foreground-based methods."""
    line_angle = estimate_text_line_skew_angle(grayscale_array)
    if line_angle is not None:
        return clamp_skew_angle(line_angle)

    foreground_angle = estimate_foreground_skew_angle(grayscale_array)
    return clamp_skew_angle(foreground_angle)


def estimate_text_line_skew_angle(grayscale_array: np.ndarray) -> float | None:
    """Estimate skew from detected long text lines; return None if not enough evidence."""
    height, width = grayscale_array.shape[:2]
    _, binary = cv2.threshold(
        grayscale_array,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    lines = cv2.HoughLinesP(
        binary,
        1,
        np.pi / 180,
        threshold=max(80, width // 12),
        minLineLength=max(100, width // 6),
        maxLineGap=max(20, width // 100),
    )
    if lines is None:
        return None

    line_angles: list[float] = []
    for line in lines[:, 0, :]:
        x1, y1, x2, y2 = line
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if abs(angle) <= DESKEW_MAX_ABS_DEGREES:
            line_angles.append(angle)

    if len(line_angles) < LINE_SKEW_MIN_SAMPLES:
        return None
    return float(-np.median(line_angles))


def estimate_foreground_skew_angle(grayscale_array: np.ndarray) -> float:
    """Fallback skew estimate based on the orientation of all foreground pixels."""
    _, binary = cv2.threshold(
        grayscale_array,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    foreground_points = cv2.findNonZero(binary)
    if foreground_points is None or len(foreground_points) < 50:
        return 0.0

    angle = cv2.minAreaRect(foreground_points)[-1]
    if angle < -45:
        return float(-(90 + angle))
    return float(-angle)


def clamp_skew_angle(angle: float) -> float:
    """Clamp extreme skew values to 0° to avoid over-rotating noisy pages."""
    if abs(angle) > DESKEW_MAX_ABS_DEGREES:
        return 0.0
    return angle


def deskew_image(grayscale_image: Image.Image, skew_angle: float) -> Image.Image:
    """Rotate a grayscale image to correct for the estimated skew angle."""
    grayscale_array = np.array(grayscale_image)
    height, width = grayscale_array.shape[:2]
    rotation_matrix = cv2.getRotationMatrix2D((width / 2, height / 2), -skew_angle, 1.0)
    rotated = cv2.warpAffine(
        grayscale_array,
        rotation_matrix,
        (width, height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    return Image.fromarray(rotated, mode="L")


def enhance_for_ocr(pil_image: Image.Image) -> Image.Image:
    """Enhance the page contrast using an automatically chosen gamma based on brightness."""
    if pil_image.mode == "RGB":
        gray_for_mean = np.array(pil_image.convert("L"))
    else:
        gray_for_mean = np.array(pil_image)

    gamma = _compute_auto_gamma(gray_for_mean)
    if gamma is None:
        return pil_image

    if pil_image.mode == "RGB":
        arr = np.array(pil_image)
        arr = _apply_gamma(arr, gamma)
        return Image.fromarray(arr, mode="RGB")
    else:
        gray = np.array(pil_image)
        gray = _apply_gamma(gray, gamma)
        return Image.fromarray(gray, mode="L")


def _compute_auto_gamma(grayscale_array: np.ndarray) -> float | None:
    """Derive a gamma value that nudges the mean brightness toward the configured target."""
    mean = float(np.mean(grayscale_array))
    if mean < 1.0:
        return None
    if abs(mean - GAMMA_TARGET_BRIGHTNESS) <= GAMMA_SKIP_TOLERANCE:
        return None
    import math
    gamma = math.log(GAMMA_TARGET_BRIGHTNESS / 255.0) / math.log(mean / 255.0)
    gamma = max(GAMMA_MIN, min(GAMMA_MAX, gamma))
    return gamma


def _apply_gamma(img: np.ndarray, gamma: float) -> np.ndarray:
    """Apply a gamma correction LUT to an image array."""
    invGamma = 1.0 / gamma
    table = np.array(
        [(i / 255.0) ** invGamma * 255 for i in range(256)], dtype=np.uint8
    )
    return cv2.LUT(img, table)
