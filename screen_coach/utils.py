"""Utility helpers for screen capture preprocessing and privacy controls."""
from __future__ import annotations

import hashlib
import io
import platform
import subprocess
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageFilter


@dataclass(frozen=True)
class Region:
    """Represents a rectangular region on screen (left, top, right, bottom)."""

    left: int
    top: int
    right: int
    bottom: int

    @classmethod
    def from_tuple(cls, coords: Sequence[int]) -> "Region":
        if len(coords) != 4:
            raise ValueError("Region requires four integers: left, top, right, bottom")
        l, t, r, b = map(int, coords)
        if r <= l or b <= t:
            raise ValueError("Invalid region dimensions")
        return cls(l, t, r, b)


def resize_image(image: Image.Image, max_size: Tuple[int, int] = (1280, 720)) -> Image.Image:
    """Resize an image to fit within *max_size* while preserving aspect ratio."""

    image = image.copy()
    image.thumbnail(max_size, Image.LANCZOS)
    return image


def compress_image(
    image: Image.Image,
    *,
    format: str = "JPEG",
    quality: int = 85,
    optimize: bool = True,
) -> Tuple[bytes, str]:
    """Encode *image* to compressed bytes.

    Returns a tuple of (bytes, mime_type).
    """

    buffer = io.BytesIO()
    fmt = format.upper()
    if fmt not in {"JPEG", "JPG", "WEBP"}:
        fmt = "JPEG"
    mime = "image/jpeg" if fmt in {"JPEG", "JPG"} else "image/webp"
    save_kwargs = {"format": fmt, "quality": quality, "optimize": optimize}
    if fmt == "WEBP":
        save_kwargs.setdefault("method", 6)
    image.save(buffer, **save_kwargs)
    return buffer.getvalue(), mime


def redact_regions(
    image: Image.Image,
    regions: Iterable[Region],
    *,
    blur_radius: int = 25,
    fill_color: Tuple[int, int, int] | None = (0, 0, 0),
) -> Image.Image:
    """Apply redaction to rectangular *regions* within *image*.

    The redaction either blurs the region or fills it with *fill_color* if provided.
    """

    processed = image.copy()
    for region in regions:
        box = (region.left, region.top, region.right, region.bottom)
        crop = processed.crop(box)
        if fill_color is None:
            crop = crop.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        else:
            crop = Image.new("RGB", crop.size, fill_color)
        processed.paste(crop, box)
    return processed


def compute_digest(data: bytes) -> str:
    """Return a short digest of *data* for change detection."""

    return hashlib.sha1(data).hexdigest()


def has_significant_change(
    current: Image.Image,
    previous: Optional[Image.Image],
    *,
    threshold: float = 8.0,
) -> bool:
    """Determine if *current* differs from *previous* by more than *threshold* RMS."""

    if previous is None:
        return True
    diff = ImageChops.difference(current, previous)
    histogram = diff.histogram()
    squares = (value * ((idx % 256) ** 2) for idx, value in enumerate(histogram))
    total_pixels = current.size[0] * current.size[1] * 3
    rms = (sum(squares) / float(total_pixels)) ** 0.5
    return rms >= threshold


def parse_region_config(config: str | None) -> List[Region]:
    """Parse a redaction configuration string into Region objects.

    Accepts semi-colon separated "left,top,right,bottom" entries.
    """

    if not config:
        return []
    regions: List[Region] = []
    for chunk in config.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        coords = [int(part) for part in chunk.split(",") if part.strip()]
        regions.append(Region.from_tuple(coords))
    return regions


def get_active_window_title() -> Optional[str]:
    """Best-effort active window title lookup.

    Returns ``None`` if the platform is unsupported or the title cannot be determined.
    """

    system = platform.system()
    try:
        if system == "Windows":
            import ctypes  # type: ignore

            user32 = ctypes.windll.user32
            handle = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(handle)
            if length == 0:
                return None
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(handle, buffer, length + 1)
            return buffer.value or None
        if system == "Darwin":
            from AppKit import NSWorkspace  # type: ignore

            active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if active_app:
                return active_app.localizedName()
            return None
        if system == "Linux":
            try:
                proc = subprocess.run(
                    [
                        "xdotool",
                        "getwindowfocus",
                        "getwindowname",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                title = proc.stdout.strip()
                return title or None
            except Exception:
                return None
    except Exception:
        return None
    return None


__all__ = [
    "Region",
    "resize_image",
    "compress_image",
    "redact_regions",
    "compute_digest",
    "has_significant_change",
    "parse_region_config",
    "get_active_window_title",
]
