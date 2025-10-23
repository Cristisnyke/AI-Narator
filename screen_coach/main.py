"""Entry point for the AI-powered screen coaching overlay."""
from __future__ import annotations

import argparse
import base64
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv
from mss import mss
from openai import OpenAI
from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .overlay import OverlayWindow
from .utils import (
    compute_digest,
    compress_image,
    get_active_window_title,
    has_significant_change,
    parse_region_config,
    redact_regions,
    resize_image,
)

DEFAULT_PROMPT = (
    "You are Screen Coach, a concise assistant observing the user's current task. "
    "Provide a short actionable suggestion (max 2 sentences) based on the visible "
    "screen. Focus on helpful tips, avoid repeating yourself unless something "
    "significant changes."
)


def capture_frame(grabber: mss, monitor: int | dict | None = None) -> Image.Image:
    """Capture a screenshot using *grabber* returning a PIL image."""

    monitor_config = monitor if monitor is not None else grabber.monitors[0]
    raw = grabber.grab(monitor_config)
    return Image.frombytes("RGB", raw.size, raw.rgb)


def encode_frame(image: Image.Image, prefer_webp: bool = True) -> tuple[bytes, str]:
    """Resize and compress *image* ready for API upload."""

    processed = resize_image(image)
    fmt = "WEBP" if prefer_webp else "JPEG"
    return compress_image(processed, format=fmt, quality=80)


def create_client() -> OpenAI:
    """Instantiate an OpenAI client with environment configuration."""

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured. Set it in your .env file.")
    return OpenAI(api_key=api_key)


def analyze_frame(client: OpenAI, prompt: str, payload: bytes, mime_type: str) -> str:
    """Send the frame to the vision model and return textual observations."""

    encoded = base64.b64encode(payload).decode("ascii")
    response = client.responses.create(
        model=os.getenv("SCREEN_COACH_MODEL", "gpt-4o-mini"),
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_base64": encoded, "media_type": mime_type},
                ],
            }
        ],
        max_output_tokens=int(os.getenv("SCREEN_COACH_MAX_TOKENS", "200")),
    )
    return response.output_text.strip()


def should_skip_window(allowed_keywords: List[str]) -> bool:
    if not allowed_keywords:
        return False
    title = get_active_window_title()
    if title is None:
        return False
    lowered = title.lower()
    return not any(keyword.lower() in lowered for keyword in allowed_keywords)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Screen Coach")
    parser.add_argument("--interval", type=float, default=float(os.getenv("SCREEN_COACH_INTERVAL", 2.0)))
    parser.add_argument(
        "--window-keywords",
        type=lambda value: [chunk.strip() for chunk in value.split(",") if chunk.strip()],
        default=[
            chunk.strip()
            for chunk in os.getenv("SCREEN_COACH_WINDOW_KEYWORDS", "").split(",")
            if chunk.strip()
        ],
        help="Only analyze when the active window contains one of these keywords.",
    )
    parser.add_argument(
        "--redact",
        default=os.getenv("SCREEN_COACH_REDACT", ""),
        help="Semicolon separated left,top,right,bottom regions to redact before upload.",
    )
    parser.add_argument(
        "--prompt",
        default=os.getenv("SCREEN_COACH_PROMPT", DEFAULT_PROMPT),
        help="Prompt to send alongside the frame.",
    )
    parser.add_argument(
        "--no-webp",
        action="store_true",
        help="Force JPEG encoding instead of WebP.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    client = create_client()

    app = QApplication.instance() or QApplication(sys.argv)
    overlay = OverlayWindow()
    overlay.show()

    grabber = mss()
    try:
        regions = parse_region_config(args.redact)
    except ValueError as exc:
        overlay.update_text(f'Invalid redaction config: {exc}')
        regions = []

    last_payload_digest: Optional[str] = None
    last_image: Optional[Image.Image] = None
    last_message: str = ""

    def process_frame() -> None:
        nonlocal last_payload_digest, last_image, last_message

        if should_skip_window(args.window_keywords):
            overlay.update_text("Waiting for target window…")
            return

        try:
            screenshot = capture_frame(grabber)
        except Exception as exc:  # pragma: no cover - UI feedback path
            overlay.update_text(f"Capture failed: {exc}")
            return

        if regions:
            screenshot = redact_regions(screenshot, regions)

        if not has_significant_change(screenshot, last_image):
            return

        payload, mime = encode_frame(screenshot, prefer_webp=not args.no_webp)
        digest_hash = compute_digest(payload)

        if last_payload_digest == digest_hash:
            return

        try:
            message = analyze_frame(client, args.prompt, payload, mime)
        except Exception as exc:  # pragma: no cover - UI feedback path
            overlay.update_text(f"Analysis failed: {exc}")
            return

        if not message:
            return

        if message != last_message:
            overlay.update_text(message)
            last_message = message

        last_payload_digest = digest_hash
        last_image = screenshot

    timer = QTimer()
    timer.timeout.connect(process_frame)
    timer.start(int(args.interval * 1000))

    overlay.update_text("Screen Coach listening…")
    app.exec()
    grabber.close()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
