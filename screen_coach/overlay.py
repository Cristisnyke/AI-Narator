"""Overlay widget for presenting coaching feedback."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class OverlayWindow(QWidget):
    """Simple always-on-top overlay to present textual updates."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus)
        self.setWindowTitle("Screen Coach")

        self._label = QLabel("Screen Coach ready")
        font = QFont("Segoe UI", 14)
        font.setBold(True)
        self._label.setFont(font)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(
            "color: white; background-color: rgba(0, 0, 0, 180); padding: 12px;"
        )

        layout = QVBoxLayout()
        layout.addWidget(self._label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.geometry()
            self.resize(int(geometry.width() * 0.3), 140)
            self.move(geometry.width() - self.width() - 40, 40)
        else:  # pragma: no cover - depends on runtime environment
            self.resize(420, 140)

    def update_text(self, text: str) -> None:
        self._label.setText(text)


__all__ = ["OverlayWindow"]
