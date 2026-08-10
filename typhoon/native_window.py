#!/usr/bin/python3
"""Native, low-memory Qt Widgets frontend for Typhoon."""

import configparser
import glob
import json
import math
import os
import signal
import subprocess
import sys
from datetime import datetime
from urllib.parse import unquote, urlencode, urlparse

from PyQt6.QtCore import QEvent, QPointF, QRectF, QSize, QSettings, Qt, QTimer, QUrl
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractScrollArea,
    QAbstractSlider,
    QApplication,
    QBoxLayout,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QStyle,
    QStyleOptionButton,
    QStylePainter,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

try:
    import dbus
    import dbus.mainloop.glib
    import dbus.service
except ImportError:
    dbus = None

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None

try:
    import cairosvg
except ImportError:
    cairosvg = None

if not IS_WINDOWS:
    try:
        import gi
        gi.require_version("Xdp", "1.0")
        from gi.repository import Xdp
    except (ImportError, ValueError):
        Xdp = None
else:
    Xdp = None


APP_ID = "io.github.archisman_panigrahi.typhoon-native-python"
APP_ICON = "io.github.archisman_panigrahi.typhoon.svg"
USER_AGENT = "Typhoon Weather App (https://github.com/archisman-panigrahi/typhoon)"
DAY_ICONS = {
    0: "v", 1: "1", 2: "d", 3: "`", 45: "h", 48: "g", 51: "0",
    53: "9", 55: "9", 56: "r", 57: "y", 61: "0", 63: "9", 65: "9",
    66: "r", 67: "e", 71: "=", 73: "o", 75: "6", 77: "6", 80: "0",
    81: "9", 82: "9", 85: "6", 86: "6", 95: "z", 96: "z", 99: "z",
}
NIGHT_ICONS = {0: "/", 1: "2", 2: "f", 45: "g", 51: "5", 53: "-", 56: "i", 61: "5", 63: "-", 66: "t", 71: "[", 73: "8", 80: "9"}
PALETTE = ["#575591", "#ff0097", "#00aba9", "#8cbf26", "#a05000", "#333333", "#f09609", "#1ba1e2", "#ff8e83", "#339933"]

# Exact font-size, left, and top rules from style.css's #code selectors.
WEATHER_ICON_CSS = {
    0: (200, 12, 70),
    1: (200, 22, 90),
    2: (200, 20, 80),
    28: (200, 22, 100),
    30: (200, 22, 100),
    31: (300, 12, 30),
    32: (200, 12, 75),
    33: (300, 12, 30),
    34: (200, 12, 75),
    36: (200, 12, 75),
    45: (200, 22, 90),
    51: (200, 22, 75),
    55: (200, 22, 60),
    61: (200, 22, 75),
    80: (200, 22, 75),
    95: (200, 22, 60),
    96: (200, 22, 60),
    99: (200, 22, 60),
}


if dbus is not None:
    class UnityLauncherService(dbus.service.Object):
        def __init__(self):
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            name = dbus.service.BusName(APP_ID, dbus.SessionBus())
            super().__init__(name, "/io/github/archisman_panigrahi/typhoon")

        @dbus.service.signal(dbus_interface="com.canonical.Unity.LauncherEntry", signature="sa{sv}")
        def Update(self, app_uri, properties):
            pass
else:
    UnityLauncherService = None


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    direct = os.path.join(base, name)
    return direct if os.path.exists(direct) else os.path.join(base, "typhoon", name)


def weather_icon(code, is_day=True):
    code = int(code or 0)
    return (DAY_ICONS if is_day else {**DAY_ICONS, **NIGHT_ICONS}).get(code, "`")


class Network:
    def __init__(self, parent):
        self.manager = QNetworkAccessManager(parent)

    def get_json(self, url, callback):
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", USER_AGENT.encode())
        request.setRawHeader(b"Accept", b"application/json")
        reply = self.manager.get(request)

        def finished():
            error = reply.error()
            error_message = reply.errorString()
            raw = bytes(reply.readAll())
            reply.deleteLater()
            if error != QNetworkReply.NetworkError.NoError:
                callback(None, error_message)
                return
            try:
                callback(json.loads(raw), None)
            except (ValueError, TypeError) as exc:
                callback(None, str(exc))

        reply.finished.connect(finished)


class ToolButton(QPushButton):
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self._base_icon = QIcon(resource(icon)) if icon else QIcon()
        if icon:
            self.setIcon(self._base_icon)
            self.setIconSize(QSize(16, 16))
        self.setObjectName("toolButton")
        self.setFixedSize(30, 30)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._uses_hover_opacity = False
        self._paint_opacity = 1.0
        self._spin_angle = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(25)
        self._spin_timer.timeout.connect(self._advance_spin)

    def start_spinning(self):
        if self._base_icon.isNull():
            return
        self.setText("")
        self._advance_spin()
        self._spin_timer.start()

    def stop_spinning(self, clear=False):
        self._spin_timer.stop()
        self._spin_angle = 0
        self.setIcon(QIcon() if clear else self._base_icon)

    def _advance_spin(self):
        size = self.iconSize()
        source = self._base_icon.pixmap(size)
        rotated = QPixmap(size)
        rotated.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rotated)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(size.width() / 2, size.height() / 2)
        painter.rotate(self._spin_angle)
        painter.translate(-size.width() / 2, -size.height() / 2)
        painter.drawPixmap(0, 0, source)
        painter.end()
        self.setIcon(QIcon(rotated))
        self._spin_angle = (self._spin_angle + 30) % 360

    def enable_hover_opacity(self):
        self._uses_hover_opacity = True
        self._paint_opacity = .8
        self.update()

    def paintEvent(self, event):
        if not self._uses_hover_opacity:
            super().paintEvent(event)
            return
        option = QStyleOptionButton()
        self.initStyleOption(option)
        painter = QStylePainter(self)
        painter.setOpacity(self._paint_opacity)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)

    def enterEvent(self, event):
        if self._uses_hover_opacity:
            self._paint_opacity = 1.0
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._uses_hover_opacity:
            self._paint_opacity = .8
            self.update()
        super().leaveEvent(event)


class GlyphLabel(QLabel):
    """Centers a font glyph by its visible bounds instead of its baseline."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._glyph_offset = QPointF()

    def set_glyph_offset(self, x, y):
        self._glyph_offset = QPointF(float(x), float(y))
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())
        bounds = painter.fontMetrics().tightBoundingRect(self.text())
        x = (self.width() - bounds.width()) / 2 - bounds.x() + self._glyph_offset.x()
        y = (self.height() - bounds.height()) / 2 - bounds.y() + self._glyph_offset.y()
        painter.drawText(round(x), round(y), self.text())


class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(34, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#222"), 2))
        painter.setBrush(QColor("#444") if self.underMouse() else QColor("#333"))
        painter.drawRoundedRect(QRectF(1, 1, 32, 18), 9, 9)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(QRectF(16 if self.isChecked() else 3, 3, 14, 14))


class CreditLinkLabel(QLabel):
    """QLabel with browser-like external links and hover underlines."""

    LINK_STYLE = "color:#fff; text-decoration:none"

    def __init__(self, html, parent=None):
        super().__init__(parent)
        self._base_html = html
        self._hovered_link = ""
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByKeyboard
        )
        self.setOpenExternalLinks(False)
        self.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        self.linkHovered.connect(self._show_link_hover)
        self.setText(html)

    def _show_link_hover(self, url):
        if url == self._hovered_link:
            return
        self._hovered_link = url
        html = self._base_html
        if url:
            html = html.replace(
                f'style="{self.LINK_STYLE}" href="{url}"',
                f'style="color:#fff; text-decoration:underline" href="{url}"',
            )
        self.setText(html)


class ResizeHandle(QWidget):
    """Invisible hit area for resizing the frameless window."""

    _CURSORS = {
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "bottom-left": Qt.CursorShape.SizeBDiagCursor,
        "bottom-right": Qt.CursorShape.SizeFDiagCursor,
    }

    def __init__(self, edge, owner):
        super().__init__(owner)
        self.edge = edge
        self.owner = owner
        self.setCursor(self._CURSORS[edge])
        self.setToolTip("Resize")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner._begin_resize(self.edge, event.globalPosition().toPoint())
            self.grabMouse()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.owner._continue_resize(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.releaseMouse()
            self.owner._finish_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.degrees = 0
        # The circle remains at the same page position; the extra canvas is
        # solely for spacing the four direction labels farther away.
        self.setFixedSize(54, 54)

    def set_degrees(self, degrees):
        self.degrees = float(degrees or 0)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 215), 1.5))
        compass_font = QFont(self.font().family())
        compass_font.setPixelSize(12)
        compass_font.setWeight(QFont.Weight.Black)
        painter.setFont(compass_font)
        metrics = QFontMetricsF(compass_font)

        def draw_label(text, horizontal, vertical):
            bounds = metrics.tightBoundingRect(text)
            if horizontal == "left":
                # Put W's visible right edge at x=15.
                x = 15 - bounds.width() - bounds.x()
            elif horizontal == "right":
                # Keep E one extra pixel outward to balance its narrower
                # visible shape against W.
                x = 46 - bounds.x()
            else:
                x = 30 - bounds.width() / 2 - bounds.x()
            if vertical == "top":
                # N ends at y=10 and S begins at y=44, leaving matching
                # gaps around the circle at y=15..39.
                baseline = 10 - bounds.height() - bounds.y()
            elif vertical == "bottom":
                baseline = 44 - bounds.y()
            else:
                baseline = (self.height() - bounds.height()) / 2 - bounds.y()
            painter.drawText(QPointF(x, baseline), text)

        draw_label("N", "center", "top")
        draw_label("W", "left", "center")
        draw_label("E", "right", "center")
        draw_label("S", "center", "bottom")
        painter.setPen(QPen(QColor(255, 255, 255, 175), 2.3))
        painter.drawEllipse(QRectF(18, 15, 24, 24))
        painter.save()
        painter.translate(30, 27)
        painter.rotate(self.degrees)
        arrow_color = QColor(255, 255, 255, 240)
        shaft_pen = QPen(arrow_color, 2.2)
        shaft_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(shaft_pen)
        painter.drawLine(QPointF(0, -6), QPointF(0, 4))
        arrowhead = QPainterPath(QPointF(0, 8))
        arrowhead.lineTo(-4, 2.5)
        arrowhead.quadTo(-4.3, 1.8, -3.4, 2.1)
        arrowhead.lineTo(0, 4.1)
        arrowhead.lineTo(3.4, 2.1)
        arrowhead.quadTo(4.3, 1.8, 4, 2.5)
        arrowhead.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(arrow_color)
        painter.drawPath(arrowhead)
        painter.restore()


class ForecastDay(QWidget):
    def __init__(self, climacon_font, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.day = QLabel("---")
        self.day.setObjectName("forecastDay")
        self.day.setContentsMargins(0, 2, 0, 0)
        self.icon = GlyphLabel("`")
        self.icon.setObjectName("forecastIcon")
        forecast_font = QFont(climacon_font)
        forecast_font.setPixelSize(48)
        self.icon.setFont(forecast_font)
        self.icon.set_glyph_offset(0, 1)
        self.temp = QLabel("--° / --°")
        self.temp.setObjectName("forecastTemp")
        self.temp.setContentsMargins(0, 0, 0, 8)
        for widget in (self.day, self.icon, self.temp):
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget)


class ForecastChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hours = []
        self.rain = []
        self.temperatures = []
        self.unit = "c"
        self.setMinimumSize(680, 245)

    def set_data(self, hours, rain, temperatures, unit):
        self.hours, self.rain, self.temperatures, self.unit = hours, rain, temperatures, unit
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        if not self.hours:
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Hourly forecast is not available yet.")
            return
        left, top, right, bottom = 40.0, 20.0, 42.0, 34.0
        width, height = self.width() - left - right, self.height() - top - bottom
        step = width / max(1, len(self.hours))
        rain_pen = QColor(90, 185, 245, 175)
        for level in (0, .5, 1):
            y = top + height * level
            painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
            painter.drawLine(int(left), int(y), int(left + width), int(y))
        for i, value in enumerate(self.rain):
            chance = max(0.0, min(100.0, float(value or 0)))
            bar_h = height * chance / 100
            painter.fillRect(QRectF(left + i * step + 2, top + height - bar_h, max(1, step - 4), bar_h), rain_pen)
        temps = [convert_temperature(float(value), self.unit) for value in self.temperatures]
        low, high = min(temps) - 2, max(temps) + 2
        span = max(1, high - low)
        points = []
        for i, value in enumerate(temps):
            points.append((left + i * step + step / 2, top + (high - value) / span * height))
        path = QPainterPath()
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        painter.setPen(QPen(QColor("#ffd08a"), 2))
        painter.drawPath(path)
        painter.setPen(QColor(255, 255, 255, 180))
        for i in range(0, len(self.hours), 3):
            label = "Now" if i == 0 else self.hours[i][11:16]
            painter.drawText(QRectF(left + i * step - 18, top + height + 8, 44, 18), Qt.AlignmentFlag.AlignCenter, label)
        painter.drawText(2, int(top + 8), "100%")
        painter.drawText(8, int(top + height), "0%")
        suffix = "K" if self.unit == "k" else "°"
        painter.drawText(int(left + width + 5), int(top + 8), f"{round(high)}{suffix}")
        painter.drawText(int(left + width + 5), int(top + height), f"{round(low)}{suffix}")


def convert_temperature(value_f, unit):
    if unit == "f":
        return value_f
    celsius = (value_f - 32) * 5 / 9
    return celsius + 273.15 if unit == "k" else celsius


def format_temperature(value_f, unit, spaced=False):
    value = math.floor(convert_temperature(float(value_f), unit) + .5)
    if unit == "k":
        return f"{value} K" if spaced else f"{value}K"
    suffix = f"°{unit.upper()}"
    return f"{value} {suffix}" if spaced else f"{value}{suffix}"


def format_location_label(location):
    name = str(location.get("name", "")).strip()
    parts = [part.strip() for part in str(location.get("display_name", "")).split(",") if part.strip()]
    country = parts[-1] if parts else ""
    if not name:
        return country or "Unknown Location"
    if not country or name.casefold() == country.casefold():
        return name
    return f"{name}, {country}"


def background_for_temperature(temp_f):
    stops = [
        (0, "#0081d3"), (10, "#007bc2"), (20, "#0071b2"),
        (30, "#2766a2"), (40, "#575591"), (50, "#94556b"),
        (60, "#af4744"), (70, "#bb4434"), (80, "#c94126"),
        (90, "#d6411b"), (100, "#e44211"),
    ]
    # JavaScript's Math.round rounds positive halves upward, unlike Python's
    # bankers' rounding.
    position = max(0, min(100, math.floor((float(temp_f) - 45) * 2.2 + .5)))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if a <= position <= b:
            ratio = (position - a) / (b - a)
            left, right = QColor(ca), QColor(cb)
            js_round = lambda value: math.floor(value + .5)
            return QColor(
                js_round(left.red() + (right.red() - left.red()) * ratio),
                js_round(left.green() + (right.green() - left.green()) * ratio),
                js_round(left.blue() + (right.blue() - left.blue()) * ratio),
            ).name()
    return stops[-1][1]


class TyphoonWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(APP_ID, "typhoon")
        self.network = Network(self)
        self.locations = self._json_setting("locations", [])
        self.location_index = min(int(self.settings.value("location_index", 0)), max(0, len(self.locations) - 1))
        self.weather = None
        self._refresh_generation = 0
        self._refresh_spin_stop_timer = QTimer(self)
        self._refresh_spin_stop_timer.setSingleShot(True)
        self._refresh_spin_stop_timer.setInterval(1000)
        self._refresh_spin_stop_timer.timeout.connect(lambda: self._set_refresh_spinning(False))
        self.drag_origin = None
        self.drag_enabled = True
        self._canvas_dragging = False
        self._validated_locations = {}
        self._location_validation_timers = {}
        self.aspect_ratio = 3 / 5
        self._resize_state = None
        self.climacon_font = self._load_font("fonts/Climacons.ttf", "Sans Serif")
        self.ui_font = self._load_font("fonts/ubuntu.ttf", "Sans Serif")
        QApplication.instance().setFont(QFont(self.ui_font, 11))
        self._setup_window()
        self._build_ui()
        self._initialize_tray()
        self._setup_launcher()
        self._apply_preferences()
        self._update_location_buttons()
        if not self.locations:
            self.stack.setCurrentWidget(self.first_location_page)
        QTimer.singleShot(0, self._update_chameleonic_color)
        QTimer.singleShot(0, self.refresh)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(int(self.settings.value("refresh_ms", 1_200_000)))

    def _load_font(self, name, fallback):
        font_id = QFontDatabase.addApplicationFont(resource(name))
        families = QFontDatabase.applicationFontFamilies(font_id)
        return families[0] if families else fallback

    def _json_setting(self, key, default):
        try:
            return json.loads(self.settings.value(key, json.dumps(default)))
        except (TypeError, ValueError):
            return default

    def _setup_window(self):
        self.setWindowTitle("Typhoon")
        self.setWindowIcon(QIcon(resource(APP_ICON)))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(210, 350)
        screen = QApplication.primaryScreen()
        if screen:
            maximum_height = round(screen.availableGeometry().height() * .9)
            self.setMaximumSize(round(maximum_height * self.aspect_ratio), maximum_height)
        size = self.settings.value("window_size")
        requested_width = size.width() if size else 300
        width, height = self._aspect_size_from_width(requested_width)
        self.resize(width, height)
        position = self.settings.value("window_position")
        if position:
            self.move(position)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.canvas_view = QGraphicsView(self)
        self.canvas_view.setFrameShape(QFrame.Shape.NoFrame)
        self.canvas_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.canvas_view.setStyleSheet("background: transparent; border: none;")
        self.canvas_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.canvas_view.viewport().installEventFilter(self)
        self.canvas_scene = QGraphicsScene(self.canvas_view)
        self.canvas_view.setScene(self.canvas_scene)
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setFixedSize(300, 500)
        self.card_proxy = self.canvas_scene.addWidget(self.card)
        self.canvas_scene.setSceneRect(0, 0, 300, 500)
        root.addWidget(self.canvas_view)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        self._top_bars = []
        self.stack = QStackedWidget()
        self.weather_page = self._build_weather_page()
        self.first_location_page = self._build_first_location_page()
        self.settings_page = self._build_settings_page()
        self.credits_page = self._build_credits_page()
        self.hourly_page = self._build_hourly_page()
        for page in (self.weather_page, self.first_location_page, self.settings_page, self.credits_page, self.hourly_page):
            self.stack.addWidget(page)
        card_layout.addWidget(self.stack)
        self.resize_handles = {
            edge: ResizeHandle(edge, self)
            for edge in ("left", "right", "bottom", "bottom-left", "bottom-right")
        }
        self._position_resize_handles()
        self.setFont(QFont(self.ui_font, 11))
        self.card.setStyleSheet(self._stylesheet("#575591"))
        self._apply_controls_position()

    def _location_entry_row(self, first_run=False):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        location_input = QLineEdit()
        location_input.setFixedSize(215, 29)
        location_input.setPlaceholderText("Location" if first_run else "Location: e.g. Boston, Kolkata, …")
        input_palette = location_input.palette()
        input_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#383838"))
        location_input.setPalette(input_palette)
        status = ToolButton(icon="sync.svg")
        status.stop_spinning(clear=True)
        status.setObjectName("locationStatus")
        status.setFixedSize(29, 29)
        status.setToolTip("Type a location to validate it")
        status.clicked.connect(lambda: self._commit_validated_location(location_input, status))
        location_input.returnPressed.connect(lambda: self._location_enter_pressed(location_input, status))
        location_input.textChanged.connect(lambda: self._schedule_location_validation(location_input, status))
        row.addWidget(location_input)
        row.addWidget(status)
        return row, location_input, status

    def _build_first_location_page(self):
        page = QWidget()
        page.setObjectName("firstLocationPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addLayout(self._top_bar())
        outer.addSpacing(30)
        panel = QFrame()
        panel.setObjectName("firstLocationPanel")
        panel.setFixedHeight(130)
        form = QVBoxLayout(panel)
        form.setContentsMargins(25, 25, 25, 10)
        form.setSpacing(8)
        entry_row, self.first_location_input, self.first_location_status = self._location_entry_row(first_run=True)
        form.addLayout(entry_row)
        example = QLabel("e.g. Boston, Kolkata, Paris")
        example.setObjectName("locationExample")
        form.addWidget(example)
        actions = QHBoxLayout()
        guess = QPushButton("Guess Location")
        guess.clicked.connect(lambda: self.guess_location(self.first_location_input))
        support = QPushButton("Support")
        support.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/archisman-panigrahi/typhoon/issues")))
        actions.addWidget(guess)
        actions.addWidget(support)
        actions.addStretch()
        form.addLayout(actions)
        outer.addWidget(panel)
        outer.addStretch()
        return page

    def _top_bar(self, back=None):
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 5, 0)
        bar.setSpacing(0)
        if back:
            button = ToolButton("‹")
            button.clicked.connect(back)
            bar.addWidget(button)
        else:
            close = ToolButton("×")
            close.setObjectName("windowToolButton")
            close.clicked.connect(self.close_or_hide)
            minimize = ToolButton("−")
            minimize.setObjectName("windowToolButton")
            minimize.clicked.connect(self.showMinimized)
            bar.addWidget(close)
            bar.addWidget(minimize)
        bar.addStretch()
        if back is None:
            self._top_bars.append(bar)
        return bar

    def _location_nav(self, page, settings_page=False):
        nav = QWidget(page)
        nav.setGeometry(155, -1, 54, 30)
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        previous = ToolButton("‹")
        remove = ToolButton("×")
        next_location = ToolButton("›")
        previous.setObjectName("navArrow")
        remove.setObjectName("navRemove")
        next_location.setObjectName("navArrow")
        previous.setFixedSize(14, 30)
        remove.setFixedSize(14, 30)
        next_location.setFixedSize(14, 30)
        for button in (previous, remove, next_location):
            button.enable_hover_opacity()
        previous.clicked.connect(lambda: self.navigate(-1))
        remove.clicked.connect(self.remove_location)
        next_location.clicked.connect(lambda: self.navigate(1))
        layout.addWidget(previous)
        layout.addWidget(remove)
        layout.addWidget(next_location)
        nav.raise_()
        if settings_page:
            self.settings_previous_button = previous
            self.settings_remove_button = remove
            self.settings_next_button = next_location
        else:
            self.previous_button = previous
            self.remove_button = remove
            self.next_button = next_location
        return nav

    def _build_weather_page(self):
        page = QWidget()
        page.setObjectName("weatherPage")
        self.actual_weather = QWidget(page)
        self.actual_weather.setObjectName("actualWeather")
        self.actual_weather.setGeometry(0, 0, 300, 500)
        top_widget = QWidget(page)
        top_widget.setGeometry(0, 0, 300, 30)
        top = self._top_bar()
        top_widget.setLayout(top)
        hourly = ToolButton(icon="clock-exclamation-svgrepo-com.svg")
        self.weather_hourly_button = hourly
        hourly.enable_hover_opacity()
        hourly.setToolTip("Next 24 hours")
        hourly.clicked.connect(lambda: self.stack.setCurrentWidget(self.hourly_page))
        settings = ToolButton(icon="settings.svg")
        self.weather_settings_button = settings
        settings.enable_hover_opacity()
        settings.clicked.connect(lambda: self.stack.setCurrentWidget(self.settings_page))
        sync = ToolButton(icon="sync.svg")
        sync.enable_hover_opacity()
        sync.clicked.connect(self.refresh)
        self.weather_sync_button = sync
        top.addWidget(hourly)
        top.addWidget(settings)
        top.addWidget(sync)
        self.weather_location_nav = self._location_nav(page)
        self.city = QPushButton("", self.actual_weather)
        self.city.setFlat(True)
        self.city.setCursor(Qt.CursorShape.PointingHandCursor)
        self.city.clicked.connect(self.open_map)
        self.city.setObjectName("city")
        self.city.setGeometry(0, 30, 300, 50)
        self.weather_icon = GlyphLabel("", self.actual_weather)
        self.weather_icon.setObjectName("weatherIcon")
        initial_weather_font = QFont(self.climacon_font)
        initial_weather_font.setPixelSize(200)
        self.weather_icon.setFont(initial_weather_font)
        self.weather_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weather_icon.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.weather_icon.setGeometry(0, 71, 300, 241)
        details_widget = QWidget(self.actual_weather)
        details_widget.setGeometry(0, 266, 300, 64)
        details = QHBoxLayout(details_widget)
        details.setContentsMargins(10, 0, 5, 0)
        details.setSpacing(0)
        temperature_widget = QWidget(details_widget)
        temperature_widget.setFixedWidth(160)
        self.thermometer = GlyphLabel("Q", temperature_widget)
        # 49pt is approximately the original 65 CSS pixels.
        thermometer_font = QFont(self.climacon_font)
        thermometer_font.setPixelSize(65)
        self.thermometer.setFont(thermometer_font)
        self.thermometer.set_glyph_offset(9, 0)
        self.thermometer.setGeometry(0, 0, 44, 64)
        self.temperature = QLabel("", temperature_widget)
        self.temperature.setObjectName("temperature")
        self.temperature.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Give the degree/unit glyphs overhang space on both sides while
        # retaining the CSS column's right edge.
        # Keep the text anchored at the same point while leaving extra widget
        # space for the final C/F/K glyph's right-side overhang.
        self.temperature.setGeometry(34, 0, 126, 64)
        self.wind = QLabel("")
        self.wind.setObjectName("details")
        humidity_row = QHBoxLayout()
        humidity_row.setContentsMargins(0, 0, 0, 0)
        humidity_row.setSpacing(5)
        humidity_icon = QLabel()
        humidity_icon.setPixmap(QIcon(resource("humidity.svg")).pixmap(14, 19))
        humidity_icon.setFixedSize(15, 21)
        self.humidity = QLabel("")
        self.humidity.setObjectName("details")
        metrics_widget = QWidget(details_widget)
        metrics = QVBoxLayout(metrics_widget)
        metrics.setContentsMargins(8, 0, 0, 0)
        metrics.setSpacing(0)
        metrics.addWidget(self.wind)
        humidity_row.addWidget(humidity_icon)
        humidity_row.addWidget(self.humidity)
        humidity_row.addStretch()
        metrics.addLayout(humidity_row)
        self.compass_widget = CompassWidget()
        details.addWidget(temperature_widget)
        details.addSpacing(2)
        details.addWidget(metrics_widget, 1)
        details.addWidget(self.compass_widget)
        extra_widget = QWidget(self.actual_weather)
        extra_widget.setGeometry(0, 333, 300, 30)
        extra = QHBoxLayout(extra_widget)
        extra.setContentsMargins(20, 0, 59, 0)
        self.feels = QLabel("")
        self.feels.setObjectName("feelsLike")
        self.rain = QPushButton("")
        self.rain.setObjectName("rainButton")
        self.rain.setFlat(True)
        self.rain.setText("")
        rain_layout = QHBoxLayout(self.rain)
        rain_layout.setContentsMargins(0, 0, 3, 0)
        rain_layout.setSpacing(0)
        rain_icon = GlyphLabel("{")
        rain_font = QFont(self.climacon_font)
        rain_font.setPixelSize(26)
        rain_icon.setFont(rain_font)
        rain_icon.set_glyph_offset(-2, 0)
        rain_icon.setFixedWidth(23)
        self.rain_value = QLabel("")
        self.rain_value.setObjectName("rainValue")
        self.rain_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        rain_layout.addWidget(rain_icon)
        rain_layout.addWidget(self.rain_value)
        self.rain.clicked.connect(lambda: self.stack.setCurrentWidget(self.hourly_page))
        extra.addWidget(self.feels)
        extra.addStretch()
        extra.addWidget(self.rain)
        week_widget = QWidget(self.actual_weather)
        week_widget.setGeometry(0, 381, 300, 111)
        week = QHBoxLayout(week_widget)
        week.setContentsMargins(0, 0, 0, 0)
        week.setSpacing(0)
        self.days = [ForecastDay(self.climacon_font) for _ in range(4)]
        for day in self.days:
            week.addWidget(day)

        self.weather_error_panel = QWidget(page)
        self.weather_error_panel.setObjectName("weatherErrorPanel")
        self.weather_error_panel.setGeometry(0, 60, 300, 145)
        error_layout = QVBoxLayout(self.weather_error_panel)
        error_layout.setContentsMargins(25, 25, 25, 25)
        error_layout.setSpacing(12)
        error_text = QLabel(
            "Could not connect to internet.<br>Check your internet connection."
        )
        error_text.setObjectName("weatherErrorText")
        retry = QPushButton("TRY AGAIN")
        retry.setObjectName("weatherRetryButton")
        retry.setFixedSize(82, 30)
        retry.clicked.connect(self._retry_weather)
        error_layout.addWidget(error_text)
        error_layout.addWidget(retry, 0, Qt.AlignmentFlag.AlignLeft)
        self.weather_error_panel.hide()
        self._set_weather_content_visible(False)
        top_widget.raise_()
        self.weather_location_nav.raise_()
        return page

    def _build_settings_page(self):
        page = QWidget()
        page.setObjectName("settingsPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        top = self._top_bar()
        close_settings = ToolButton(icon="settings.svg")
        close_settings.enable_hover_opacity()
        close_settings.setToolTip("Close settings")
        close_settings.clicked.connect(lambda: self.stack.setCurrentWidget(self.weather_page))
        refresh = ToolButton(icon="sync.svg")
        refresh.enable_hover_opacity()
        refresh.clicked.connect(lambda: (self.stack.setCurrentWidget(self.weather_page), self.refresh()))
        self.settings_sync_button = refresh
        top.addWidget(close_settings)
        top.addWidget(refresh)
        outer.addLayout(top)
        self.settings_location_nav = self._location_nav(page, settings_page=True)
        outer.addSpacing(29)
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("settingsContent")
        form = QVBoxLayout(content)
        form.setContentsMargins(25, 25, 25, 16)
        form.setSpacing(9)
        entry_row, self.location_input, self.location_status = self._location_entry_row()
        form.addLayout(entry_row)
        form.addSpacing(3)
        actions = QHBoxLayout()
        guess = QPushButton("Guess Location")
        guess.setObjectName("settingsAction")
        guess.setFixedSize(102, 29)
        guess.clicked.connect(lambda: self.guess_location(self.location_input))
        report = QPushButton("Report Bugs")
        report.setObjectName("settingsAction")
        report.setFixedSize(89, 29)
        report.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/archisman-panigrahi/typhoon/issues")))
        actions.addWidget(guess)
        actions.addWidget(report)
        actions.addStretch()
        form.addLayout(actions)
        self.unit_group, unit_row = self._choice_row((("°C", "c"), ("°F", "f"), ("K", "k")), "unit", "c")
        form.addLayout(unit_row)
        self.speed_group, speed_row = self._choice_row((("mph", "mph"), ("km/h", "kph"), ("m/s", "ms")), "speed", "kph")
        form.addLayout(speed_row)
        form.addSpacing(6)
        colors = QHBoxLayout()
        colors.setSpacing(1)
        gradient = QPushButton()
        gradient.setObjectName("gradientSwatch")
        gradient.setToolTip("Temperature-based color")
        gradient.setFixedSize(22, 22)
        gradient.clicked.connect(lambda: self.set_color("gradient"))
        chameleon = QPushButton()
        chameleon.setToolTip("Chameleonic color")
        chameleon.setIcon(QIcon(resource("chameleon-svgrepo-com.svg")))
        chameleon.setIconSize(QSize(17, 17))
        chameleon.setFixedSize(22, 22)
        chameleon.clicked.connect(lambda: self.set_color("chameleonic"))
        custom = QPushButton()
        custom.setToolTip("Pick a custom color")
        custom.setIcon(QIcon(resource("dropper-svgrepo-com.svg")))
        custom.setIconSize(QSize(17, 17))
        custom.setFixedSize(22, 22)
        custom.clicked.connect(self.pick_color)
        colors.addWidget(gradient)
        colors.addWidget(chameleon)
        colors.addWidget(custom)
        for index, color in enumerate(PALETTE):
            button = QPushButton()
            button.setToolTip(color)
            button.setFixedSize(17, 22)
            button.setStyleSheet(f"background:{color}; border:2px solid #292929; padding:0")
            button.clicked.connect(lambda _checked=False, value=color: self.set_color(value))
            colors.addWidget(button)
        colors.addStretch()
        form.addLayout(colors)
        self.launcher_check = QCheckBox("Launcher Count")
        self.notification_check = QCheckBox("Notifications")
        self.tray_check = QCheckBox("System tray")
        for checkbox, key, default in ((self.launcher_check, "launcher", True), (self.notification_check, "notifications", True), (self.tray_check, "tray", False)):
            checkbox.setChecked(self.settings.value(key, default, type=bool))
            checkbox.toggled.connect(lambda value, setting=key: self.preference_changed(setting, value))
        primary_options = QHBoxLayout()
        primary_options.setSpacing(8)
        primary_options.addWidget(self.launcher_check)
        primary_options.addWidget(self.notification_check)
        primary_options.addStretch()
        form.addLayout(primary_options)
        tray_controls = QHBoxLayout()
        tray_controls.setSpacing(1)
        self.tray_check.setFixedWidth(94)
        tray_controls.addWidget(self.tray_check)
        tray_controls.addStretch()
        tray_controls.addWidget(QLabel("Control: Left"))
        self.position_toggle = ToggleSwitch()
        self.position_toggle.setObjectName("positionToggle")
        self.position_toggle.setChecked(str(self.settings.value("controls_position", "left")) == "right")
        self.position_toggle.toggled.connect(lambda checked: self.preference_changed("controls_position", "right" if checked else "left"))
        tray_controls.addWidget(self.position_toggle)
        tray_controls.addWidget(QLabel("Right"))
        form.addLayout(tray_controls)
        form.addSpacing(7)
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity"))
        opacity_row.addSpacing(9)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setObjectName("opacitySlider")
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setFixedWidth(170)
        self.opacity_slider.setValue(round(float(self.settings.value("opacity", .8)) * 100))
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addStretch()
        form.addLayout(opacity_row)
        form.addSpacing(2)
        footer = QHBoxLayout()
        footer.setContentsMargins(9, 0, 0, 0)
        footer.setSpacing(7)
        credits = QPushButton("CREDITS")
        credits.setObjectName("settingsAction")
        credits.setFixedSize(68, 30)
        credits.clicked.connect(self.show_credits)
        homepage = QPushButton("HOMEPAGE")
        homepage.setObjectName("settingsAction")
        homepage.setFixedSize(90, 30)
        homepage.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://archisman-panigrahi.github.io/typhoon")))
        reset = QPushButton("RESET")
        reset.setObjectName("settingsAction")
        reset.setFixedSize(59, 30)
        reset.clicked.connect(self.reset_settings)
        footer.addWidget(credits)
        footer.addWidget(homepage)
        footer.addWidget(reset)
        footer.addStretch()
        form.addLayout(footer)
        form.addSpacing(6)
        hint = QLabel("Add multiple locations by typing a new\nlocation in the searchbox above!")
        hint.setObjectName("settingsHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addWidget(hint)
        form.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return page

    def _build_credits_page(self):
        page = QWidget()
        page.setObjectName("creditsPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addLayout(self._top_bar())
        outer.addSpacing(29)

        body = QWidget()
        body.setObjectName("creditsBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(25, 18, 25, 10)
        layout.setSpacing(0)

        back = ToolButton(icon="back.svg")
        back.setObjectName("creditsBack")
        back.setIconSize(QSize(20, 20))
        back.clicked.connect(lambda: self.stack.setCurrentWidget(self.settings_page))
        layout.addWidget(back, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(6)

        link_style = CreditLinkLabel.LINK_STYLE
        title = CreditLinkLabel(
            f'<a style="{link_style}" href="https://archisman-panigrahi.github.io/typhoon">'
            "Typhoon</a> 1.9.0"
        )
        title.setObjectName("creditsTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(36)
        layout.addWidget(title)

        intro = CreditLinkLabel(
            "Typhoon is a stylish weather application for<br>"
            "GNU/Linux. It is and always will be free.<br>"
            f'<a style="{link_style}" href="https://github.com/apandada1/typhoon/">'
            "Source code</a> is released under "
            f'<a style="{link_style}" href="http://www.gnu.org/licenses/gpl.html">GPL-3</a>.'
        )
        intro.setObjectName("creditsText")
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro.setFixedHeight(60)
        layout.addWidget(intro)
        layout.addSpacing(10)

        credits = CreditLinkLabel(
            f'•&nbsp; Based on <a style="{link_style}" href="https://github.com/consindo/stormcloud/tree/'
            'e7ef8e131466d477075e92337e502c3cac004ee2">Stormcloud 1.1</a> by '
            f'<a style="{link_style}" href="https://github.com/consindo">Jono Cooper</a>.<br>'
            "•&nbsp; Currently developed and maintained by<br>"
            f'&nbsp;&nbsp;&nbsp;<a style="{link_style}" href="https://github.com/archisman-panigrahi">'
            "Archisman Panigrahi</a> and ChatGPT :)<br>"
            f'•&nbsp; Icons (<a style="{link_style}" href="https://web.archive.org/web/20160531215708/'
            'http://adamwhitcroft.com/climacons/">Climacons</a>) by '
            f'<a style="{link_style}" href="https://adamwhitcroft.com/">Adam Whitcroft</a>.<br>'
            f'•&nbsp; Powered by <a style="{link_style}" href="https://open-meteo.com/">Open Meteo</a>, '
            f'<a style="{link_style}" href="https://www.openstreetmap.org/">OpenStreetMap</a><br>'
            f'&nbsp;&nbsp;&nbsp;and <a style="{link_style}" href="https://ipapi.co/">ipapi</a>.'
        )
        credits.setObjectName("creditsText")
        credits.setFixedHeight(96)
        layout.addWidget(credits)

        heading = QLabel("Significant Contributors:")
        heading.setObjectName("creditsHeading")
        heading.setFixedHeight(24)
        layout.addWidget(heading)

        contributors = CreditLinkLabel(
            "•&nbsp; Andy Van Pelt<br>"
            f'•&nbsp; <a style="{link_style}" href="https://github.com/soumyaDghosh">'
            "Soumyadeep Ghosh</a><br>"
            f'•&nbsp; <a style="{link_style}" href="https://github.com/zlatanvasovic">'
            "Zlatan Vasović</a>"
        )
        contributors.setObjectName("creditsText")
        contributors.setFixedHeight(58)
        layout.addWidget(contributors)

        layout.addStretch()

        dedication = QLabel(
            "To those whose warmth brings sunshine and\n"
            "calm to every storm and whose light\n"
            "brightens the sky 💖"
        )
        dedication.setObjectName("creditsText")
        dedication.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dedication.setFixedHeight(52)
        layout.addWidget(dedication)

        outer.addWidget(body)
        return page

    def _choice_row(self, choices, key, default):
        group = QButtonGroup(self)
        row = QHBoxLayout()
        row.setSpacing(0)
        selected = str(self.settings.value(key, default))
        for label, value in choices:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty("choice", True)
            button.setFixedSize(41 if key == "unit" else 42, 41)
            button.setChecked(value == selected)
            button.clicked.connect(lambda _checked=False, setting=key, result=value: self.preference_changed(setting, result))
            group.addButton(button)
            row.addWidget(button)
        row.addStretch()
        return group, row

    def _build_hourly_page(self):
        page = QWidget()
        page.setObjectName("hourlyPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.addLayout(self._top_bar(lambda: self.stack.setCurrentWidget(self.weather_page)))
        title = QLabel("Next 24 hours")
        title.setObjectName("panelTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        self.hourly_location = QLabel("")
        self.hourly_location.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hourly_location)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chart = ForecastChart()
        scroll.setWidget(self.chart)
        layout.addWidget(scroll)
        return page

    def _stylesheet(self, color):
        tick_path = resource("tick.svg").replace("\\", "/")
        return f"""
            #card {{ background: {color}; color: white; }}
            QWidget {{ color: white; }}
            QPushButton {{ border: 1px solid rgba(20,20,20,.65); background: rgba(30,30,30,.28); padding: 5px; }}
            QPushButton:hover, QPushButton:checked {{ background: rgba(255,255,255,.18); }}
            #toolButton, #windowToolButton, #navArrow, #navRemove {{ border: none; padding: 0; }}
            #toolButton {{ background: transparent; font-size: 24px; }}
            #windowToolButton {{ background: rgba(0,0,0,.045); font-size: 24px; font-weight: bold; }}
            #navArrow {{ background: transparent; font-size: 32px; font-weight: normal; }}
            #navRemove {{ background: transparent; font-size: 28px; font-weight: normal; }}
            #toolButton:hover, #navArrow:hover, #navRemove:hover {{ background: transparent; }}
            #windowToolButton:hover {{ background: rgba(0,0,0,.18); }}
            QLineEdit {{ color: #222; background: white; border: 2px solid #333; padding: 6px; }}
            QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
            #settingsPage {{ background: transparent; }}
            #firstLocationPage {{ background: transparent; }}
            #firstLocationPanel {{ background: #444; }}
            #firstLocationPanel QLineEdit {{ padding: 2px 9px; font-size: 16px; }}
            #firstLocationPanel QPushButton {{ padding: 2px 8px; font-size: 16px; }}
            #locationExample {{ font-size: 17px; }}
            #locationStatus {{ border: none; background: transparent; padding: 0; font-family: sans-serif; font-size: 22px; font-weight: bold; }}
            #locationStatus:hover {{ background: rgba(255,255,255,.14); }}
            #settingsScroll, #settingsContent {{ background: #444; }}
            #creditsBody {{ background: #444; }}
            #creditsBack, #creditsBack:hover {{ border: none; background: transparent; padding: 0; }}
            #creditsTitle {{ font-size: 28px; font-weight: bold; }}
            #creditsText {{ font-size: 15px; }}
            #creditsHeading {{ font-size: 18px; font-weight: bold; }}
            #weatherErrorPanel {{ background: #444; }}
            #weatherErrorText {{ font-size: 16px; }}
            #weatherRetryButton {{ border: 2px solid #222; background: #333; padding: 1px 5px; font-size: 16px; }}
            #weatherRetryButton:hover {{ background: #555; }}
            #settingsContent QPushButton {{ border: 2px solid #222; background: #333; padding: 1px 4px; font-size: 16px; }}
            #settingsContent QPushButton:hover, #settingsContent QPushButton:checked {{ background: #555; }}
            #settingsContent #settingsAction {{ font-size: 17px; letter-spacing: -1px; }}
            #settingsContent QLineEdit {{ padding: 2px 9px; font-size: 15px; }}
            #settingsContent QLabel {{ font-size: 16px; }}
            #settingsContent QCheckBox {{ spacing: 6px; font-size: 16px; }}
            #settingsContent QCheckBox::indicator {{ width: 16px; height: 16px; border: 2px solid #222; background: #333; }}
            #settingsContent QCheckBox::indicator:checked {{ image: url("{tick_path}"); }}
            #settingsContent #locationStatus {{ border: none; background: transparent; padding: 0; font-family: sans-serif; font-size: 22px; font-weight: bold; }}
            #gradientSwatch {{ background: qlineargradient(x1:0,y1:1,x2:0,y2:0, stop:0 #e44211, stop:.35 #f09609, stop:.7 #575591, stop:1 #1ba1e2); border:2px solid #292929; padding:0; }}
            #opacitySlider::groove:horizontal {{ height: 5px; border-radius: 2px; background: #777; }}
            #opacitySlider::sub-page:horizontal {{ background: #aaa; }}
            #opacitySlider::handle:horizontal {{ width: 30px; margin: -8px 0; border-radius: 10px; background: white; }}
            #settingsHint {{ font-size: 16px; }}
            #hourlyPage {{ background: #444; }}
            #city {{ border: none; background: transparent; font-size: 24px; letter-spacing: -2px; padding-top: 15px; }}
            #weatherIcon {{ background: transparent; }}
            #temperature {{ font-size: 65px; letter-spacing: -5px; padding-right: 12px; }}
            #details {{ font-size: 25px; letter-spacing: -2px; }}
            #feelsLike {{ font-size: 22px; }}
            #rainButton {{ border: none; background: transparent; font-size: 22px; padding: 2px 8px; }}
            #rainButton:hover {{ background: rgba(255,255,255,.14); border-radius: 4px; }}
            #rainValue {{ font-size: 22px; }}
            #forecastDay {{ font-size: 18px; }}
            #forecastTemp {{ font-size: 18px; }}
            #forecastTemp[compact="true"] {{ font-size: 15px; }}
            #panelTitle {{ font-size: 22px; }}
            QCheckBox {{ spacing: 8px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
        """

    def _apply_preferences(self):
        self.card_proxy.setOpacity(float(self.settings.value("opacity", .8)))
        self._apply_background()
        self._update_tray_visibility()
        self._apply_controls_position()

    def _apply_controls_position(self):
        right = str(self.settings.value("controls_position", "left")) == "right"
        direction = (
            QBoxLayout.Direction.RightToLeft
            if right else QBoxLayout.Direction.LeftToRight
        )
        for bar in getattr(self, "_top_bars", []):
            bar.setDirection(direction)
            bar.setContentsMargins(5, 0, 0, 0) if right else bar.setContentsMargins(0, 0, 5, 0)

        nav_x = 300 - 155 - 54 if right else 155
        for name in ("weather_location_nav", "settings_location_nav"):
            nav = getattr(self, name, None)
            if nav is not None:
                nav.move(nav_x, -1)

    def preference_changed(self, key, value):
        self.settings.setValue(key, value)
        if key == "tray":
            self._set_tray_enabled(bool(value))
        elif key == "controls_position":
            self._apply_controls_position()
        if self.weather and key in ("unit", "speed"):
            self.render_weather()

    def set_color(self, color):
        self.settings.setValue("color", color)
        self._apply_background()
        if color == "chameleonic":
            self._update_chameleonic_color()

    def pick_color(self):
        color = QColorDialog.getColor(QColor(str(self.settings.value("custom_color", "#575591"))), self)
        if color.isValid():
            self.settings.setValue("custom_color", color.name())
            self.set_color("custom")

    def _apply_background(self):
        choice = str(self.settings.value("color", "gradient"))
        if choice == "gradient":
            color = background_for_temperature(self.weather["current"]["temperature_2m"]) if self.weather else "#575591"
        elif choice == "custom":
            color = str(self.settings.value("custom_color", "#575591"))
        elif choice == "chameleonic":
            color = str(self.settings.value("special_color", QApplication.palette().highlight().color().name()))
        else:
            color = choice
        self.card.setStyleSheet(self._stylesheet(color))

    def _set_chameleonic_color(self, color):
        color = QColor(color)
        if not color.isValid():
            return
        self.settings.setValue("special_color", color.name())
        if str(self.settings.value("color", "gradient")) == "chameleonic":
            self._apply_background()

    def _update_chameleonic_color(self):
        """Match master's wallpaper -> representative -> accent fallback chain."""
        try:
            color = self._extract_dominant_color(self.get_wallpaper_path())
            if color:
                self._set_chameleonic_color(color)
                return
        except Exception:
            pass

        if not IS_WINDOWS:
            try:
                output = subprocess.check_output(["xprop", "-root"], text=True)
                line = next(
                    line for line in output.splitlines()
                    if "_GNOME_BACKGROUND_REPRESENTATIVE_COLORS" in line
                )
                rgb_string = line.split('"')[1].strip()
                red, green, blue = (int(value) for value in rgb_string[4:-1].split(","))
                self._set_chameleonic_color(QColor(red, green, blue))
                return
            except Exception:
                pass

        self._set_chameleonic_color(self._get_accent_color())

    def _extract_dominant_color(self, wallpaper_path):
        if not wallpaper_path:
            return None
        if wallpaper_path.lower().endswith(".svg"):
            if cairosvg is None:
                return None
            image = QImage()
            image.loadFromData(
                cairosvg.svg2png(url=wallpaper_path, output_width=16, output_height=16),
                "PNG",
            )
        else:
            image = QImage(wallpaper_path)
        if image.isNull():
            return None
        tiny = image.scaled(
            1, 1,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return tiny.pixelColor(0, 0).name() if not tiny.isNull() else None

    def _get_accent_color(self):
        if IS_WINDOWS:
            return self._get_windows_accent_color()

        if Xdp is not None:
            try:
                value = Xdp.Portal().get_settings().read_value(
                    "org.freedesktop.appearance", "accent-color"
                )
                value = value.unpack() if hasattr(value, "unpack") else value
                if value is not None and len(value) == 3:
                    return QColor(*(round(float(channel) * 255) for channel in value))
            except Exception:
                pass

        if dbus is not None:
            try:
                portal = dbus.SessionBus().get_object(
                    "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
                )
                value = dbus.Interface(
                    portal, "org.freedesktop.portal.Settings"
                ).Read("org.freedesktop.appearance", "accent-color")
                if value is not None and len(value) == 3:
                    return QColor(*(round(float(channel) * 255) for channel in value))
            except Exception:
                pass
        return QApplication.palette().highlight().color()

    @staticmethod
    def _windows_registry_dword(path, name):
        if winreg is None:
            return None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                value, _kind = winreg.QueryValueEx(key, name)
                return value if isinstance(value, int) else None
        except Exception:
            return None

    def _get_windows_accent_color(self):
        value = self._windows_registry_dword(
            r"Software\Microsoft\Windows\DWM", "ColorizationColor"
        )
        if value is not None:
            return QColor((value >> 16) & 0xff, (value >> 8) & 0xff, value & 0xff)
        value = self._windows_registry_dword(
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent",
            "AccentColorMenu",
        )
        if value is not None:
            return QColor(value & 0xff, (value >> 8) & 0xff, (value >> 16) & 0xff)
        return QApplication.palette().highlight().color()

    def _get_primary_monitor(self):
        try:
            lines = subprocess.check_output(["xrandr", "--current"], text=True).splitlines()
            connected = [line for line in lines if " connected" in line]
            primary = next((line for line in connected if " primary " in line), None)
            return (primary or connected[0]).split()[0] if connected else None
        except Exception:
            return None

    def get_wallpaper_path(self):
        if IS_WINDOWS:
            if winreg is None:
                raise RuntimeError("Windows registry support is unavailable")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
                wallpaper, _kind = winreg.QueryValueEx(key, "WallPaper")
            if not str(wallpaper).strip():
                raise RuntimeError("Windows wallpaper path is empty")
            return str(wallpaper).strip()

        if os.environ.get("FLATPAK_ID") or os.environ.get("SNAP"):
            raise RuntimeError("Use the desktop portal inside a sandbox")
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        wallpaper = None
        if "gnome" in desktop:
            wallpaper = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                text=True,
            ).strip().strip("'")
        elif "cinnamon" in desktop:
            wallpaper = subprocess.check_output(
                ["gsettings", "get", "org.cinnamon.desktop.background", "picture-uri"],
                text=True,
            ).strip().strip("'")
        elif "mate" in desktop:
            wallpaper = subprocess.check_output(
                ["gsettings", "get", "org.mate.background", "picture-filename"],
                text=True,
            ).strip().strip("'")
        elif "xfce" in desktop:
            monitor = self._get_primary_monitor()
            if not monitor:
                raise RuntimeError("Could not detect the primary monitor")
            wallpaper = subprocess.check_output(
                ["xfconf-query", "-c", "xfce4-desktop", "-p",
                 f"/backdrop/screen0/monitor{monitor}/workspace0/last-image"],
                text=True,
            ).strip()
        elif "kde" in desktop:
            config_path = os.path.expanduser(
                "~/.config/plasma-org.kde.plasma.desktop-appletsrc"
            )
            with open(config_path, encoding="utf-8") as config_file:
                for line in config_file:
                    if line.strip().startswith("Image="):
                        wallpaper = line.strip().split("=", 1)[1]
                        break
            parsed = urlparse(wallpaper or "")
            wallpaper = unquote(parsed.path) if parsed.scheme == "file" else wallpaper
            if wallpaper and os.path.isdir(wallpaper):
                images = wallpaper if os.path.basename(wallpaper) == "images" else os.path.join(wallpaper, "contents", "images")
                candidates = glob.glob(os.path.join(images, "*"))
                wallpaper = next((path for path in candidates if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp"))), wallpaper)
        elif "lxde" in desktop or "labwc:wlroots" in desktop:
            files = glob.glob(os.path.expanduser("~/.config/pcmanfm/*/desktop-items-*.conf"))
            monitor = self._get_primary_monitor()
            if monitor:
                files.sort(key=lambda path: 0 if monitor in path else 1)
            for path in files:
                config = configparser.ConfigParser()
                config.read(path)
                if config.has_option("*", "wallpaper"):
                    wallpaper = config.get("*", "wallpaper")
                    break
        else:
            raise RuntimeError(f"Unsupported desktop environment: {desktop}")

        if not wallpaper:
            raise RuntimeError("Could not determine the wallpaper path")
        parsed = urlparse(wallpaper)
        return unquote(parsed.path) if parsed.scheme == "file" else wallpaper

    def _schedule_location_validation(self, location_input, status):
        self._validated_locations.pop(location_input, None)
        status.stop_spinning(clear=True)
        status.setText("")
        status.setToolTip("Type a location to validate it")
        timer = self._location_validation_timers.get(location_input)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._validate_location(location_input, status))
            self._location_validation_timers[location_input] = timer
        if location_input.text().strip():
            timer.start(1000)
        else:
            timer.stop()

    def _location_enter_pressed(self, location_input, status):
        pending = self._validated_locations.get(location_input)
        if pending and pending[0] == location_input.text().strip():
            self._commit_validated_location(location_input, status)
        else:
            self._validate_location(location_input, status)

    def _validate_location(self, location_input, status):
        query = location_input.text().strip()
        if not query:
            return
        status.start_spinning()
        status.setToolTip("Checking location…")
        url = "https://nominatim.openstreetmap.org/search?" + urlencode({"q": query, "format": "jsonv2", "limit": 1})

        def complete(data, error):
            if location_input.text().strip() != query:
                return
            if error or not data:
                self._validated_locations.pop(location_input, None)
                status.stop_spinning(clear=True)
                status.setText("×")
                status.setToolTip("Location not found")
                return
            item = data[0]
            location = {"name": item.get("name") or item.get("display_name", query).split(",")[0], "display_name": item.get("display_name", query), "lat": float(item["lat"]), "lon": float(item["lon"])}
            self._validated_locations[location_input] = (query, location)
            status.stop_spinning(clear=True)
            status.setText("✓")
            status.setToolTip("Load weather for this location")

        self.network.get_json(url, complete)

    def _commit_validated_location(self, location_input, status):
        pending = self._validated_locations.get(location_input)
        if not pending or pending[0] != location_input.text().strip():
            self._validate_location(location_input, status)
            return
        location = pending[1]
        match = next((old for old in self.locations if abs(old["lat"] - location["lat"]) < .0001 and abs(old["lon"] - location["lon"]) < .0001), None)
        if match is None:
            self.locations.append(location)
            match = location
        self.location_index = self.locations.index(match)
        self._save_locations()
        self._validated_locations.pop(location_input, None)
        location_input.clear()
        status.setText("")
        self.stack.setCurrentWidget(self.weather_page)
        self.refresh()

    def guess_location(self, location_input=None):
        location_input = location_input or self.location_input
        def complete(data, error):
            if error or not data or not data.get("city") or not data.get("region") or not data.get("country"):
                self.show_error("Could not determine your location.")
            else:
                location_input.setText(f"{data['city']}, {data['region']}, {data['country']}")
        self.network.get_json("https://ipapi.co/json/", complete)

    def refresh(self):
        if not self.locations:
            self._refresh_spin_stop_timer.stop()
            self._set_refresh_spinning(False)
            self.stack.setCurrentWidget(self.first_location_page)
            return
        if self.weather is None:
            self._set_weather_content_visible(False)
        self.weather_error_panel.hide()
        self._refresh_generation += 1
        request_generation = self._refresh_generation
        self._refresh_spin_stop_timer.stop()
        self._set_refresh_spinning(True)
        location = self.locations[self.location_index]
        params = {
            "latitude": location["lat"], "longitude": location["lon"], "timezone": "auto",
            "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
            "current_weather": "true",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,wind_direction_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "forecast_days": 7,
        }
        def complete(data, error):
            if request_generation != self._refresh_generation:
                return
            self._refresh_spin_stop_timer.start()
            current = self._current_weather_from_web_response(data) if data else None
            if error or not current:
                self._show_weather_network_error()
                return
            data["current"] = current
            self.weather = data
            self.render_weather()

        self.network.get_json("https://api.open-meteo.com/v1/forecast?" + urlencode(params), complete)

    def _set_weather_content_visible(self, visible):
        self.actual_weather.setVisible(visible)
        self.weather_location_nav.setVisible(visible)
        self.weather_hourly_button.setVisible(visible)
        self.weather_settings_button.setVisible(visible)

    def _show_weather_network_error(self):
        self._set_weather_content_visible(False)
        self.weather_error_panel.show()
        self.weather_error_panel.raise_()

    def _retry_weather(self):
        self.weather_error_panel.hide()
        self.weather = None
        self.refresh()

    def _set_refresh_spinning(self, spinning):
        for name in ("weather_sync_button", "settings_sync_button"):
            button = getattr(self, name, None)
            if button:
                button.start_spinning() if spinning else button.stop_spinning()

    @classmethod
    def _current_weather_from_web_response(cls, data):
        """Normalize the same current_weather/hourly rows used by script.js."""
        current = data.get("current_weather") or {}
        hourly = data.get("hourly") or {}
        times = hourly.get("time") or []
        if not current or not times:
            return None
        index = cls._current_hour_index(times, current.get("time", ""))

        def hourly_value(name, fallback=0):
            values = hourly.get(name) or []
            return values[index] if index < len(values) else fallback

        return {
            "time": current.get("time", ""),
            "temperature_2m": current.get("temperature"),
            "is_day": current.get("is_day", 1),
            "weather_code": current.get("weathercode", current.get("weather_code", 0)),
            "wind_speed_10m": current.get("windspeed", current.get("wind_speed_10m", 0)),
            "wind_direction_10m": hourly_value("wind_direction_10m", current.get("winddirection", 0)),
            "relative_humidity_2m": hourly_value("relative_humidity_2m"),
            "apparent_temperature": hourly_value("apparent_temperature", current.get("temperature")),
        }

    def _set_current_weather_icon(self, code, is_day):
        code = int(code or 0)
        is_day = bool(is_day)
        icon = weather_icon(code, is_day)
        font_size, css_left, css_top = WEATHER_ICON_CSS.get(code, (200, 22, 75))
        if icon == "/":
            font_size, css_left, css_top = 300, 20, 30

        icon_font = QFont(self.climacon_font)
        icon_font.setPixelSize(font_size)
        metrics = QFontMetricsF(icon_font)
        bounds = metrics.tightBoundingRect(icon)

        # CSS centers the glyph's advance box in a 300px-wide element whose
        # top/left are then manually adjusted. GlyphLabel centers its visible
        # bounds, so account for that metrics difference explicitly.
        desired_left = css_left + (300 - metrics.horizontalAdvance(icon)) / 2 + bounds.x()
        centered_left = (self.weather_icon.width() - bounds.width()) / 2
        desired_top = css_top + metrics.ascent() + bounds.y()
        centered_top = (self.weather_icon.height() - bounds.height()) / 2 + self.weather_icon.y()

        self.weather_icon.setFont(icon_font)
        self.weather_icon.set_glyph_offset(desired_left - centered_left, desired_top - centered_top)
        self.weather_icon.setText(icon)

    def render_weather(self):
        data, current = self.weather, self.weather["current"]
        location = self.locations[self.location_index]
        unit = str(self.settings.value("unit", "c"))
        speed_unit = str(self.settings.value("speed", "kph"))
        self.city.setText(format_location_label(location).upper())
        self.hourly_location.setText(location.get("display_name", location["name"]))
        self._set_current_weather_icon(current.get("weather_code"), current.get("is_day", 1))
        self.temperature.setText(format_temperature(current["temperature_2m"], unit))
        temp_f = float(current["temperature_2m"])
        self.thermometer.setText("_" if temp_f < 32 else "+" if temp_f < 55 else "Q" if temp_f < 85 else "W" if temp_f < 100 else "E")
        self.feels.setText("Feels Like: " + format_temperature(current.get("apparent_temperature", current["temperature_2m"]), unit))
        speed = float(current.get("wind_speed_10m", 0))
        speed = speed if speed_unit == "mph" else speed * (1.609344 if speed_unit == "kph" else .44704)
        speed_label = {"mph": "mph", "kph": "km/h", "ms": "m/s"}[speed_unit]
        humidity = round(float(current.get("relative_humidity_2m", 0)))
        self.wind.setText(f"{round(speed)} {speed_label}")
        self.humidity.setText(f"{humidity}%")
        self.compass_widget.set_degrees(current.get("wind_direction_10m", 0))
        hourly = data.get("hourly", {})
        start = self._current_hour_index(hourly.get("time", []), current.get("time", ""))
        hours = hourly.get("time", [])[start:start + 24]
        hourly_rain = hourly.get("precipitation_probability", [])
        rain = hourly_rain[start:start + 24]
        temperatures = hourly.get("temperature_2m", [])[start:start + 24]
        # Match the web app: use the previous hour, current hour, and next
        # five hours for the headline rain chance.  The chart still shows
        # the complete next 24 hours.
        near_term_rain = hourly_rain[max(0, start - 1):start + 6]
        rain_percentage = max([float(value or 0) for value in near_term_rain] or [0])
        self.rain_value.setText(f"{round(rain_percentage)}%")
        self.chart.set_data(hours, rain, temperatures, unit)
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        for index, widget in enumerate(self.days):
            if index >= len(dates):
                continue
            widget.day.setText(datetime.fromisoformat(dates[index]).strftime("%a").upper())
            widget.icon.setText(weather_icon(daily["weather_code"][index]))
            low = math.floor(convert_temperature(float(daily["temperature_2m_min"][index]), unit) + .5)
            high = math.floor(convert_temperature(float(daily["temperature_2m_max"][index]), unit) + .5)
            degree = "" if unit == "k" else "°"
            temperature_range = f"{low}{degree} / {high}{degree}{unit.upper()}"
            widget.temp.setText(temperature_range)
            widget.temp.setProperty("compact", unit == "k" or len(temperature_range) > 11)
            widget.temp.style().unpolish(widget.temp)
            widget.temp.style().polish(widget.temp)
        self._apply_background()
        self._update_location_buttons()
        tray_temp = format_temperature(current["temperature_2m"], unit)
        self._tray_temperature = tray_temp[:8]
        self._update_tray_icon()
        if self.settings.value("launcher", True, type=bool):
            self._update_launcher(round(convert_temperature(current["temperature_2m"], unit)))
        self.weather_error_panel.hide()
        self._set_weather_content_visible(True)
        self._maybe_notify(round(rain_percentage), int(current.get("weather_code", 0)), location["name"])

    @staticmethod
    def _current_hour_index(hours, current_time):
        target = str(current_time)[:13] + ":00"
        exact = next((i for i, hour in enumerate(hours) if str(hour) == target), None)
        if exact is not None:
            return exact
        return next((i for i, hour in enumerate(hours) if str(hour) >= target), 0)

    @staticmethod
    def compass(degrees):
        names = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        return names[round(float(degrees or 0) / 45) % 8]

    def navigate(self, offset):
        if self.locations:
            self.location_index = (self.location_index + offset) % len(self.locations)
            self._save_locations()
            self.weather = None
            self.refresh()

    def remove_location(self):
        if not self.locations:
            return
        self.locations.pop(self.location_index)
        self.location_index = min(self.location_index, max(0, len(self.locations) - 1))
        self._save_locations()
        self.weather = None
        self.refresh()

    def _save_locations(self):
        self.settings.setValue("locations", json.dumps(self.locations))
        self.settings.setValue("location_index", self.location_index)
        self._update_location_buttons()

    def _update_location_buttons(self):
        multiple = len(self.locations) > 1
        self.previous_button.setVisible(multiple)
        self.next_button.setVisible(multiple)
        self.remove_button.setVisible(multiple)
        self.settings_previous_button.setVisible(multiple)
        self.settings_remove_button.setVisible(multiple)
        self.settings_next_button.setVisible(multiple)

    def open_map(self):
        if self.locations:
            location = self.locations[self.location_index]
            QDesktopServices.openUrl(QUrl(f"https://www.openstreetmap.org/?mlat={location['lat']}&mlon={location['lon']}#map=10/{location['lat']}/{location['lon']}"))

    def show_error(self, message):
        QMessageBox.warning(self, "Typhoon", message)

    def show_credits(self):
        self.stack.setCurrentWidget(self.credits_page)

    def change_opacity(self, value):
        opacity = value / 100
        self.settings.setValue("opacity", opacity)
        self.card_proxy.setOpacity(opacity)

    def reset_settings(self):
        self.settings.clear()
        self.locations = []
        self.location_index = 0
        self.weather = None
        self._save_locations()
        self.resize(300, 500)
        self.position_toggle.setChecked(False)
        self.stack.setCurrentWidget(self.first_location_page)
        self._apply_preferences()

    def _initialize_tray(self):
        self.tray = None
        self.tray_menu = None
        self.tray_visibility_action = None
        self._tray_enabled = False
        self._tray_temperature = None
        self._rendered_tray_temperature = None
        if IS_WINDOWS or self.settings.value("tray", False, type=bool):
            self._set_tray_enabled(True)

    def _setup_tray(self):
        if self.tray is not None:
            self.tray.show()
            self._tray_enabled = True
            return True
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                return False
            icon = self.windowIcon()
            if icon.isNull():
                icon = QApplication.style().standardIcon(
                    QStyle.StandardPixmap.SP_MessageBoxInformation
                )
            self.tray = QSystemTrayIcon(icon, self)
            self.tray.setToolTip("Typhoon")
            self.tray.activated.connect(self._tray_activated)
            self.tray_menu = QMenu(self)
            self.tray_visibility_action = self.tray_menu.addAction("Hide")
            self.tray_visibility_action.triggered.connect(self._toggle_window_visibility)
            self.tray_menu.aboutToShow.connect(self._update_tray_visibility_action)
            self.tray_menu.addAction("Quit").triggered.connect(self._quit_from_tray)
            self.tray.setContextMenu(self.tray_menu)
            self.tray.show()
            if not self.tray.isVisible():
                self.tray.deleteLater()
                self.tray = None
                self.tray_menu = None
                self.tray_visibility_action = None
                return False
            self._tray_enabled = True
            self._update_tray_icon(force=True)
            return True
        except Exception:
            self.tray = None
            self.tray_menu = None
            self.tray_visibility_action = None
            self._tray_enabled = False
            return False

    def _set_tray_checkbox(self, checked):
        self.settings.setValue("tray", checked)
        if hasattr(self, "tray_check"):
            blocked = self.tray_check.blockSignals(True)
            self.tray_check.setChecked(checked)
            self.tray_check.blockSignals(blocked)

    def _set_tray_enabled(self, enabled):
        if IS_WINDOWS:
            enabled = True
        if enabled:
            if self._setup_tray():
                if IS_WINDOWS:
                    self._set_tray_checkbox(True)
                return
            self._set_tray_checkbox(False)
            return
        if self.tray is not None:
            self.tray.hide()
        self._tray_enabled = False

    def _setup_launcher(self):
        self.launcher_service = None
        if UnityLauncherService is not None:
            try:
                self.launcher_service = UnityLauncherService()
            except Exception:
                pass

    def _update_tray_visibility(self):
        self._set_tray_enabled(self.settings.value("tray", False, type=bool))

    def _update_tray_icon(self, force=False):
        if self.tray is None or not self._tray_enabled:
            return
        if not force and self._tray_temperature == self._rendered_tray_temperature:
            return
        if not self._tray_temperature:
            self.tray.setIcon(self.windowIcon())
            self.tray.setToolTip("Typhoon")
            self._rendered_tray_temperature = self._tray_temperature
            return
        base = self.windowIcon()
        if base.isNull():
            base = QApplication.style().standardIcon(
                QStyle.StandardPixmap.SP_MessageBoxInformation
            )
        pixmap = base.pixmap(64, 64)
        if pixmap.isNull():
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setPen(Qt.GlobalColor.white)
        painter.setBrush(QColor(32, 32, 40, 225))
        painter.drawRoundedRect(QRectF(1, 27, 62, 36), 9, 9)
        font = QFont(self.ui_font)
        font.setBold(True)
        font.setPixelSize(23 if len(self._tray_temperature) <= 4 else 19)
        painter.setFont(font)
        painter.drawText(
            QRectF(1, 27, 62, 36), Qt.AlignmentFlag.AlignCenter,
            self._tray_temperature,
        )
        painter.end()
        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip(f"Typhoon: {self._tray_temperature}")
        self._rendered_tray_temperature = self._tray_temperature

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window_visibility()

    def _update_tray_visibility_action(self):
        if self.tray_visibility_action is not None:
            self.tray_visibility_action.setText(
                "Hide" if self.isVisible() and not self.isMinimized() else "Show"
            )

    def _toggle_window_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        elif self.isMinimized():
            self.showNormal()
        else:
            self.show()
        if self.isVisible():
            self.raise_()
            self.activateWindow()

    def _quit_from_tray(self):
        QApplication.instance().quit()

    def close_or_hide(self):
        if self.tray is not None and self._tray_enabled:
            self.hide()
        else:
            self.close()

    def _maybe_notify(self, rain, code, city):
        if not self.settings.value("notifications", True, type=bool):
            return
        message = None
        if 95 <= code <= 99:
            message = f"Thunderstorm warning for {city}."
        elif code in (71, 73, 75, 77, 85, 86):
            message = f"Snow expected in {city}."
        elif rain >= 35:
            message = f"Rain expected ({rain}% chance) in {city}."
        now = int(datetime.now().timestamp())
        last = int(self.settings.value("last_notification", 0))
        if message and now - last >= int(self.settings.value("refresh_ms", 1_200_000)) / 1000:
            if self.tray is not None and self._tray_enabled:
                self.tray.showMessage("Typhoon Weather Alert", message, QSystemTrayIcon.MessageIcon.Information, 5000)
            elif dbus is not None and not sys.platform.startswith("win"):
                try:
                    notifications = dbus.SessionBus().get_object(
                        "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
                    )
                    notifications.Notify(
                        "Typhoon", dbus.UInt32(0), APP_ID, "Typhoon Weather Alert",
                        message, dbus.Array([], signature="s"), {}, dbus.Int32(5000),
                        dbus_interface="org.freedesktop.Notifications",
                    )
                except Exception:
                    pass
            self.settings.setValue("last_notification", now)

    def _update_launcher(self, count):
        if not self.launcher_service or dbus is None:
            return
        try:
            self.launcher_service.Update(
                f"application://{APP_ID}.desktop",
                {"count": dbus.Int64(count), "count-visible": True},
            )
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.stack.currentWidget() is self.weather_page:
            self.drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_origin)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_origin = None
        super().mouseReleaseEvent(event)

    def disable_drag(self):
        self.drag_enabled = False

    def enable_drag(self):
        self.drag_enabled = True

    def _canvas_point_is_interactive(self, viewport_point):
        scene_point = self.canvas_view.mapToScene(viewport_point)
        if not self.card_proxy.contains(self.card_proxy.mapFromScene(scene_point)):
            return True
        card_point = self.card_proxy.mapFromScene(scene_point).toPoint()
        widget = self.card.childAt(card_point)
        interactive_types = (QAbstractButton, QAbstractSlider, QAbstractScrollArea, QLineEdit)
        while widget is not None and widget is not self.card:
            if isinstance(widget, CreditLinkLabel):
                return True
            if isinstance(widget, interactive_types):
                return True
            widget = widget.parentWidget()
        return False

    def _start_system_drag(self):
        handle = self.windowHandle()
        if handle and hasattr(handle, "startSystemMove"):
            try:
                return bool(handle.startSystemMove())
            except Exception:
                pass
        return False

    def eventFilter(self, watched, event):
        if watched is getattr(self, "canvas_view", None).viewport():
            event_type = event.type()
            if event_type == QEvent.Type.MouseButtonPress and event.button() in (
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.MiddleButton,
            ):
                if self._canvas_point_is_interactive(event.position().toPoint()):
                    self.disable_drag()
                    return False
                self.enable_drag()
                if self._start_system_drag():
                    return True
                self._canvas_dragging = True
                self.drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                watched.grabMouse()
                return True
            if event_type == QEvent.Type.MouseMove and self._canvas_dragging:
                self.move(event.globalPosition().toPoint() - self.drag_origin)
                return True
            if event_type == QEvent.Type.MouseButtonRelease:
                if self._canvas_dragging:
                    self._canvas_dragging = False
                    self.drag_origin = None
                    watched.releaseMouse()
                    self.enable_drag()
                    return True
                self.enable_drag()
        return super().eventFilter(watched, event)

    def _aspect_size_from_width(self, width):
        width = max(self.minimumWidth(), min(int(width), self.maximumWidth()))
        height = round(width / self.aspect_ratio)
        if height > self.maximumHeight():
            height = self.maximumHeight()
            width = round(height * self.aspect_ratio)
        if height < self.minimumHeight():
            height = self.minimumHeight()
            width = round(height * self.aspect_ratio)
        return width, height

    def _aspect_size_from_height(self, height):
        height = max(self.minimumHeight(), min(int(height), self.maximumHeight()))
        width = round(height * self.aspect_ratio)
        if width > self.maximumWidth():
            width = self.maximumWidth()
            height = round(width / self.aspect_ratio)
        if width < self.minimumWidth():
            width = self.minimumWidth()
            height = round(width / self.aspect_ratio)
        return width, height

    def _begin_resize(self, edge, global_position):
        self._resize_state = (edge, global_position, self.geometry())
        self.disable_drag()

    def _continue_resize(self, global_position):
        if self._resize_state is None:
            return
        edge, origin, initial = self._resize_state
        delta = global_position - origin

        if edge == "bottom":
            width, height = self._aspect_size_from_height(initial.height() + delta.y())
        elif edge == "bottom-right":
            # Project the pointer movement onto the fixed-ratio diagonal. This
            # uses both axes without switching between them mid-drag.
            height_delta = (self.aspect_ratio * delta.x() + delta.y()) / (
                self.aspect_ratio ** 2 + 1
            )
            width, height = self._aspect_size_from_height(initial.height() + height_delta)
        elif edge == "bottom-left":
            height_delta = (-self.aspect_ratio * delta.x() + delta.y()) / (
                self.aspect_ratio ** 2 + 1
            )
            width, height = self._aspect_size_from_height(initial.height() + height_delta)
        elif edge == "left":
            width, height = self._aspect_size_from_width(initial.width() - delta.x())
        else:
            width, height = self._aspect_size_from_width(initial.width() + delta.x())

        x = initial.x()
        if edge in ("left", "bottom-left"):
            x = initial.x() + initial.width() - width
        self.setGeometry(x, initial.y(), width, height)

    def _finish_resize(self):
        self._resize_state = None
        self.enable_drag()

    def _position_resize_handles(self):
        # Corners are deliberately larger than the edge strips so they remain
        # easy to catch at every scale.
        edge = 6
        corner = 14
        width = self.width()
        height = self.height()
        self.resize_handles["left"].setGeometry(0, 0, edge, max(0, height - corner))
        self.resize_handles["right"].setGeometry(width - edge, 0, edge, max(0, height - corner))
        self.resize_handles["bottom"].setGeometry(
            corner, height - edge, max(0, width - 2 * corner), edge
        )
        self.resize_handles["bottom-left"].setGeometry(0, height - corner, corner, corner)
        self.resize_handles["bottom-right"].setGeometry(
            width - corner, height - corner, corner, corner
        )
        for handle in self.resize_handles.values():
            handle.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "canvas_view"):
            scale = self.width() / 300
            self.canvas_view.resetTransform()
            self.canvas_view.scale(scale, scale)
        if hasattr(self, "resize_handles"):
            self._position_resize_handles()
        self.settings.setValue("window_size", self.size())

    def moveEvent(self, event):
        super().moveEvent(event)
        self.settings.setValue("window_position", self.pos())


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(APP_ID)
    app.setApplicationName("typhoon-native-python")
    app.setQuitOnLastWindowClosed(True)
    if hasattr(app, "setDesktopFileName") and not sys.platform.startswith("win"):
        app.setDesktopFileName(APP_ID)
    window = TyphoonWindow()
    window.show()
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(200)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
