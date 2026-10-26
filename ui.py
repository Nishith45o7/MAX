from __future__ import annotations
from max_brain import run_agent
import collections
import html
import json
import math
import os
import platform
import random
import re
import sys
import threading
import time
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QThread, QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QCursor, QDragEnterEvent, QDropEvent, QFont,
    QFontDatabase, QKeySequence, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient, QShortcut, QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QStackedWidget,
)


# ═══════════════════════════ AGENT WORKER THREAD ══════════════════════════════
class AgentWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def run(self):
        try:
            output = run_agent(self.prompt)
            self.response_ready.emit(output)
        except Exception as e:
            self.response_ready.emit(f"ERR: {str(e)}")


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 1260, 840
_MIN_W,     _MIN_H     = 880, 580
_OS = platform.system()


# ═══════════════════════════ PURE BLACK THEME SYSTEM ══════════════════════════
class Theme:
    """Flagship AI Theme supporting Pure Pitch Black (OLED) and Minimal Crisp Light."""
    def __init__(self, dark: bool = True):
        self.dark = dark
        if dark:
            # ── PURE PITCH BLACK (ChatGPT / Claude / Gemini OLED Dark) ──
            self.bg_app         = "#000000"     # Pure Black Canvas
            self.bg_sidebar     = "#09090B"     # Sleek Obsidian
            self.bg_chat        = "#000000"     # Pure Black Stream
            self.bg_card        = "#111114"     # Subtle card background
            self.bg_card_hover  = "#18181C"     # Card hover state
            self.bg_user_bubble = "#1A1A1E"     # User chat bubble
            self.bg_input       = "#111114"     # Input pill container
            self.bg_hover       = "#18181B"     # Hover state
            self.bg_active      = "#222226"     # Active button

            self.border         = "rgba(255, 255, 255, 0.09)"
            self.border_subtle  = "rgba(255, 255, 255, 0.05)"
            self.border_hover   = "rgba(255, 255, 255, 0.20)"

            self.text_pri       = "#FFFFFF"     # Crisp White
            self.text_sec       = "#A1A1AA"     # Secondary Gray
            self.text_dim       = "#71717A"     # Muted / Placeholder

            # Flagship AI Accents
            self.accent         = "#10A37F"     # ChatGPT Emerald Green
            self.accent_hover   = "#1A7F64"
            self.think          = "#38BDF8"     # Electric Sky Cyan
            self.speak          = "#818CF8"     # Soft Indigo / Violet
            self.aurora_pink    = "#F472B6"     # Gemini Aurora Fuchsia
            self.muted          = "#EF4444"     # Coral Red

            self.send_btn_bg    = "#FFFFFF"
            self.send_btn_fg    = "#000000"
            self.code_bg        = "#09090B"
            self.code_header    = "#18181B"
            self.scroll_thumb   = "rgba(255, 255, 255, 0.16)"
            self.scroll_thumb_h = "rgba(255, 255, 255, 0.32)"
        else:
            # ── MINIMAL CRISP LIGHT (Claude / ChatGPT Light) ──
            self.bg_app         = "#FFFFFF"
            self.bg_sidebar     = "#F9FAFB"
            self.bg_chat        = "#FFFFFF"
            self.bg_card        = "#F3F4F6"
            self.bg_card_hover  = "#E5E7EB"
            self.bg_user_bubble = "#F3F4F6"
            self.bg_input       = "#F3F4F6"
            self.bg_hover       = "#E5E7EB"
            self.bg_active      = "#D1D5DB"

            self.border         = "rgba(0, 0, 0, 0.08)"
            self.border_subtle  = "rgba(0, 0, 0, 0.04)"
            self.border_hover   = "rgba(0, 0, 0, 0.18)"

            self.text_pri       = "#111827"
            self.text_sec       = "#4B5563"
            self.text_dim       = "#9CA3AF"

            self.accent         = "#10A37F"
            self.accent_hover   = "#0D8A6A"
            self.think          = "#0284C7"
            self.speak          = "#6366F1"
            self.aurora_pink    = "#DB2777"
            self.muted          = "#DC2626"

            self.send_btn_bg    = "#111827"
            self.send_btn_fg    = "#FFFFFF"
            self.code_bg        = "#F9FAFB"
            self.code_header    = "#F3F4F6"
            self.scroll_thumb   = "rgba(0, 0, 0, 0.14)"
            self.scroll_thumb_h = "rgba(0, 0, 0, 0.28)"


def qcol(h: str, a: int = 255) -> QColor:
    if h.startswith("rgba"):
        try:
            parts = h.replace("rgba(", "").replace(")", "").split(",")
            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
            alpha = int(float(parts[3]) * 255) if len(parts) > 3 else a
            return QColor(r, g, b, alpha)
        except Exception:
            pass
    c = QColor(h)
    c.setAlpha(a)
    return c


def get_ui_font(size: float | int = 9, bold: bool = False, mono: bool = False) -> QFont:
    family = "Consolas" if mono else "Segoe UI"
    f = QFont(family, int(round(size)))
    if bold:
        f.setWeight(QFont.Weight.DemiBold)
    return f


# ═══════════════════════════ CLAUDE / CHATGPT MARKDOWN FORMATTER ══════════════
def markdown_to_chat_html(text: str, theme: Theme) -> str:
    """Format markdown text cleanly with syntax code cards, headers, tables, and lists."""
    safe = html.escape(text)

    # 1. Code blocks ```lang\ncode\n```
    def replace_code_block(m):
        lang = (m.group(1) or "code").upper()
        code_body = m.group(2).strip()
        return (
            f"<div style='background: {theme.code_bg}; border: 1px solid {theme.border}; "
            f"border-radius: 8px; margin: 12px 0; overflow: hidden;'>"
            f"<div style='background: {theme.code_header}; padding: 6px 14px; font-size: 7.5pt; "
            f"color: {theme.text_sec}; border-bottom: 1px solid {theme.border_subtle}; font-family: Consolas, monospace; "
            f"font-weight: 600; letter-spacing: 0.5px;'>{lang}</div>"
            f"<div style='padding: 12px 14px; font-family: Consolas, monospace; font-size: 8.8pt; "
            f"color: {theme.text_pri}; white-space: pre-wrap; line-height: 1.48;'>{code_body}</div>"
            f"</div>"
        )
    safe = re.sub(r'```([a-zA-Z0-9_-]+)?\n(.*?)```', replace_code_block, safe, flags=re.DOTALL)

    # 2. Inline code `code`
    safe = re.sub(
        r'`([^`]+)`',
        rf"<span style='background: {theme.code_bg}; border: 1px solid {theme.border_subtle}; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 8.5pt; color: {theme.think};'>\1</span>",
        safe
    )

    # 3. Bold text **text**
    safe = re.sub(r'\*\*([^*]+)\*\*', r'<b style="font-weight: 600; color: ' + theme.text_pri + r';">\1</b>', safe)

    # 4. Italic text *text* or _text_
    safe = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i style="color: ' + theme.text_sec + r';">\1</i>', safe)

    # 5. Headers & Bullet lists
    lines = safe.split('\n')
    in_list = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            item = stripped[2:].strip()
            if not in_list:
                new_lines.append("<ul style='margin: 4px 0 6px 18px; padding-left: 0;'>")
                in_list = True
            new_lines.append(f"<li style='margin-bottom: 4px; line-height: 1.5;'>{item}</li>")
        elif stripped.startswith("### "):
            if in_list:
                new_lines.append("</ul>")
                in_list = False
            new_lines.append(f"<div style='font-size: 10.5pt; font-weight: 600; margin: 10px 0 4px 0; color: {theme.text_pri};'>{stripped[4:]}</div>")
        elif stripped.startswith("## "):
            if in_list:
                new_lines.append("</ul>")
                in_list = False
            new_lines.append(f"<div style='font-size: 11.5pt; font-weight: 600; margin: 12px 0 4px 0; color: {theme.text_pri};'>{stripped[3:]}</div>")
        elif stripped.startswith("# "):
            if in_list:
                new_lines.append("</ul>")
                in_list = False
            new_lines.append(f"<div style='font-size: 13pt; font-weight: 700; margin: 14px 0 6px 0; color: {theme.text_pri};'>{stripped[2:]}</div>")
        elif stripped.startswith("> "):
            if in_list:
                new_lines.append("</ul>")
                in_list = False
            new_lines.append(f"<div style='border-left: 3px solid {theme.accent}; padding-left: 10px; margin: 6px 0; color: {theme.text_sec}; font-style: italic;'>{stripped[2:]}</div>")
        else:
            if in_list:
                new_lines.append("</ul>")
                in_list = False
            new_lines.append(line)
    if in_list:
        new_lines.append("</ul>")

    res = "\n".join(new_lines)
    res = res.replace("\n", "<br>")
    res = re.sub(r'<br>\s*<ul', '<ul', res)
    res = re.sub(r'</ul>\s*<br>', '</ul>', res)
    return res


# ═══════════════════════════ FLOATING AUDIO SOUNDWAVE ══════════════════════════
class FloatingWaveWidget(QWidget):
    """
    Sleek, fluid audio soundwave capsule (Gemini Live / ChatGPT Advanced Voice):
    - 8 fluid multi-harmonic equalizer bars undulating organically with audio frequencies.
    - Gemini's signature multi-color gradient spectrum (cyan -> violet -> pink) during speech.
    - Shows real-time speech / transcription status.
    - Clickable to mute/unmute or toggle voice mode.
    """
    clicked = pyqtSignal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.state = "LISTENING"
        self.speaking = False
        self.muted = False
        self.live_transcription = ""

        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(20)

    def set_theme(self, theme: Theme):
        self._theme = theme
        self.update()

    def set_state(self, state: str):
        self.state = state
        self.speaking = (state == "SPEAKING")
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def _step(self):
        # Multi-frequency phase advance for smooth organic motion
        self._phase += 0.15
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        W, H = self.width(), self.height()

        rect = QRectF(0, 0, W, H).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, H / 2.0, H / 2.0)

        # Translucent pitch dark capsule with fine border
        bg_col = qcol("#0D0D10" if self._theme.dark else "#F3F4F6", 240)
        p.fillPath(path, QBrush(bg_col))
        p.setPen(QPen(qcol(self._theme.border), 1.0))
        p.drawPath(path)

        if self.muted:
            status_txt = "Microphone muted — click to unmute [F4]"
        elif self.state == "THINKING":
            status_txt = "MAX is thinking & reasoning..."
        elif self.state == "SPEAKING" or self.speaking:
            status_txt = "MAX speaking..."
        else:
            status_txt = "Listening to your voice..."

        if self.live_transcription:
            status_txt = f"\"{self.live_transcription[:52]}\""

        # ── 8 Dynamic Multi-Harmonic Equalizer Bars ──
        bar_count = 8
        bar_w = 3.0
        bar_spacing = 3.2
        start_x = 16.0
        mid_y = H / 2.0

        for i in range(bar_count):
            bx = start_x + i * (bar_w + bar_spacing)
            if self.muted:
                bar_h = 3.0
                bar_col = qcol(self._theme.muted)
            elif self.state == "THINKING":
                wave_factor = abs(math.sin(self._phase + i * 0.7))
                bar_h = 4.0 + 12.0 * wave_factor
                bar_col = qcol(self._theme.think)
            elif self.state == "SPEAKING" or self.speaking:
                # Gemini Live multi-harmonic wave
                wave1 = math.sin(self._phase + i * 0.8)
                wave2 = math.cos(self._phase * 1.5 + i * 1.1)
                wave_factor = 0.5 * abs(wave1) + 0.5 * abs(wave2)
                bar_h = 4.0 + 17.0 * wave_factor

                # Vibrant aurora gradient per bar (Cyan -> Indigo -> Fuchsia)
                t = i / max(1, bar_count - 1)
                if t < 0.5:
                    bar_col = qcol(self._theme.think)
                else:
                    bar_col = qcol(self._theme.aurora_pink)
            else:
                # Listening state: smooth organic breathing wave
                wave_factor = abs(math.sin(self._phase * 0.8 + i * 0.6))
                bar_h = 4.0 + 13.0 * wave_factor
                bar_col = qcol(self._theme.accent)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bx, mid_y - bar_h / 2.0, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)

        # ── Status / Live Speech Subtitle ──
        p.setFont(get_ui_font(8.5, bold=True))
        p.setPen(QPen(qcol(self._theme.text_pri)))
        text_x = start_x + bar_count * (bar_w + bar_spacing) + 12.0
        text_w = W - text_x - 36.0
        p.drawText(QRectF(text_x, 0, text_w, H), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, status_txt)

        # ── Action Icon (Right) ──
        icon = "🔇" if self.muted else "🎙"
        p.setFont(get_ui_font(9))
        p.drawText(QRectF(W - 32.0, 0, 24.0, H), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter, icon)


# ═══════════════════════════ REASONING / THINKING CARD ════════════════════════
class ReasoningBlockWidget(QWidget):
    """
    ChatGPT o1 / Gemini 2.0 / Claude 3.7 style Reasoning Block:
    - Collapsible card showing real-time AI thought process and tool execution.
    - Shimmering animated loader.
    - Clickable to expand/collapse thought trace.
    """
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._tick = 0.0
        self._current_step = "Thinking..."
        self._start_time = time.time()
        self._elapsed = 0.0
        self._is_active = True
        self._steps: list[str] = []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(35)

    def _step(self):
        self._tick += 0.12
        if self._is_active:
            self._elapsed = time.time() - self._start_time
        self.update()

    def set_theme(self, theme: Theme):
        self._theme = theme
        self.update()

    def start_thinking(self, initial_step: str = "Thinking..."):
        self._start_time = time.time()
        self._elapsed = 0.0
        self._is_active = True
        self._current_step = initial_step
        self._steps = [initial_step]
        self.show()
        self.update()

    def add_step(self, step: str):
        self._current_step = step
        if step not in self._steps:
            self._steps.append(step)
        self.update()

    def finish_thinking(self):
        self._is_active = False
        self._current_step = f"Thought for {self._elapsed:.1f}s"
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Pill background
        rect = QRectF(0, 2, 230, 30)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        p.fillPath(path, QBrush(qcol(self._theme.bg_card)))
        p.setPen(QPen(qcol(self._theme.border_subtle), 1.0))
        p.drawPath(path)

        # Sparkle emblem ✦
        p.setFont(get_ui_font(9, bold=True))
        p.setPen(QPen(qcol(self._theme.think if self._is_active else self._theme.text_sec)))
        p.drawText(10, 21, "✦")

        # Step text
        p.setFont(get_ui_font(8.5, bold=True))
        p.setPen(QPen(qcol(self._theme.text_pri if self._is_active else self._theme.text_sec)))
        txt = self._current_step[:24]
        p.drawText(26, 21, txt)

        if self._is_active:
            # 3 Shimmering animated dots
            start_x = 180.0
            y = 17.0
            dot_r = 2.2
            for i in range(3):
                alpha = int(90 + 160 * abs(math.sin(self._tick - i * 0.7)))
                p.setBrush(QBrush(qcol(self._theme.think, alpha)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(start_x + i * 7.5, y), dot_r, dot_r)
        else:
            # Chevron
            p.setFont(get_ui_font(7))
            p.setPen(QPen(qcol(self._theme.text_dim)))
            p.drawText(206, 20, "▾")


# ═══════════════════════════ AUTO-EXPANDING PROMPT TEXT EDIT ═══════════════════
class PromptTextEdit(QTextEdit):
    """
    ChatGPT / Claude style Auto-Expanding Multiline Prompt Box:
    - Automatically grows from 1 line (36px) up to 130px.
    - Pressing Enter sends the message.
    - Pressing Shift+Enter creates a new line.
    - Smooth placeholder text and transparent background.
    """
    send_requested = pyqtSignal()
    height_changed = pyqtSignal()

    def __init__(self, placeholder: str = "Message MAX...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAcceptRichText(False)
        self.setFont(get_ui_font(9.5))
        self.setFixedHeight(36)
        self.textChanged.connect(self._adjust_height)

    def text(self) -> str:
        return self.toPlainText()


    def _adjust_height(self):
        doc = self.document()
        target_h = int(doc.size().height()) + 8
        target_h = max(36, min(130, target_h))
        if self.height() != target_h:
            self.setFixedHeight(target_h)
            self.height_changed.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(e)
                self._adjust_height()
            else:
                self.send_requested.emit()
                e.accept()
        else:
            super().keyPressEvent(e)
            self._adjust_height()



# ═══════════════════════════ GLASS TELEMETRY WIDGET ══════════════════════════
class GlassTelemetryWidget(QFrame):
    """
    Obsidian / Glassmorphic HUD Telemetry widget showing live system vitals:
    - CPU Usage %
    - RAM Usage %
    - Battery level % + charging status
    - Non-blocking QTimer(1000) update cycle without UI stutter
    """
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedHeight(72)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        # Header title
        title_box = QHBoxLayout()
        title_lbl = QLabel("SYSTEM TELEMETRY")
        title_lbl.setFont(get_ui_font(7, bold=True))
        title_lbl.setStyleSheet(f"color: {theme.text_sec}; letter-spacing: 1px;")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        self._status_chip = QLabel("ONLINE")
        self._status_chip.setFont(get_ui_font(6, bold=True))
        self._status_chip.setStyleSheet("color: #10A37F; background: rgba(16, 163, 127, 0.15); border-radius: 4px; padding: 1px 4px;")
        title_box.addWidget(self._status_chip)
        lay.addLayout(title_box)

        # Metrics row
        metrics_box = QHBoxLayout()
        metrics_box.setSpacing(6)

        self._cpu_val = QLabel("CPU --%")
        self._cpu_val.setFont(get_ui_font(7, bold=True))
        metrics_box.addWidget(self._cpu_val)

        self._ram_val = QLabel("RAM --%")
        self._ram_val.setFont(get_ui_font(7, bold=True))
        metrics_box.addWidget(self._ram_val)

        self._batt_val = QLabel("BAT --%")
        self._batt_val.setFont(get_ui_font(7, bold=True))
        metrics_box.addWidget(self._batt_val)

        metrics_box.addStretch()
        lay.addLayout(metrics_box)

        self.apply_theme(theme)

        # Non-blocking update timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_metrics)
        self._timer.start(1000)
        self._update_metrics()

    def _update_metrics(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()

            self._cpu_val.setText(f"CPU {cpu:.0f}%")
            self._ram_val.setText(f"RAM {ram:.0f}%")
            if batt:
                plug = "⚡" if batt.power_plugged else ""
                self._batt_val.setText(f"BAT {batt.percent}%{plug}")
            else:
                self._batt_val.setText("PWR AC")
        except Exception:
            pass

    def apply_theme(self, theme: Theme):
        self._theme = theme
        self.setStyleSheet(f"""
            GlassTelemetryWidget {{
                background: {theme.bg_card};
                border: 1px solid {theme.border};
                border-radius: 8px;
            }}
            QLabel {{
                color: {theme.text_pri};
            }}
        """)


# ═══════════════════════════ CHATGPT SIDEBAR ═════════════════════════════════
class ChatGPTSidebar(QWidget):
    """Authentic ChatGPT Collapsible Left Navigation Sidebar with pure black palette."""
    new_chat_clicked = pyqtSignal()
    toggle_theme_clicked = pyqtSignal()
    toggle_mic_clicked = pyqtSignal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedWidth(260)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(10)

        # 1. New Chat Button (+ New chat)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._new_chat_btn = QPushButton("＋  New chat")
        self._new_chat_btn.setFont(get_ui_font(9, bold=True))
        self._new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_chat_btn.setFixedHeight(38)
        self._new_chat_btn.clicked.connect(self.new_chat_clicked.emit)
        top_row.addWidget(self._new_chat_btn, stretch=1)

        lay.addLayout(top_row)

        # 2. History Section Header
        self._recent_lbl = QLabel("Recent Conversations")
        self._recent_lbl.setFont(get_ui_font(7.5, bold=True))
        lay.addWidget(self._recent_lbl)

        # Scrollable session list
        self._session_list_widget = QWidget()
        self._session_lay = QVBoxLayout(self._session_list_widget)
        self._session_lay.setContentsMargins(0, 0, 0, 0)
        self._session_lay.setSpacing(4)
        self._session_lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._session_list_widget)
        lay.addWidget(scroll, stretch=1)

        self._add_session_item("Active Conversation", is_active=True)
        self._add_session_item("System Diagnostics & Audio")
        self._add_session_item("Live Multimodal Vision")

        # 3. Bottom Controls Area
        bottom_box = QFrame()
        b_lay = QVBoxLayout(bottom_box)
        b_lay.setContentsMargins(0, 8, 0, 0)
        b_lay.setSpacing(4)

        # Live Glass Telemetry HUD
        self._telemetry = GlassTelemetryWidget(theme)
        b_lay.addWidget(self._telemetry)

        # Theme Switcher
        self._theme_btn = QPushButton("🌙  Pure Black" if theme.dark else "☀️  Light mode")
        self._theme_btn.setFont(get_ui_font(8))
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_btn.setFixedHeight(34)
        self._theme_btn.clicked.connect(self.toggle_theme_clicked.emit)
        b_lay.addWidget(self._theme_btn)

        # Mic Toggle
        self._mic_btn = QPushButton("🎙  Voice active [F4]")
        self._mic_btn.setFont(get_ui_font(8))
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setFixedHeight(34)
        self._mic_btn.clicked.connect(self.toggle_mic_clicked.emit)
        b_lay.addWidget(self._mic_btn)

        # User Profile Badge
        profile_card = QFrame()
        profile_card.setFixedHeight(44)
        p_lay = QHBoxLayout(profile_card)
        p_lay.setContentsMargins(8, 0, 8, 0)
        p_lay.setSpacing(8)

        avatar = QLabel("M")
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFont(get_ui_font(9, bold=True))
        avatar.setStyleSheet("background: #10A37F; color: #FFFFFF; border-radius: 14px;")
        p_lay.addWidget(avatar)

        name_box = QVBoxLayout()
        name_box.setSpacing(1)
        name_lbl = QLabel("MAX Assistant")
        name_lbl.setFont(get_ui_font(8, bold=True))
        sub_lbl = QLabel("Gemini Live Native")
        sub_lbl.setFont(get_ui_font(7))
        self._p_name = name_lbl
        self._p_sub = sub_lbl
        name_box.addWidget(name_lbl)
        name_box.addWidget(sub_lbl)
        p_lay.addLayout(name_box)
        p_lay.addStretch()

        b_lay.addWidget(profile_card)
        self._profile_card = profile_card

        lay.addWidget(bottom_box)
        self.apply_theme(theme)

    def _add_session_item(self, title: str, is_active: bool = False):
        btn = QPushButton(f"💬  {title}")
        btn.setFont(get_ui_font(8))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(32)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {self._theme.bg_active if is_active else 'transparent'};
                color: {self._theme.text_pri if is_active else self._theme.text_sec};
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 10px;
            }}
            QPushButton:hover {{
                background: {self._theme.bg_hover};
                color: {self._theme.text_pri};
            }}
        """)
        self._session_lay.insertWidget(self._session_lay.count() - 1, btn)

    def set_muted(self, muted: bool):
        if muted:
            self._mic_btn.setText("🔇  Voice muted [F4]")
            self._mic_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(239, 68, 68, 0.12);
                    color: {self._theme.muted};
                    border: 1px solid {self._theme.muted};
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }}
            """)
        else:
            self._mic_btn.setText("🎙  Voice active [F4]")
            self._mic_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self._theme.text_sec};
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }}
                QPushButton:hover {{
                    background: {self._theme.bg_hover};
                    color: {self._theme.text_pri};
                }}
            """)

    def apply_theme(self, theme: Theme):
        self._theme = theme
        if hasattr(self, "_telemetry") and self._telemetry:
            self._telemetry.apply_theme(theme)
        self.setStyleSheet(f"""
            ChatGPTSidebar {{
                background: {theme.bg_sidebar};
                border-right: 1px solid {theme.border};
            }}
        """)
        self._new_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background: {theme.bg_card};
                color: {theme.text_pri};
                border: 1px solid {theme.border};
                border-radius: 10px;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton:hover {{
                background: {theme.bg_hover};
                border: 1px solid {theme.border_hover};
            }}
        """)
        self._recent_lbl.setStyleSheet(f"color: {theme.text_dim}; padding-left: 8px; margin-top: 6px;")

        btn_qss = f"""
            QPushButton {{
                background: transparent;
                color: {theme.text_sec};
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 10px;
            }}
            QPushButton:hover {{
                background: {theme.bg_hover};
                color: {theme.text_pri};
            }}
        """
        self._theme_btn.setStyleSheet(btn_qss)
        self._theme_btn.setText("🌙  Pure Black" if theme.dark else "☀️  Light mode")
        self._p_name.setStyleSheet(f"color: {theme.text_pri};")
        self._p_sub.setStyleSheet(f"color: {theme.text_dim};")
        self._profile_card.setStyleSheet(f"background: {theme.bg_card}; border: 1px solid {theme.border_subtle}; border-radius: 10px;")


# ═══════════════════════════ CHATGPT STREAM VIEW ═════════════════════════════
class ChatGPTStream(QWidget):
    """
    ChatGPT Centered Stream with pure pitch black background:
    - Clean greeting hero (NO sphere)
    - Shimmering Reasoning/Thinking block
    - Selectable rich text (TextSelectableByMouse)
    - Message Action Toolbar (Play/Pause, Copy, Like, Dislike)
    - Token streaming animation
    """
    prompt_clicked = pyqtSignal(str)
    stop_speech_clicked = pyqtSignal()
    read_aloud_clicked = pyqtSignal(str)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._messages: list[tuple[str, str, str]] = []
        self._active_stream_timer: QTimer | None = None
        self._active_stream_label: QLabel | None = None
        self._active_stream_text: str = ""
        self._active_stream_index: int = 0

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        # Scroll Area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Center Container
        self._container = QWidget()
        self._cont_lay = QVBoxLayout(self._container)
        self._cont_lay.setContentsMargins(0, 24, 0, 24)
        self._cont_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Inner Content Column (Width constrained like ChatGPT)
        self._column = QWidget()
        self._column.setFixedWidth(760)
        self._col_lay = QVBoxLayout(self._column)
        self._col_lay.setContentsMargins(0, 0, 0, 0)
        self._col_lay.setSpacing(16)

        # ── 1. Hero Empty State (No sphere!) ──
        self._hero_widget = self._build_hero()
        self._col_lay.addWidget(self._hero_widget)

        # ── 2. Message Stream Container ──
        self._msg_widget = QWidget()
        self._msg_lay = QVBoxLayout(self._msg_widget)
        self._msg_lay.setContentsMargins(0, 0, 0, 0)
        self._msg_lay.setSpacing(20)
        self._col_lay.addWidget(self._msg_widget)
        self._msg_widget.hide()

        # ── 3. Reasoning / Thinking Block ──
        self._reasoning_widget = ReasoningBlockWidget(self._theme)
        self._col_lay.addWidget(self._reasoning_widget)
        self._reasoning_widget.hide()

        self._cont_lay.addWidget(self._column)
        self._scroll.setWidget(self._container)
        lay.addWidget(self._scroll)

        self.apply_theme(theme)

    def _build_hero(self) -> QWidget:
        hero = QWidget()
        h_lay = QVBoxLayout(hero)
        h_lay.setContentsMargins(0, 48, 0, 24)
        h_lay.setSpacing(18)
        h_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Circular MAX emblem badge with glowing ring
        badge = QLabel("✦")
        badge.setFixedSize(54, 54)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFont(get_ui_font(20, bold=True))
        badge.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10A37F, stop:1 #38BDF8);
            color: #FFFFFF;
            border-radius: 27px;
        """)
        h_lay.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        # Headline
        self._hero_title = QLabel("What can I help with today?")
        self._hero_title.setFont(get_ui_font(18, bold=True))
        self._hero_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_lay.addWidget(self._hero_title)

        # Subtitle
        self._hero_sub = QLabel("Speak naturally, execute desktop commands, write code, or drop files to inspect.")
        self._hero_sub.setFont(get_ui_font(9))
        self._hero_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_lay.addWidget(self._hero_sub)

        # 2x2 Suggestion Prompt Cards Grid
        grid_col = QVBoxLayout()
        grid_col.setSpacing(10)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        c1 = self._make_card("🔍 Search the web", "Latest news, real-time facts, and research", "Search Google for the latest tech news")
        c2 = self._make_card("📁 Analyze document", "Summarize, extract data, or read PDFs & code", "Analyze the uploaded document and summarize key points")
        row1.addWidget(c1)
        row1.addWidget(c2)
        grid_col.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        c3 = self._make_card("⚙️ Control my system", "Launch apps, adjust volume, take screenshots", "Take a screenshot and inspect my screen")
        c4 = self._make_card("💻 Write & debug code", "Generate Python scripts, fix bugs, or build apps", "Write a fast Python script to analyze CSV data")
        row2.addWidget(c3)
        row2.addWidget(c4)
        grid_col.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(10)
        c5 = self._make_card("🦁 Crew & Org Chart", "View multi-agent hierarchy, Pride chart, and roles", "/org")
        c6 = self._make_card("🧠 System & Memory", "Inspect Tideline persistent facts and gateway status", "/status")
        row3.addWidget(c5)
        row3.addWidget(c6)
        grid_col.addLayout(row3)

        h_lay.addLayout(grid_col)
        self._card_buttons = [c1, c2, c3, c4, c5, c6]
        return hero

    def _make_card(self, title: str, subtitle: str, prompt_text: str) -> QPushButton:
        btn = QPushButton()
        btn.setFont(get_ui_font(9))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(68)

        l = QVBoxLayout(btn)
        l.setContentsMargins(14, 10, 14, 10)
        l.setSpacing(2)

        t = QLabel(title)
        t.setFont(get_ui_font(9, bold=True))
        sub = QLabel(subtitle)
        sub.setFont(get_ui_font(7.5))

        btn._t = t
        btn._sub = sub
        l.addWidget(t)
        l.addWidget(sub)

        btn.clicked.connect(lambda: self.prompt_clicked.emit(prompt_text))
        return btn

    def apply_theme(self, theme: Theme):
        self._theme = theme
        self.setStyleSheet(f"background-color: {theme.bg_chat};")
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {theme.bg_chat};
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.scroll_thumb};
                border-radius: 3px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme.scroll_thumb_h};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self._hero_title.setStyleSheet(f"color: {theme.text_pri};")
        self._hero_sub.setStyleSheet(f"color: {theme.text_dim};")

        card_qss = f"""
            QPushButton {{
                background: {theme.bg_card};
                border: 1px solid {theme.border};
                border-radius: 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {theme.bg_card_hover};
                border: 1px solid {theme.border_hover};
            }}
        """
        for b in getattr(self, "_card_buttons", []):
            b.setStyleSheet(card_qss)
            b._t.setStyleSheet(f"color: {theme.text_pri};")
            b._sub.setStyleSheet(f"color: {theme.text_dim};")

        self._reasoning_widget.set_theme(theme)
        self._rebuild_messages()

    def set_thinking(self, thinking: bool, step: str = "Thinking..."):
        if thinking:
            self._hero_widget.hide()
            self._msg_widget.show()
            self._reasoning_widget.start_thinking(step)
            QTimer.singleShot(25, self._scroll_to_bottom)
        else:
            self._reasoning_widget.finish_thinking()
            self._reasoning_widget.hide()

    def update_thinking_step(self, step: str):
        self._hero_widget.hide()
        self._msg_widget.show()
        self._reasoning_widget.add_step(step)

    def append_message(self, sender: str, text: str):
        self._hero_widget.hide()
        self._msg_widget.show()
        if sender == "max":
            self.set_thinking(False)

        ts = time.strftime("%H:%M")
        self._messages.append((sender, text, ts))
        self._render_message_row(sender, text, ts, stream=(sender == "max"))
        QTimer.singleShot(25, self._scroll_to_bottom)

    def _render_message_row(self, sender: str, text: str, ts: str, stream: bool = False):
        T = self._theme
        row = QWidget()
        r_lay = QVBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(6)

        if sender == "you":
            # User Message — ChatGPT right-aligned rounded bubble with mouse selection
            bubble_container = QHBoxLayout()
            bubble_container.setContentsMargins(0, 0, 0, 0)
            bubble_container.addStretch()

            bubble = QLabel(text)
            bubble.setWordWrap(True)
            bubble.setFont(get_ui_font(9.5))
            bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
            bubble.setMaximumWidth(580)
            bubble.setStyleSheet(f"""
                QLabel {{
                    background: {T.bg_user_bubble};
                    color: {T.text_pri};
                    border: 1px solid {T.border_subtle};
                    border-radius: 18px;
                    padding: 10px 16px;
                }}
            """)
            bubble_container.addWidget(bubble)
            r_lay.addLayout(bubble_container)

        elif sender == "max":
            # Assistant Message — Claude & ChatGPT left-aligned response
            top_header = QHBoxLayout()
            top_header.setSpacing(8)

            avatar = QLabel("✦")
            avatar.setFixedSize(24, 24)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setFont(get_ui_font(10, bold=True))
            avatar.setStyleSheet(f"background: {T.accent}; color: #FFFFFF; border-radius: 12px;")
            top_header.addWidget(avatar)

            name_lbl = QLabel("MAX")
            name_lbl.setFont(get_ui_font(8.5, bold=True))
            name_lbl.setStyleSheet(f"color: {T.text_pri};")
            top_header.addWidget(name_lbl)

            model_badge = QLabel("MAX 2.5 Live")
            model_badge.setFont(get_ui_font(7))
            model_badge.setStyleSheet(f"color: {T.text_dim}; padding-left: 4px;")
            top_header.addWidget(model_badge)

            top_header.addStretch()
            r_lay.addLayout(top_header)

            body = QLabel()
            body.setWordWrap(True)
            body.setFont(get_ui_font(9.5))
            body.setTextFormat(Qt.TextFormat.RichText)
            body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
            body.setOpenExternalLinks(True)
            body.setStyleSheet("QLabel { padding-left: 32px; }")
            r_lay.addWidget(body)

            formatted_html = markdown_to_chat_html(text, T)

            # ── Flagship Action Toolbar (Claude & ChatGPT) ──
            action_bar = QHBoxLayout()
            action_bar.setContentsMargins(32, 4, 0, 0)
            action_bar.setSpacing(6)

            btn_qss = f"""
                QPushButton {{
                    background: transparent;
                    color: {T.text_dim};
                    border: none;
                    border-radius: 6px;
                    font-size: 11px;
                    padding: 3px 6px;
                }}
                QPushButton:hover {{
                    background: {T.bg_hover};
                    color: {T.text_pri};
                }}
            """

            # 1. Play / Pause speech button
            play_btn = QPushButton("🔊")
            play_btn.setFixedSize(28, 28)
            play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            play_btn.setToolTip("Read aloud / Stop speech")
            play_btn.setStyleSheet(btn_qss)
            play_btn.clicked.connect(self.stop_speech_clicked.emit)
            action_bar.addWidget(play_btn)

            # 2. Copy button
            copy_btn = QPushButton("📋")
            copy_btn.setFixedSize(28, 28)
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.setToolTip("Copy response")
            copy_btn.setStyleSheet(btn_qss)
            copy_btn.clicked.connect(lambda _, t=text: self._copy_to_clipboard(t, copy_btn))
            action_bar.addWidget(copy_btn)

            # 3. Thumbs Up / Down feedback
            like_btn = QPushButton("👍")
            like_btn.setFixedSize(28, 28)
            like_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            like_btn.setToolTip("Good response")
            like_btn.setStyleSheet(btn_qss)
            like_btn.clicked.connect(lambda _, b=like_btn: self._thumb_clicked(b, "👍"))
            action_bar.addWidget(like_btn)

            dislike_btn = QPushButton("👎")
            dislike_btn.setFixedSize(28, 28)
            dislike_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dislike_btn.setToolTip("Bad response")
            dislike_btn.setStyleSheet(btn_qss)
            dislike_btn.clicked.connect(lambda _, b=dislike_btn: self._thumb_clicked(b, "👎"))
            action_bar.addWidget(dislike_btn)

            action_bar.addStretch()
            r_lay.addLayout(action_bar)

            # Smooth Streaming Animation (ChatGPT / Claude Real-Time Feel)
            if stream and len(text) > 8:
                self._stream_text_into_label(body, text, formatted_html, T)
            else:
                body.setText(f"<div style='color: {T.text_pri}; line-height: 1.55;'>{formatted_html}</div>")

        else:
            # System / Tool info
            sys_lbl = QLabel(f"• {text}")
            sys_lbl.setFont(get_ui_font(8))
            sys_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sys_lbl.setStyleSheet(f"color: {T.text_dim}; padding: 4px 0;")
            r_lay.addWidget(sys_lbl)

        self._msg_lay.addWidget(row)

    def _stream_text_into_label(self, label: QLabel, raw_text: str, full_html: str, theme: Theme):
        """Streams text word-by-word with a blinking cursor at 14ms interval."""
        words = raw_text.split(" ")
        state = {"idx": 0, "current": ""}

        timer = QTimer(self)
        def _tick():
            if state["idx"] < len(words):
                state["current"] += (" " if state["idx"] > 0 else "") + words[state["idx"]]
                state["idx"] += 1
                partial_html = markdown_to_chat_html(state["current"], theme)
                label.setText(f"<div style='color: {theme.text_pri}; line-height: 1.55;'>{partial_html} <span style='color: {theme.think};'>▊</span></div>")
                self._scroll_to_bottom()
            else:
                timer.stop()
                label.setText(f"<div style='color: {theme.text_pri}; line-height: 1.55;'>{full_html}</div>")
                self._scroll_to_bottom()

        timer.timeout.connect(_tick)
        timer.start(14)

    def _copy_to_clipboard(self, text: str, btn: QPushButton):
        QApplication.clipboard().setText(text)
        btn.setText("✓")
        QTimer.singleShot(1500, lambda: btn.setText("📋"))

    def _thumb_clicked(self, btn: QPushButton, original: str):
        btn.setText("✓")
        QTimer.singleShot(1500, lambda: btn.setText(original))

    def _rebuild_messages(self):
        while self._msg_lay.count():
            item = self._msg_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self._messages:
            self._hero_widget.show()
            self._msg_widget.hide()
            return

        self._hero_widget.hide()
        self._msg_widget.show()
        for sender, text, ts in self._messages:
            self._render_message_row(sender, text, ts, stream=False)

    def clear(self):
        self._messages.clear()
        self.set_thinking(False)
        self._rebuild_messages()

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())


# ═══════════════════════════ CHATGPT FLOATING INPUT BAR ═══════════════════════
class ChatGPTInputBar(QWidget):
    """
    Flagship Centered Floating Input Pill with attached file chip and floating soundwave:
    - Attachment button (+)
    - Attached file preview card with remove action
    - Auto-expanding multiline text edit (Shift+Enter for newline, Enter to send)
    - Voice / Mic button
    - Circular Send button (Up Arrow)
    - Small floating wavy structure directly above the input pill
    """
    send_clicked = pyqtSignal(str)
    file_attached = pyqtSignal(str)
    file_removed = pyqtSignal()
    voice_toggle_clicked = pyqtSignal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._current_attached_file: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 10)
        lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Centered container (Width 760px)
        wrapper = QWidget()
        wrapper.setFixedWidth(760)
        w_lay = QVBoxLayout(wrapper)
        w_lay.setContentsMargins(0, 0, 0, 0)
        w_lay.setSpacing(6)

        # ── 1. Floating Small Wavy Structure (Voice Mode Capsule) ──
        self._wave_widget = FloatingWaveWidget(self._theme)
        self._wave_widget.clicked.connect(self.voice_toggle_clicked.emit)
        w_lay.addWidget(self._wave_widget)

        # ── 2. Attached File Preview Chip (Claude style) ──
        self._file_chip = QFrame()
        self._file_chip.setFixedHeight(30)
        fc_lay = QHBoxLayout(self._file_chip)
        fc_lay.setContentsMargins(10, 0, 8, 0)
        fc_lay.setSpacing(6)

        self._file_lbl = QLabel("📄 attached_file.py")
        self._file_lbl.setFont(get_ui_font(8, bold=True))
        fc_lay.addWidget(self._file_lbl)

        fc_lay.addStretch()

        self._file_close_btn = QPushButton("✕")
        self._file_close_btn.setFont(get_ui_font(8))
        self._file_close_btn.setFixedSize(20, 20)
        self._file_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._file_close_btn.clicked.connect(self._remove_file)
        fc_lay.addWidget(self._file_close_btn)

        w_lay.addWidget(self._file_chip)
        self._file_chip.hide()

        # ── 3. Auto-Expanding Multiline Pill Input Box ──
        pill = QFrame()
        self._pill = pill
        p_lay = QHBoxLayout(pill)
        p_lay.setContentsMargins(10, 4, 10, 4)
        p_lay.setSpacing(8)

        # Attachment (+)
        self._attach_btn = QPushButton("＋")
        self._attach_btn.setFixedSize(36, 36)
        self._attach_btn.setFont(get_ui_font(12))
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip("Attach file or media")
        self._attach_btn.clicked.connect(self._browse)
        p_lay.addWidget(self._attach_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        # Multiline Auto-Expanding Input Box
        self._input = PromptTextEdit("Message MAX... (Shift+Enter for newline)")
        self._input.send_requested.connect(self._on_send)
        self._input.textChanged.connect(self._on_text_changed)
        p_lay.addWidget(self._input, stretch=1)

        # Mic button
        self._mic_btn = QPushButton("🎙")
        self._mic_btn.setFixedSize(36, 36)
        self._mic_btn.setFont(get_ui_font(11))
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setToolTip("Toggle Voice [F4]")
        self._mic_btn.clicked.connect(self.voice_toggle_clicked.emit)
        p_lay.addWidget(self._mic_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        # Send button (Up Arrow)
        self._send_btn = QPushButton("↑")
        self._send_btn.setFixedSize(34, 34)
        self._send_btn.setFont(get_ui_font(12, bold=True))
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.clicked.connect(self._on_send)
        p_lay.addWidget(self._send_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        w_lay.addWidget(pill)

        # Disclaimer
        self._disclaimer = QLabel("MAX can make mistakes. Verify important information.")
        self._disclaimer.setFont(get_ui_font(7.5))
        self._disclaimer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w_lay.addWidget(self._disclaimer)

        lay.addWidget(wrapper)
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme):
        self._theme = theme
        self._wave_widget.set_theme(theme)
        self._file_chip.setStyleSheet(f"""
            QFrame {{
                background: {theme.bg_card};
                border: 1px solid {theme.border};
                border-radius: 6px;
            }}
        """)
        self._file_lbl.setStyleSheet(f"color: {theme.think};")
        self._file_close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.text_dim};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: {theme.text_pri};
            }}
        """)

        self._pill.setStyleSheet(f"""
            QFrame {{
                background: {theme.bg_input};
                border: 1px solid {theme.border};
                border-radius: 22px;
            }}
        """)
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                color: {theme.text_pri};
                border: none;
                padding: 4px;
            }}
        """)
        self._attach_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.text_sec};
                border: none;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background: {theme.bg_hover};
                color: {theme.text_pri};
            }}
        """)
        self._mic_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.text_sec};
                border: none;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background: {theme.bg_hover};
                color: {theme.text_pri};
            }}
        """)
        self._disclaimer.setStyleSheet(f"color: {theme.text_dim};")
        self._on_text_changed()

    def set_wave_state(self, state: str):
        self._wave_widget.set_state(state)

    def set_wave_muted(self, muted: bool):
        self._wave_widget.muted = muted
        self._mic_btn.setText("🔇" if muted else "🎙")
        self._wave_widget.update()

    def set_transcription(self, text: str):
        self._wave_widget.live_transcription = text
        self._wave_widget.update()

    def show_attached_file(self, filename: str, size_str: str):
        self._current_attached_file = filename
        self._file_lbl.setText(f"📄 {filename}  ·  {size_str}")
        self._file_chip.show()

    def _remove_file(self):
        self._current_attached_file = None
        self._file_chip.hide()
        self.file_removed.emit()

    def _on_text_changed(self):
        txt = self._input.toPlainText().strip()
        has_text = bool(txt)
        T = self._theme
        if has_text:
            self._send_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {T.send_btn_bg};
                    color: {T.send_btn_fg};
                    border: none;
                    border-radius: 17px;
                    font-weight: bold;
                }}
            """)
        else:
            self._send_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {T.bg_hover};
                    color: {T.text_dim};
                    border: none;
                    border-radius: 17px;
                }}
            """)

    def _on_send(self):
        txt = self._input.toPlainText().strip()
        if not txt:
            return
        self._input.clear()
        self.send_clicked.emit(txt)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Attach Document or Media for MAX",
            "", "All Files (*.*);;PDF (*.pdf);;Images (*.png *.jpg *.jpeg);;Text (*.txt *.py *.md)"
        )
        if path:
            self.file_attached.emit(path)


# ═══════════════════════════ SETUP OVERLAY ══════════════════════════════════
class SetupOverlay(QWidget):
    """Clean modal dialog for entering Gemini & OpenRouter API keys."""
    done = pyqtSignal(str, str, str)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame(self)
        card.setFixedSize(460, 400)
        self._card = card

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(28, 24, 28, 24)
        c_lay.setSpacing(12)

        title = QLabel("CORE SETUP // INITIALIZE LINK")
        title.setFont(get_ui_font(10, bold=True))
        self._title_lbl = title
        c_lay.addWidget(title)

        desc = QLabel("Enter your Gemini API key to activate the MAX Live Voice & Tool engine:")
        desc.setFont(get_ui_font(8))
        desc.setWordWrap(True)
        self._desc_lbl = desc
        c_lay.addWidget(desc)

        def _lbl(t: str):
            l = QLabel(t)
            l.setFont(get_ui_font(7, bold=True))
            return l

        self._l1 = _lbl("GEMINI API KEY (REQUIRED)")
        c_lay.addWidget(self._l1)
        self._gem = QLineEdit()
        self._gem.setEchoMode(QLineEdit.EchoMode.Password)
        self._gem.setFont(get_ui_font(8, mono=True))
        self._gem.setFixedHeight(34)
        c_lay.addWidget(self._gem)

        self._l2 = _lbl("OPENROUTER API KEY (OPTIONAL)")
        c_lay.addWidget(self._l2)
        self._opr = QLineEdit()
        self._opr.setEchoMode(QLineEdit.EchoMode.Password)
        self._opr.setFont(get_ui_font(8, mono=True))
        self._opr.setFixedHeight(34)
        c_lay.addWidget(self._opr)

        self._l3 = _lbl("TARGET OS ENVIRONMENT")
        c_lay.addWidget(self._l3)
        hb = QHBoxLayout()
        hb.setSpacing(8)
        self._os_btns = {}
        for k in ["Windows", "Darwin", "Linux"]:
            b = QPushButton({"Windows": "WINDOWS", "Darwin": "macOS", "Linux": "LINUX"}[k])
            b.setFixedHeight(30)
            b.setFont(get_ui_font(8, bold=True))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, x=k: self._select_os(x))
            hb.addWidget(b)
            self._os_btns[k] = b
        c_lay.addLayout(hb)
        self._selected_os = _OS
        self._select_os(self._selected_os)

        btn = QPushButton("INITIALIZE MAX CORE >")
        btn.setFixedHeight(38)
        btn.setFont(get_ui_font(9, bold=True))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._save)
        self._btn = btn
        c_lay.addWidget(btn)

        lay.addWidget(card)
        self.apply_theme(theme)

    def apply_theme(self, theme: Theme):
        self._theme = theme
        self._card.setStyleSheet(f"""
            QFrame {{
                background: {theme.bg_sidebar};
                border: 1px solid {theme.border_hover};
                border-radius: 16px;
            }}
        """)
        self._title_lbl.setStyleSheet(f"color: {theme.accent}; letter-spacing: 1.5px;")
        self._desc_lbl.setStyleSheet(f"color: {theme.text_sec};")
        for l in (self._l1, self._l2, self._l3):
            l.setStyleSheet(f"color: {theme.text_dim};")

        input_qss = f"""
            QLineEdit {{
                background: {theme.bg_input};
                color: {theme.text_pri};
                border: 1px solid {theme.border};
                border-radius: 8px;
                padding: 0 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.accent};
            }}
        """
        self._gem.setStyleSheet(input_qss)
        self._opr.setStyleSheet(input_qss)

        self._btn.setStyleSheet(f"""
            QPushButton {{
                background: {theme.accent};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {theme.accent_hover};
            }}
        """)
        self._select_os(self._selected_os)

    def _select_os(self, os_name):
        self._selected_os = os_name
        T = self._theme
        for k, b in self._os_btns.items():
            if k == os_name:
                b.setStyleSheet(f"background: {T.accent}; color: #FFFFFF; border: 1px solid {T.accent}; border-radius: 6px;")
            else:
                b.setStyleSheet(f"background: {T.bg_input}; color: {T.text_dim}; border: 1px solid {T.border}; border-radius: 6px;")

    def _save(self):
        k = self._gem.text().strip()
        o = self._opr.text().strip()
        if k:
            self.done.emit(k, o, self._selected_os)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), qcol("#000000", 200))


# ═══════════════════════════ MAIN APPLICATION WINDOW ═══════════════════════════
class MainWindow(QMainWindow):
    _state_sig = pyqtSignal(str)
    _log_sig   = pyqtSignal(str)

    def __init__(self, face_path: str):
        super().__init__()
        self._dark_mode = True
        self._theme = Theme(dark=self._dark_mode)

        self.setWindowTitle("MAX  |  Next-Gen AI Assistant")
        self.resize(_DEFAULT_W, _DEFAULT_H)
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.setAcceptDrops(True)

        self.on_text_command = None
        self._current_file: str | None = None
        self._muted = False
        self._ready = self._check_config()
        self._overlay: SetupOverlay | None = None

        container = QWidget()
        self.setCentralWidget(container)

        root_lay = QHBoxLayout(container)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── 1. Left ChatGPT / Claude Sidebar ──
        self._sidebar = ChatGPTSidebar(self._theme)
        self._sidebar.new_chat_clicked.connect(self._new_chat)
        self._sidebar.toggle_theme_clicked.connect(self._toggle_theme)
        self._sidebar.toggle_mic_clicked.connect(self._toggle_mute)
        root_lay.addWidget(self._sidebar)

        # ── 2. Right Main Chat Workspace ──
        chat_workspace = QWidget()
        c_lay = QVBoxLayout(chat_workspace)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        # Top Header Bar
        c_lay.addWidget(self._build_top_header())

        # Main Conversation Stream
        self._stream = ChatGPTStream(self._theme)
        self._stream.prompt_clicked.connect(self._send_text)
        self._stream.stop_speech_clicked.connect(self._stop_or_toggle_speech)
        c_lay.addWidget(self._stream, stretch=1)

        # Bottom Floating Input Dock with Wavy Soundwave
        self._input_bar = ChatGPTInputBar(self._theme)
        self._input_bar.send_clicked.connect(self._send_text)
        self._input_bar.file_attached.connect(self._on_file_selected)
        self._input_bar.file_removed.connect(self._on_file_removed)
        self._input_bar.voice_toggle_clicked.connect(self._toggle_mute)
        c_lay.addWidget(self._input_bar)

        root_lay.addWidget(chat_workspace, stretch=1)

        # Signals
        self._state_sig.connect(self._apply_state)
        self._log_sig.connect(self._on_log_received)

        # Shortcuts
        QShortcut(QKeySequence("F4"), self, self._toggle_mute)
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+N"), self, self._new_chat)

        self._apply_theme_to_all()

        if not self._ready:
            self._show_setup()

    def _build_top_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(50)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        # Sidebar Toggle Button (☰)
        self._sidebar_btn = QPushButton("☰")
        self._sidebar_btn.setFont(get_ui_font(12))
        self._sidebar_btn.setFixedSize(34, 34)
        self._sidebar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sidebar_btn.setToolTip("Toggle sidebar")
        self._sidebar_btn.clicked.connect(self._toggle_sidebar)
        lay.addWidget(self._sidebar_btn)

        # Model Selector Pill (OmniRoute / Gateway Indicator)
        from gateway.omniroute_manager import is_omniroute_alive
        omni_online = is_omniroute_alive()

        model_pill = QPushButton("⚡ OmniRoute (375+ Providers) ▾" if omni_online else "MAX 2.5 Live ▾")
        model_pill.setFont(get_ui_font(9, bold=True))
        model_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        model_pill.setFixedHeight(32)
        if omni_online:
            model_pill.setToolTip("Connected to OmniRoute Local Gateway at http://localhost:20128/v1. Click to open Dashboard.")
        else:
            model_pill.setToolTip("Click to open OmniRoute Dashboard / Launch Gateway (http://localhost:20128/dashboard)")
        model_pill.clicked.connect(self._open_omniroute_dashboard)
        self._model_pill = model_pill
        lay.addWidget(model_pill)

        lay.addStretch()

        # State Indicator with Live Pulsing Dot
        self._state_dot = QFrame()
        self._state_dot.setFixedSize(8, 8)
        self._state_dot.setStyleSheet(f"background: {self._theme.accent}; border-radius: 4px;")
        lay.addWidget(self._state_dot)

        self._state_text = QLabel("Listening")
        self._state_text.setFont(get_ui_font(8, bold=True))
        lay.addWidget(self._state_text)

        lay.addStretch()

        # Clear Chat Button
        self._clear_btn = QPushButton("🗑")
        self._clear_btn.setFont(get_ui_font(10))
        self._clear_btn.setFixedSize(32, 32)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setToolTip("Clear conversation")
        self._clear_btn.clicked.connect(self._new_chat)
        lay.addWidget(self._clear_btn)

        # Fullscreen Button
        self._fs_btn = QPushButton("⛶")
        self._fs_btn.setFont(get_ui_font(9))
        self._fs_btn.setFixedSize(32, 32)
        self._fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fs_btn.setToolTip("Toggle fullscreen [F11]")
        self._fs_btn.clicked.connect(self._toggle_fullscreen)
        lay.addWidget(self._fs_btn)

        self._header_widget = header
        return header

    # ── Drag & Drop Files Support (ChatGPT / Claude Desktop) ──
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path and os.path.exists(path):
                self._on_file_selected(path)
                e.acceptProposedAction()

    def _toggle_sidebar(self):
        if self._sidebar.isVisible():
            self._sidebar.hide()
        else:
            self._sidebar.show()

    def _open_omniroute_dashboard(self):
        import webbrowser
        from gateway.omniroute_manager import is_omniroute_alive
        if is_omniroute_alive():
            webbrowser.open("http://localhost:20128/dashboard")
        else:
            self._stream.append_message(
                "sys",
                "OmniRoute Gateway is currently offline. You can launch it with 'start_omniroute.bat' or 'npx -y omniroute'. "
                "Once running, dashboard will be accessible at http://localhost:20128/dashboard."
            )
            webbrowser.open("http://localhost:20128/dashboard")

    def _new_chat(self):
        self._stream.clear()
        self._input_bar._remove_file()

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self._theme = Theme(dark=self._dark_mode)
        self._apply_theme_to_all()

    def _apply_theme_to_all(self):
        T = self._theme
        self.centralWidget().setStyleSheet(f"background-color: {T.bg_app};")
        self._sidebar.apply_theme(T)
        self._stream.apply_theme(T)
        self._input_bar.apply_theme(T)

        self._header_widget.setStyleSheet(f"""
            QFrame {{
                background: {T.bg_app};
                border-bottom: 1px solid {T.border};
            }}
        """)
        self._sidebar_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T.text_sec};
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {T.bg_hover};
                color: {T.text_pri};
            }}
        """)
        self._model_pill.setStyleSheet(f"""
            QPushButton {{
                background: {T.bg_card};
                color: {T.text_pri};
                border: 1px solid {T.border};
                border-radius: 8px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background: {T.bg_hover};
            }}
        """)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T.text_sec};
                border: 1px solid {T.border};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                color: {T.text_pri};
            }}
        """)
        self._fs_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {T.text_sec};
                border: 1px solid {T.border};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                color: {T.text_pri};
            }}
        """)
        self._state_text.setStyleSheet(f"color: {T.text_sec};")

        if self._overlay:
            self._overlay.apply_theme(T)

    def _handle_command(self, prompt: str | None = None):
        # 1. Read input text and clear input field
        if prompt is None or not isinstance(prompt, str):
            prompt = self._cmd_input.text().strip()
        if not prompt:
            return
        self._cmd_input.clear()

        # 2. Add message to activity log and set neural core to THINKING
        self._log.append_log(f"You: {prompt}")
        self._core.state = "THINKING"
        self._input_bar.set_transcription("")

        # 3. Launch background worker thread
        self._worker = AgentWorker(prompt)
        self._worker.response_ready.connect(self._on_agent_reply)
        self._worker.start()

    def _on_agent_reply(self, reply: str):
        # 4. Return sphere/core to LISTENING and display output
        self._core.state = "LISTENING"
        self._log.append_log(f"Max: {reply}")

    def _send_text(self, text: str):
        self._handle_command(text)

    on_user_submit = _handle_command
    _on_agent_response = _on_agent_reply

    @property
    def _cmd_input(self):
        return self._input_bar._input

    @property
    def _input_field(self):
        return self._input_bar._input

    @property
    def _log(self):
        return self._log_widget

    @property
    def _log_widget(self):
        class _LogShim:
            def __init__(w_self, stream):
                w_self._stream = stream
            def append_log(w_self, text: str):
                if text.startswith("You:"):
                    w_self._stream.append_message("you", text[4:].strip())
                elif text.startswith("Max:") or text.startswith("MAX:"):
                    w_self._stream.append_message("max", text[4:].strip())
                else:
                    w_self._stream.append_message("sys", text)
        return _LogShim(self._stream)

    @property
    def _core(self):
        return self._core_visualizer

    @property
    def _core_visualizer(self):
        class _VisShim:
            def __init__(w_self, win):
                w_self._win = win
            @property
            def state(w_self):
                return w_self._win._state_text.text()
            @state.setter
            def state(w_self, val):
                w_self._win._apply_state(val)
        return _VisShim(self)


    def _on_log_received(self, text: str):
        text = text.strip()
        if not text:
            return
        if text.startswith("You:"):
            content = text[4:].strip()
            self._stream.append_message("you", content)
            self._apply_state("THINKING")
        elif text.startswith("Max:") or text.startswith("MAX:"):
            content = text[4:].strip()
            self._apply_state("LISTENING")
            self._stream.append_message("max", content)
        elif text.startswith("[") and "]" in text:
            # Tool reasoning log (e.g. [Search] ..., [DevAgent] ...)
            step_name = text[1:text.index("]")]
            self._stream.update_thinking_step(f"Using {step_name}...")
        else:
            self._stream.append_message("sys", text)

    def _on_file_selected(self, path: str):
        self._current_file = path
        p = Path(path)
        sz = f"{p.stat().st_size / 1024:.1f} KB"
        self._input_bar.show_attached_file(p.name, sz)
        self._stream.append_message("sys", f"Attached file: '{p.name}' ({sz})")
        msg = f"I have uploaded a file: '{p.name}' (path: {path}, size: {sz}). Please inspect and summarize it."
        self._send_text(msg)

    def _on_file_removed(self):
        self._current_file = None

    def _toggle_mute(self):
        self._muted = not self._muted
        self._sidebar.set_muted(self._muted)
        self._input_bar.set_wave_muted(self._muted)
        if self._muted:
            self._apply_state("MUTED")
            self._stream.append_message("sys", "Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._stream.append_message("sys", "Microphone active.")

    def _stop_or_toggle_speech(self):
        if self._state_text.text().lower() == "speaking":
            self._apply_state("LISTENING")
            self._stream.append_message("sys", "Speech paused.")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _apply_state(self, state: str):
        self._input_bar.set_wave_state(state)
        T = self._theme

        if state == "THINKING":
            self._stream.set_thinking(True, "Thinking...")
            self._state_text.setText("Thinking...")
            self._state_text.setStyleSheet(f"color: {T.think};")
            self._state_dot.setStyleSheet(f"background: {T.think}; border-radius: 4px;")
        elif state == "SPEAKING":
            self._stream.set_thinking(False)
            self._state_text.setText("Speaking")
            self._state_text.setStyleSheet(f"color: {T.speak};")
            self._state_dot.setStyleSheet(f"background: {T.speak}; border-radius: 4px;")
        elif state == "MUTED":
            self._stream.set_thinking(False)
            self._state_text.setText("Muted")
            self._state_text.setStyleSheet(f"color: {T.muted};")
            self._state_dot.setStyleSheet(f"background: {T.muted}; border-radius: 4px;")
        else:
            self._stream.set_thinking(False)
            self._state_text.setText("Listening")
            self._state_text.setStyleSheet(f"color: {T.accent};")
            self._state_dot.setStyleSheet(f"background: {T.accent}; border-radius: 4px;")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._overlay:
            cw = self.centralWidget()
            if cw:
                self._overlay.setGeometry(0, 0, cw.width(), cw.height())

    def _check_config(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key")) and bool(d.get("os_system"))
        except Exception:
            return False

    def _show_setup(self):
        cw = self.centralWidget()
        ov = SetupOverlay(self._theme, cw)
        ov.setGeometry(0, 0, cw.width(), cw.height())
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    def _on_setup_done(self, key, or_key, os_name):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({"gemini_api_key": key, "openrouter_api_key": or_key, "os_system": os_name}, indent=4),
            encoding="utf-8"
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._stream.append_message("sys", f"System initialized. OS={os_name.upper()}. MAX online.")


# ═══════════════════════════ JARVIS UI PUBLIC WRAPPER ═══════════════════════
class _RootShim:
    def __init__(self, app):
        self._app = app

    def mainloop(self):
        self._app.exec()

    def protocol(self, *_):
        pass


class JarvisUI:
    """Public wrapper preserving 100% API compatibility with main.py."""
    def __init__(self, face_path: str = "face.png", size=None):
        if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._current_file

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def speak(self, text: str):
        self._win._log_sig.emit(f"Max: {text}")

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    def on_user_submit(self):
        self._win.on_user_submit()


if __name__ == "__main__":
    ui = JarvisUI()
    ui.root.mainloop()