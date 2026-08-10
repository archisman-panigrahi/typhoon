#!/usr/bin/python3
"""Native, low-memory Qt Widgets frontend for Typhoon."""

import json
import math
import os
import signal
import sys
from datetime import datetime
from urllib.parse import urlencode

from PyQt6.QtCore import QEvent, QPointF, QRectF, QSize, QSettings, Qt, QTimer, QUrl
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractScrollArea,
    QAbstractSlider,
    QApplication,
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
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSizeGrip,
    QStackedWidget,
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


APP_ID = "io.github.archisman_panigrahi.typhoon"
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
        if icon:
            self.setIcon(QIcon(resource(icon)))
            self.setIconSize(QSize(19, 19))
        self.setObjectName("toolButton")
        self.setFixedSize(30, 30)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)


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
        self.drag_origin = None
        self.drag_enabled = True
        self._canvas_dragging = False
        self._validated_locations = {}
        self._location_validation_timers = {}
        self.aspect_ratio = 3 / 5
        self._resizing_guard = False
        self.climacon_font = self._load_font("fonts/Climacons.ttf", "Sans Serif")
        self.ui_font = self._load_font("fonts/ubuntu.ttf", "Sans Serif")
        QApplication.instance().setFont(QFont(self.ui_font, 11))
        self._setup_window()
        self._build_ui()
        self._setup_tray()
        self._setup_launcher()
        self._apply_preferences()
        self._update_location_buttons()
        if not self.locations:
            self.stack.setCurrentWidget(self.first_location_page)
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
        self.setWindowIcon(QIcon(resource(f"{APP_ID}.svg")))
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
        self.stack = QStackedWidget()
        self.weather_page = self._build_weather_page()
        self.first_location_page = self._build_first_location_page()
        self.settings_page = self._build_settings_page()
        self.hourly_page = self._build_hourly_page()
        for page in (self.weather_page, self.first_location_page, self.settings_page, self.hourly_page):
            self.stack.addWidget(page)
        card_layout.addWidget(self.stack)
        self.size_grip = QSizeGrip(self)
        self.size_grip.setToolTip("Resize")
        self.size_grip.raise_()
        self.setFont(QFont(self.ui_font, 11))
        self.card.setStyleSheet(self._stylesheet("#575591"))

    def _location_entry_row(self, first_run=False):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        location_input = QLineEdit()
        location_input.setFixedSize(215, 29)
        location_input.setPlaceholderText("Location" if first_run else "Location: e.g. Boston, Kolkata, …")
        status = QPushButton("")
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
            close.clicked.connect(self.close_or_hide)
            minimize = ToolButton("−")
            minimize.clicked.connect(self.showMinimized)
            bar.addWidget(close)
            bar.addWidget(minimize)
        bar.addStretch()
        return bar

    def _build_weather_page(self):
        page = QWidget()
        page.setObjectName("weatherPage")
        top_widget = QWidget(page)
        top_widget.setGeometry(0, 0, 300, 30)
        top = self._top_bar()
        top_widget.setLayout(top)
        self.previous_button = ToolButton("‹")
        self.remove_button = ToolButton("×")
        self.next_button = ToolButton("›")
        self.previous_button.clicked.connect(lambda: self.navigate(-1))
        self.remove_button.clicked.connect(self.remove_location)
        self.next_button.clicked.connect(lambda: self.navigate(1))
        for button in (self.previous_button, self.remove_button, self.next_button):
            top.addWidget(button)
        top.addStretch()
        hourly = ToolButton(icon="clock-exclamation-svgrepo-com.svg")
        hourly.setToolTip("Next 24 hours")
        hourly.clicked.connect(lambda: self.stack.setCurrentWidget(self.hourly_page))
        settings = ToolButton(icon="settings.svg")
        settings.clicked.connect(lambda: self.stack.setCurrentWidget(self.settings_page))
        sync = ToolButton(icon="sync.svg")
        sync.clicked.connect(self.refresh)
        top.addWidget(hourly)
        top.addWidget(settings)
        top.addWidget(sync)
        self.city = QPushButton("ADD A LOCATION", page)
        self.city.setFlat(True)
        self.city.setCursor(Qt.CursorShape.PointingHandCursor)
        self.city.clicked.connect(self.open_map)
        self.city.setObjectName("city")
        self.city.setGeometry(0, 30, 300, 41)
        self.weather_icon = GlyphLabel("`", page)
        self.weather_icon.setObjectName("weatherIcon")
        initial_weather_font = QFont(self.climacon_font)
        initial_weather_font.setPixelSize(200)
        self.weather_icon.setFont(initial_weather_font)
        self.weather_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weather_icon.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.weather_icon.setGeometry(0, 71, 300, 241)
        details_widget = QWidget(page)
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
        self.temperature = QLabel("--°", temperature_widget)
        self.temperature.setObjectName("temperature")
        self.temperature.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Give the degree/unit glyphs overhang space on both sides while
        # retaining the CSS column's right edge.
        # Keep the text anchored at the same point while leaving extra widget
        # space for the final C/F/K glyph's right-side overhang.
        self.temperature.setGeometry(34, 0, 126, 64)
        self.wind = QLabel("-- km/h")
        self.wind.setObjectName("details")
        humidity_row = QHBoxLayout()
        humidity_row.setContentsMargins(0, 0, 0, 0)
        humidity_row.setSpacing(5)
        humidity_icon = QLabel()
        humidity_icon.setPixmap(QIcon(resource("humidity.svg")).pixmap(14, 19))
        humidity_icon.setFixedSize(15, 21)
        self.humidity = QLabel("--%")
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
        extra_widget = QWidget(page)
        extra_widget.setGeometry(0, 333, 300, 30)
        extra = QHBoxLayout(extra_widget)
        extra.setContentsMargins(20, 0, 59, 0)
        self.feels = QLabel("Feels Like: --°")
        self.feels.setObjectName("feelsLike")
        self.rain = QPushButton("☂  --%")
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
        self.rain_value = QLabel("--%")
        self.rain_value.setObjectName("rainValue")
        self.rain_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        rain_layout.addWidget(rain_icon)
        rain_layout.addWidget(self.rain_value)
        self.rain.clicked.connect(lambda: self.stack.setCurrentWidget(self.hourly_page))
        extra.addWidget(self.feels)
        extra.addStretch()
        extra.addWidget(self.rain)
        week_widget = QWidget(page)
        week_widget.setGeometry(0, 381, 300, 111)
        week = QHBoxLayout(week_widget)
        week.setContentsMargins(0, 0, 0, 0)
        week.setSpacing(0)
        self.days = [ForecastDay(self.climacon_font) for _ in range(4)]
        for day in self.days:
            week.addWidget(day)
        return page

    def _build_settings_page(self):
        page = QWidget()
        page.setObjectName("settingsPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        top = self._top_bar()
        previous = ToolButton("‹")
        self.settings_remove_button = ToolButton("×")
        next_location = ToolButton("›")
        previous.clicked.connect(lambda: self.navigate(-1))
        self.settings_remove_button.clicked.connect(self.remove_location)
        next_location.clicked.connect(lambda: self.navigate(1))
        top.addWidget(previous)
        top.addWidget(self.settings_remove_button)
        top.addWidget(next_location)
        close_settings = ToolButton(icon="settings.svg")
        close_settings.setToolTip("Close settings")
        close_settings.clicked.connect(lambda: self.stack.setCurrentWidget(self.weather_page))
        refresh = ToolButton(icon="sync.svg")
        refresh.clicked.connect(lambda: (self.stack.setCurrentWidget(self.weather_page), self.refresh()))
        top.addWidget(close_settings)
        top.addWidget(refresh)
        outer.addLayout(top)
        outer.addSpacing(29)
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("settingsContent")
        form = QVBoxLayout(content)
        form.setContentsMargins(25, 26, 25, 16)
        form.setSpacing(9)
        entry_row, self.location_input, self.location_status = self._location_entry_row()
        form.addLayout(entry_row)
        actions = QHBoxLayout()
        guess = QPushButton("Guess Location")
        guess.setFixedSize(102, 29)
        guess.clicked.connect(lambda: self.guess_location(self.location_input))
        report = QPushButton("Report Bugs")
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
        form.addSpacing(4)
        colors = QHBoxLayout()
        colors.setSpacing(1)
        gradient = QPushButton()
        gradient.setObjectName("gradientSwatch")
        gradient.setToolTip("Temperature-based color")
        gradient.setFixedSize(21, 21)
        gradient.clicked.connect(lambda: self.set_color("gradient"))
        chameleon = QPushButton()
        chameleon.setToolTip("Chameleonic color")
        chameleon.setIcon(QIcon(resource("chameleon-svgrepo-com.svg")))
        chameleon.setIconSize(QSize(17, 17))
        chameleon.setFixedSize(21, 21)
        chameleon.clicked.connect(lambda: self.set_color("chameleonic"))
        custom = QPushButton()
        custom.setToolTip("Pick a custom color")
        custom.setIcon(QIcon(resource("dropper-svgrepo-com.svg")))
        custom.setIconSize(QSize(17, 17))
        custom.setFixedSize(21, 21)
        custom.clicked.connect(self.pick_color)
        colors.addWidget(gradient)
        colors.addWidget(chameleon)
        colors.addWidget(custom)
        for index, color in enumerate(PALETTE):
            button = QPushButton()
            button.setToolTip(color)
            button.setFixedSize(17, 21)
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
        self.position_toggle = QCheckBox()
        self.position_toggle.setObjectName("positionToggle")
        self.position_toggle.setChecked(str(self.settings.value("controls_position", "left")) == "right")
        self.position_toggle.toggled.connect(lambda checked: self.preference_changed("controls_position", "right" if checked else "left"))
        tray_controls.addWidget(self.position_toggle)
        tray_controls.addWidget(QLabel("Right"))
        form.addLayout(tray_controls)
        form.addSpacing(7)
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity"))
        opacity_row.addSpacing(13)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setObjectName("opacitySlider")
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setFixedWidth(153)
        self.opacity_slider.setValue(round(float(self.settings.value("opacity", .8)) * 100))
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addStretch()
        form.addLayout(opacity_row)
        form.addSpacing(5)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        credits = QPushButton("CREDITS")
        credits.setFixedSize(71, 28)
        credits.clicked.connect(self.show_credits)
        homepage = QPushButton("HOMEPAGE")
        homepage.setFixedSize(86, 28)
        homepage.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://archisman-panigrahi.github.io/typhoon")))
        reset = QPushButton("RESET")
        reset.setFixedSize(62, 28)
        reset.clicked.connect(self.reset_settings)
        footer.addWidget(credits)
        footer.addWidget(homepage)
        footer.addWidget(reset)
        footer.addStretch()
        form.addLayout(footer)
        hint = QLabel("Add multiple locations by typing a new\nlocation in the searchbox above!")
        hint.setObjectName("settingsHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addWidget(hint)
        form.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
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
        return f"""
            #card {{ background: {color}; color: white; }}
            QWidget {{ color: white; }}
            QPushButton {{ border: 1px solid rgba(20,20,20,.65); background: rgba(30,30,30,.28); padding: 5px; }}
            QPushButton:hover, QPushButton:checked {{ background: rgba(255,255,255,.18); }}
            #toolButton {{ border: none; background: rgba(0,0,0,.045); padding: 0; font-size: 24px; font-weight: bold; }}
            #toolButton:hover {{ background: rgba(0,0,0,.18); }}
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
            #settingsContent QPushButton {{ padding: 1px 4px; font-size: 13px; }}
            #settingsContent QLineEdit {{ padding: 2px 9px; font-size: 13px; }}
            #settingsContent QLabel {{ font-size: 13px; }}
            #settingsContent QCheckBox {{ spacing: 6px; font-size: 14px; }}
            #settingsContent QCheckBox::indicator {{ width: 18px; height: 18px; }}
            #settingsContent #locationStatus {{ border: none; background: transparent; padding: 0; font-family: sans-serif; font-size: 22px; font-weight: bold; }}
            #gradientSwatch {{ background: qlineargradient(x1:0,y1:1,x2:0,y2:0, stop:0 #e44211, stop:.35 #f09609, stop:.7 #575591, stop:1 #1ba1e2); border:2px solid #292929; padding:0; }}
            #positionToggle {{ spacing: 0; }}
            #positionToggle::indicator {{ width: 39px; height: 21px; border-radius: 10px; border: 1px solid #292929; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 white, stop:.43 white, stop:.44 #333, stop:1 #333); }}
            #positionToggle::indicator:checked {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #333, stop:.56 #333, stop:.57 white, stop:1 white); }}
            #opacitySlider::groove:horizontal {{ height: 5px; border-radius: 2px; background: #777; }}
            #opacitySlider::sub-page:horizontal {{ background: #aaa; }}
            #opacitySlider::handle:horizontal {{ width: 26px; margin: -10px 0; border-radius: 13px; background: white; }}
            #settingsHint {{ font-size: 13px; }}
            #hourlyPage {{ background: #444; }}
            #city {{ border: none; background: transparent; font-size: 22px; letter-spacing: -1px; padding-top: 20px; }}
            #weatherIcon {{ background: transparent; }}
            #temperature {{ font-size: 65px; letter-spacing: -5px; padding-right: 12px; }}
            #details {{ font-size: 25px; letter-spacing: -2px; }}
            #feelsLike {{ font-size: 22px; }}
            #rainButton {{ border: none; background: transparent; font-size: 22px; padding: 2px 8px; }}
            #rainButton:hover {{ background: rgba(255,255,255,.14); border-radius: 4px; }}
            #rainValue {{ font-size: 22px; }}
            #forecastDay {{ font-size: 18px; }}
            #forecastTemp {{ font-size: 18px; }}
            #panelTitle {{ font-size: 22px; }}
            QCheckBox {{ spacing: 8px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
        """

    def _apply_preferences(self):
        self.card_proxy.setOpacity(float(self.settings.value("opacity", .8)))
        self._apply_background()
        self._update_tray_visibility()

    def preference_changed(self, key, value):
        self.settings.setValue(key, value)
        if key == "tray":
            self._update_tray_visibility()
        if self.weather and key in ("unit", "speed"):
            self.render_weather()

    def set_color(self, color):
        self.settings.setValue("color", color)
        self._apply_background()

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

    def _schedule_location_validation(self, location_input, status):
        self._validated_locations.pop(location_input, None)
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
        status.setText("|")
        status.setToolTip("Checking location…")
        url = "https://nominatim.openstreetmap.org/search?" + urlencode({"q": query, "format": "jsonv2", "limit": 1})

        def complete(data, error):
            if location_input.text().strip() != query:
                return
            if error or not data:
                self._validated_locations.pop(location_input, None)
                status.setText("×")
                status.setToolTip("Location not found")
                return
            item = data[0]
            location = {"name": item.get("name") or item.get("display_name", query).split(",")[0], "display_name": item.get("display_name", query), "lat": float(item["lat"]), "lon": float(item["lon"])}
            self._validated_locations[location_input] = (query, location)
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
            self.stack.setCurrentWidget(self.first_location_page)
            return
        location = self.locations[self.location_index]
        params = {
            "latitude": location["lat"], "longitude": location["lon"], "timezone": "auto",
            "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
            "current_weather": "true",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,wind_direction_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "forecast_days": 7,
        }
        self.city.setText("REFRESHING…")

        def complete(data, error):
            current = self._current_weather_from_web_response(data) if data else None
            if error or not current:
                self.show_error("Could not connect to the weather service.")
                self.city.setText(location["name"].upper())
                return
            data["current"] = current
            self.weather = data
            self.render_weather()

        self.network.get_json("https://api.open-meteo.com/v1/forecast?" + urlencode(params), complete)

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
            widget.temp.setText(f"{low}{degree} / {high}{degree}{unit.upper()}")
        self._apply_background()
        self._update_location_buttons()
        tray_temp = format_temperature(current["temperature_2m"], unit)
        if self.tray:
            self.tray.setToolTip(f"Typhoon: {tray_temp}")
        if self.settings.value("launcher", True, type=bool):
            self._update_launcher(round(convert_temperature(current["temperature_2m"], unit)))
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
        self.settings_remove_button.setVisible(multiple)

    def open_map(self):
        if self.locations:
            location = self.locations[self.location_index]
            QDesktopServices.openUrl(QUrl(f"https://www.openstreetmap.org/?mlat={location['lat']}&mlon={location['lon']}#map=10/{location['lat']}/{location['lon']}"))

    def show_error(self, message):
        QMessageBox.warning(self, "Typhoon", message)

    def show_credits(self):
        QMessageBox.information(
            self,
            "Typhoon",
            "Typhoon 1.9.0\n\nBased on Stormcloud 1.1 by Jono Cooper.\n"
            "Weather data by Open-Meteo; maps and geocoding by OpenStreetMap.\n\n"
            "Released under GPL-3.0.",
        )

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
        self.stack.setCurrentWidget(self.first_location_page)
        self._apply_preferences()

    def _setup_tray(self):
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.windowIcon(), self)
            self.tray.setToolTip("Typhoon")
            self.tray.activated.connect(self._tray_activated)
            self._update_tray_visibility()

    def _setup_launcher(self):
        self.launcher_service = None
        if UnityLauncherService is not None:
            try:
                self.launcher_service = UnityLauncherService()
            except Exception:
                pass

    def _update_tray_visibility(self):
        if getattr(self, "tray", None):
            self.tray.setVisible(self.settings.value("tray", False, type=bool))

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.setVisible(not self.isVisible())

    def close_or_hide(self):
        if self.tray and self.tray.isVisible():
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
            if self.tray:
                self.tray.show()
                self.tray.showMessage("Typhoon Weather Alert", message, QSystemTrayIcon.MessageIcon.Information, 5000)
                if not self.settings.value("tray", False, type=bool):
                    QTimer.singleShot(5500, lambda: self.tray.hide())
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

    def resizeEvent(self, event):
        if not self._resizing_guard:
            new_size = event.size()
            old_size = event.oldSize()
            use_width = True
            if old_size.isValid():
                width_change = abs(new_size.width() - old_size.width())
                height_change = abs(new_size.height() - old_size.height())
                use_width = width_change >= height_change
            target = (
                self._aspect_size_from_width(new_size.width())
                if use_width
                else self._aspect_size_from_height(new_size.height())
            )
            if target != (new_size.width(), new_size.height()):
                self._resizing_guard = True
                self.resize(*target)
                self._resizing_guard = False
        super().resizeEvent(event)
        if hasattr(self, "canvas_view"):
            scale = self.width() / 300
            self.canvas_view.resetTransform()
            self.canvas_view.scale(scale, scale)
        if hasattr(self, "size_grip"):
            extent = 18
            self.size_grip.setGeometry(self.width() - extent, self.height() - extent, extent, extent)
            self.size_grip.raise_()
        self.settings.setValue("window_size", event.size())

    def moveEvent(self, event):
        super().moveEvent(event)
        self.settings.setValue("window_position", self.pos())


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(APP_ID)
    app.setApplicationName("typhoon")
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
