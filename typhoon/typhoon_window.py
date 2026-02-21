#!/usr/bin/python3

import configparser
import glob
import logging
import os
import subprocess
import sys
import threading
from urllib.parse import unquote, urlparse

import dbus
import dbus.mainloop.glib
import dbus.service

QT_MAJOR = 6
try:
    from PyQt6.QtCore import QEvent, QPoint, Qt, QUrl
    from PyQt6.QtGui import QDesktopServices, QIcon, QImage, QPainter
    from PyQt6.QtWebEngineCore import (
        QWebEnginePage,
        QWebEngineProfile,
        QWebEngineSettings,
    )
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWidgets import QApplication, QWidget
except ImportError:
    QT_MAJOR = 5
    from PyQt5.QtCore import QEvent, QPoint, Qt, QUrl
    from PyQt5.QtGui import QDesktopServices, QIcon, QImage, QPainter
    from PyQt5.QtWebEngineWidgets import (
        QWebEnginePage,
        QWebEngineProfile,
        QWebEngineSettings,
        QWebEngineView,
    )
    from PyQt5.QtWidgets import QApplication, QWidget

try:
    import cairosvg
except ImportError:
    cairosvg = None

try:
    import gi

    gi.require_version("Xdp", "1.0")
    from gi.repository import Xdp
    try:
        from gi.repository import Unity
    except Exception:
        Unity = None
except Exception:
    Xdp = None
    Unity = None


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

if QT_MAJOR == 6:
    QT_NAV_LINK_CLICKED = QWebEnginePage.NavigationType.NavigationTypeLinkClicked
    QT_CURSOR_BDIAG = Qt.CursorShape.SizeBDiagCursor
    QT_CURSOR_FDIAG = Qt.CursorShape.SizeFDiagCursor
    QT_MOUSE_LEFT = Qt.MouseButton.LeftButton
    QT_MOUSE_MIDDLE = Qt.MouseButton.MiddleButton
    QT_MOUSE_RIGHT = Qt.MouseButton.RightButton
    QT_WINDOW_FLAGS = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
    QT_NO_CONTEXT_MENU = Qt.ContextMenuPolicy.NoContextMenu
    QT_ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    QT_COLOR_WHITE = Qt.GlobalColor.white
    QT_EVENT_MOUSE_PRESS = QEvent.Type.MouseButtonPress
    QT_EVENT_MOUSE_MOVE = QEvent.Type.MouseMove
    QT_EVENT_MOUSE_RELEASE = QEvent.Type.MouseButtonRelease
    QT_EVENT_WINDOW_STATE_CHANGE = QEvent.Type.WindowStateChange
    QT_ATTR_LOCAL_STORAGE = QWebEngineSettings.WebAttribute.LocalStorageEnabled
    QT_ATTR_LOCAL_TO_REMOTE = QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls
    QT_ATTR_LOCAL_TO_FILE = QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls
    QT_COOKIE_FORCE_PERSIST = QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    QT_ASPECT_IGNORE = Qt.AspectRatioMode.IgnoreAspectRatio
    QT_SMOOTH_TRANSFORM = Qt.TransformationMode.SmoothTransformation
    QT_TEXT_ANTIALIAS = QPainter.RenderHint.TextAntialiasing
    QT_WA_TRANSLUCENT_BG = Qt.WidgetAttribute.WA_TranslucentBackground
    QT_COLOR_TRANSPARENT = Qt.GlobalColor.transparent
else:
    QT_NAV_LINK_CLICKED = QWebEnginePage.NavigationTypeLinkClicked
    QT_CURSOR_BDIAG = Qt.SizeBDiagCursor
    QT_CURSOR_FDIAG = Qt.SizeFDiagCursor
    QT_MOUSE_LEFT = Qt.LeftButton
    QT_MOUSE_MIDDLE = Qt.MiddleButton
    QT_MOUSE_RIGHT = Qt.RightButton
    QT_WINDOW_FLAGS = Qt.Window | Qt.FramelessWindowHint
    QT_NO_CONTEXT_MENU = Qt.NoContextMenu
    QT_ALIGN_CENTER = Qt.AlignCenter
    QT_COLOR_WHITE = Qt.white
    QT_EVENT_MOUSE_PRESS = QEvent.MouseButtonPress
    QT_EVENT_MOUSE_MOVE = QEvent.MouseMove
    QT_EVENT_MOUSE_RELEASE = QEvent.MouseButtonRelease
    QT_EVENT_WINDOW_STATE_CHANGE = QEvent.WindowStateChange
    QT_ATTR_LOCAL_STORAGE = QWebEngineSettings.LocalStorageEnabled
    QT_ATTR_LOCAL_TO_REMOTE = QWebEngineSettings.LocalContentCanAccessRemoteUrls
    QT_ATTR_LOCAL_TO_FILE = QWebEngineSettings.LocalContentCanAccessFileUrls
    QT_COOKIE_FORCE_PERSIST = QWebEngineProfile.ForcePersistentCookies
    QT_ASPECT_IGNORE = Qt.IgnoreAspectRatio
    QT_SMOOTH_TRANSFORM = Qt.SmoothTransformation
    QT_TEXT_ANTIALIAS = QPainter.TextAntialiasing
    QT_WA_TRANSLUCENT_BG = Qt.WA_TranslucentBackground
    QT_COLOR_TRANSPARENT = Qt.transparent


def event_global_point(event):
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


class TyphoonWebPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if (
            nav_type == QT_NAV_LINK_CLICKED
            and url.scheme() != "file"
        ):
            logger.info("Opening link externally: %s", url.toString())
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class Service(dbus.service.Object):
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName(
            "io.github.archisman_panigrahi.typhoon", dbus.SessionBus()
        )
        super().__init__(bus_name, "/io/github/archisman_panigrahi/typhoon")

    @dbus.service.signal(
        dbus_interface="com.canonical.Unity.LauncherEntry", signature="sa{sv}"
    )
    def Update(self, app_uri, properties):
        logger.info("Launcher update %s %s", app_uri, properties)


class ResizeHandle(QWidget):
    def __init__(self, parent, side="right"):
        super().__init__(parent)
        self.side = side
        self._resizing = False
        self._start_global = QPoint()
        self._start_width = 0
        self._start_right = 0
        self._start_y = 0
        self.setFixedSize(18, 18)
        if self.side == "left":
            self.setCursor(QT_CURSOR_BDIAG)
            self.setToolTip("Resize from left")
        else:
            self.setCursor(QT_CURSOR_FDIAG)
            self.setToolTip("Resize from right")

    def mousePressEvent(self, event):
        if event.button() == QT_MOUSE_LEFT:
            self._resizing = True
            self._start_global = event_global_point(event)
            self._start_width = self.parent().width()
            self._start_right = self.parent().x() + self.parent().width()
            self._start_y = self.parent().y()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event_global_point(event) - self._start_global
            if self.side == "left":
                new_width = self._start_width - delta.x()
            else:
                new_width = self._start_width + delta.x()
            target_w, target_h = self.parent()._aspect_size_from_width(new_width)
            if self.side == "left":
                new_x = self._start_right - target_w
                self.parent().setGeometry(new_x, self._start_y, target_w, target_h)
            else:
                self.parent().resize(target_w, target_h)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QT_MOUSE_LEFT:
            self._resizing = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QT_TEXT_ANTIALIAS)
        painter.setPen(QT_COLOR_WHITE)
        if self.side == "right":
            # Draw a small corner line so the handle looks like a classic resize grip.
            painter.drawLine(self.width() - 2, self.height() - 2, self.width() - 2, self.height() - 8)
            painter.drawLine(self.width() - 2, self.height() - 2, self.width() - 8, self.height() - 2)
            painter.drawText(self.rect(), QT_ALIGN_CENTER, "↘")
        painter.end()
        super().paintEvent(event)


class TyphoonWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.aspect_ratio = 3 / 5
        self.drag_enabled = True
        self._resizing_guard = False
        self._drag_start = QPoint()
        self._dragging = False
        self._prefer_per_pixel_alpha = self._is_wayland_platform()

        self._initialize_window()
        self._setup_webview()
        self._setup_dbus_launcher()
        self._restore_size_and_position()
        self._set_size_constraints()
        QApplication.instance().installEventFilter(self)

    def _clamp(self, value, min_value, max_value):
        return max(min_value, min(value, max_value))

    def _aspect_size_from_width(self, width):
        min_w, max_w = self.minimumWidth(), self.maximumWidth()
        min_h, max_h = self.minimumHeight(), self.maximumHeight()

        width = self._clamp(width, min_w, max_w)
        height = int(round(width / self.aspect_ratio))
        height = self._clamp(height, min_h, max_h)
        width = int(round(height * self.aspect_ratio))
        width = self._clamp(width, min_w, max_w)
        height = int(round(width / self.aspect_ratio))
        return width, height

    def _aspect_size_from_height(self, height):
        min_w, max_w = self.minimumWidth(), self.maximumWidth()
        min_h, max_h = self.minimumHeight(), self.maximumHeight()

        height = self._clamp(height, min_h, max_h)
        width = int(round(height * self.aspect_ratio))
        width = self._clamp(width, min_w, max_w)
        height = int(round(width / self.aspect_ratio))
        height = self._clamp(height, min_h, max_h)
        width = int(round(height * self.aspect_ratio))
        return width, height

    def _initialize_window(self):
        self.setWindowTitle("Typhoon")
        self.setWindowFlags(QT_WINDOW_FLAGS)
        self.setAttribute(QT_WA_TRANSLUCENT_BG, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)
        self._set_window_icon()

        self.grip_right = ResizeHandle(self, side="right")
        self.grip_left = ResizeHandle(self, side="left")
        self.grip_right.show()
        self.grip_left.show()

    def _set_window_icon(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "io.github.archisman_panigrahi.typhoon.svg",
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _setup_webview(self):
        self.webview = QWebEngineView(self)
        self.webview.setAttribute(QT_WA_TRANSLUCENT_BG, True)
        self.webview.setStyleSheet("background: transparent;")
        profile_root = os.path.join(self._get_config_dir(), "qtwebengine")
        os.makedirs(profile_root, exist_ok=True)
        self.web_profile = QWebEngineProfile("typhoon", self)
        self.web_profile.setPersistentStoragePath(
            os.path.join(profile_root, "storage")
        )
        self.web_profile.setCachePath(os.path.join(profile_root, "cache"))
        self.web_profile.setPersistentCookiesPolicy(
            QT_COOKIE_FORCE_PERSIST
        )

        self.webview.setPage(TyphoonWebPage(self.web_profile, self.webview))
        self.webview.page().setBackgroundColor(QT_COLOR_TRANSPARENT)
        self.webview.setContextMenuPolicy(QT_NO_CONTEXT_MENU)
        self.webview.installEventFilter(self)

        settings = self.webview.settings()
        settings.setAttribute(QT_ATTR_LOCAL_STORAGE, True)
        settings.setAttribute(QT_ATTR_LOCAL_TO_REMOTE, True)
        settings.setAttribute(QT_ATTR_LOCAL_TO_FILE, True)
        self.webview.page().profile().setHttpUserAgent(
            "Typhoon Weather App (https://github.com/archisman-panigrahi/typhoon)"
        )

        self.webview.titleChanged.connect(self._handle_title_change)
        self.webview.loadFinished.connect(self._on_load_finished)

        html_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "typhoon.html"
        )
        self.webview.setUrl(QUrl.fromLocalFile(html_path))

    def _setup_dbus_launcher(self):
        self.launcher = None
        self.launcher_service = None
        if Unity is not None:
            try:
                self.launcher = Unity.LauncherEntry.get_for_desktop_id(
                    "io.github.archisman_panigrahi.typhoon.desktop"
                )
                self.launcher.set_property("count_visible", False)
            except Exception as e:
                logger.warning("Could not initialize Unity launcher entry: %s", e)

        try:
            self.launcher_service = Service()
        except Exception as e:
            logger.warning("Could not initialize launcher D-Bus service: %s", e)
            return
        self.launcher_service.Update(
            "application://io.github.archisman_panigrahi.typhoon.desktop", {}
        )

    def _restore_size_and_position(self):
        last_width, last_height = self._get_last_window_size()
        self.resize(last_width, last_height)
        last_position = self._get_last_window_position()
        if last_position:
            self.move(last_position[0], last_position[1])
        else:
            self._center_window()

    def _center_window(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geometry = screen.availableGeometry()
        x = geometry.x() + (geometry.width() - self.width()) // 2
        y = geometry.y() + (geometry.height() - self.height()) // 2
        self.move(x, y)

    def _set_size_constraints(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.setMinimumSize(210, 350)
            return
        screen_height = screen.availableGeometry().height()
        self.setMinimumSize(210, 350)
        self.setMaximumSize(int(screen_height * 0.9 * 3 / 5), int(screen_height * 0.9))

    def _on_load_finished(self, ok):
        if not ok:
            logger.error("Failed to load local UI")
            return

        try:
            wallpaper_path = self.get_wallpaper_path()
            dominant_color = self._extract_dominant_color(wallpaper_path)
            if dominant_color and dominant_color.startswith("#"):
                logger.info("Extracted hex color from wallpaper: %s", dominant_color)
                self.send_message_to_webview(f"'{dominant_color[1:]}'")
                return
            raise ValueError("Invalid color format from wallpaper method")
        except Exception as e:
            logger.info("Error determining color from wallpaper: %s", e)

        try:
            output = subprocess.check_output(["xprop", "-root"], text=True)
            line = next(
                (
                    ln
                    for ln in output.splitlines()
                    if "_GNOME_BACKGROUND_REPRESENTATIVE_COLORS" in ln
                ),
                None,
            )
            if not line:
                raise RuntimeError("No representative colors found in xprop output")

            rgb_string = line.split('"')[1].strip()
            rgb_values = rgb_string[4:-1].split(",")
            rgb = tuple(map(int, rgb_values))
            hex_color = "{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])
            logger.info("Extracted hex color from xprop: #%s", hex_color)
            self.send_message_to_webview(f"'{hex_color}'")
        except Exception as e:
            logger.info("Falling back to accent color: %s", e)
            self._get_accent_color()

    def _extract_dominant_color(self, wallpaper_path):
        image = QImage()
        if wallpaper_path.lower().endswith(".svg"):
            if not cairosvg:
                return None
            png_bytes = cairosvg.svg2png(
                url=wallpaper_path, output_width=16, output_height=16
            )
            image.loadFromData(png_bytes, "PNG")
        else:
            image = QImage(wallpaper_path)

        if image.isNull():
            return None

        tiny = image.scaled(
            1,
            1,
            QT_ASPECT_IGNORE,
            QT_SMOOTH_TRANSFORM,
        )
        if tiny.isNull():
            return None
        color = tiny.pixelColor(0, 0)
        return "#{:02x}{:02x}{:02x}".format(color.red(), color.green(), color.blue())

    def _get_accent_color(self):
        logger.info("Getting system accent color")
        hex_color = "575591"
        used_source = None

        if Xdp is not None:
            try:
                portal = Xdp.Portal()
                settings = portal.get_settings()
                accent_color = settings.read_value(
                    "org.freedesktop.appearance", "accent-color"
                )
                if accent_color is not None:
                    r, g, b = accent_color
                    hex_color = "{:02x}{:02x}{:02x}".format(
                        int(float(r) * 255),
                        int(float(g) * 255),
                        int(float(b) * 255),
                    )
                    used_source = "libportal"
            except Exception as e:
                logger.warning("libportal accent lookup failed: %s", e)

        if used_source is None:
            try:
                bus = dbus.SessionBus()
                obj = bus.get_object(
                    "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
                )
                iface = dbus.Interface(obj, "org.freedesktop.portal.Settings")
                accent_color = iface.Read(
                    "org.freedesktop.appearance", "accent-color"
                )
                if accent_color is not None and len(accent_color) == 3:
                    r, g, b = accent_color
                    hex_color = "{:02x}{:02x}{:02x}".format(
                        int(float(r) * 255),
                        int(float(g) * 255),
                        int(float(b) * 255),
                    )
                    used_source = "portal-dbus"
            except Exception as e:
                logger.warning("Portal D-Bus accent lookup failed: %s", e)

        if used_source:
            logger.info("Accent color found via %s: '#%s'", used_source, hex_color)
        else:
            logger.warning("Accent color not found, using default '#%s'", hex_color)

        self.send_message_to_webview(f"'{hex_color}'")

    def send_message_to_webview(self, message):
        js_code = f"receiveMessage({message});"
        self.webview.page().runJavaScript(js_code)

    def _send_dbus_notification(self, message):
        try:
            bus = dbus.SessionBus()
            notify_obj = bus.get_object(
                "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
            )
            notify_interface = dbus.Interface(
                notify_obj, "org.freedesktop.Notifications"
            )
            hints = {"desktop-entry": dbus.String("io.github.archisman_panigrahi.typhoon")}
            notify_interface.Notify(
                "Weather Alert",
                0,
                "io.github.archisman_panigrahi.typhoon",
                message,
                "Take care and stay safe.",
                dbus.Array([], signature="s"),
                hints,
                -1,
            )
        except Exception as e:
            logger.error("Failed to send D-Bus notification: %s", e)

    def _handle_title_change(self, title):
        if not title:
            return

        logger.info("%s", title)

        if title.startswith("notify:"):
            message = title[len("notify:"):] or "Weather alert"
            threading.Thread(
                target=self._send_dbus_notification, args=(message,), daemon=True
            ).start()
            return

        if title.startswith("height="):
            try:
                height = int(title.split("=")[1])
                width = int(0.6 * height)
                self.resize(width, height)
            except ValueError:
                logger.warning("Invalid height value in title: %s", title)
            return

        if title == "close":
            self._toggle_unity_launcher("disable_launcher")
            self.close()
        elif title == "minimize":
            self.showMinimized()
        elif title == "disabledrag":
            self.drag_enabled = False
        elif title == "enabledrag":
            self.drag_enabled = True
        elif title.startswith("o"):
            self._set_opacity_from_title(title)
        elif title == "reset":
            self._toggle_unity_launcher("disable_launcher")
            self.resize(300, 500)
        elif title in ["enable_launcher", "disable_launcher"]:
            self._toggle_unity_launcher(title)
        elif title.lstrip("-").isdigit():
            self._update_unity_count(title)

    def _set_opacity_from_title(self, title):
        try:
            opacity = self._clamp(float(title[1:]), 0.1, 1.0)
            if self._prefer_per_pixel_alpha:
                self._set_webview_alpha(opacity)
            else:
                self.setWindowOpacity(opacity)
        except ValueError:
            pass

    def _set_webview_alpha(self, opacity):
        js_code = (
            "(function(){"
            f"var o={opacity:.3f};"
            "if (window.setWindowAlpha) {"
            "window.setWindowAlpha(o);"
            "} else {"
            "document.documentElement.style.setProperty('--window-alpha', o);"
            "}"
            "})();"
        )
        self.webview.page().runJavaScript(js_code)

    def _toggle_unity_launcher(self, title):
        visible = title == "enable_launcher"
        if self.launcher is not None:
            try:
                self.launcher.set_property("count_visible", visible)
            except Exception as e:
                logger.warning("Failed to toggle Unity launcher visibility: %s", e)

        if not self.launcher_service:
            return
        try:
            self.launcher_service.Update(
                "application://io.github.archisman_panigrahi.typhoon.desktop",
                {"count-visible": visible},
            )
        except Exception as e:
            logger.warning("Failed to toggle launcher visibility: %s", e)

    def _update_unity_count(self, title):
        if self.launcher is not None:
            try:
                self.launcher.set_property("count", int(title))
            except Exception as e:
                logger.warning("Failed to update Unity launcher count: %s", e)

        if not self.launcher_service:
            return
        try:
            count = int(title)
            self.launcher_service.Update(
                "application://io.github.archisman_panigrahi.typhoon.desktop",
                {"count": dbus.Int64(count)},
            )
        except ValueError:
            pass
        except Exception as e:
            logger.warning("Failed to update launcher count: %s", e)

    def _get_config_dir(self):
        config_dir = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        app_config_dir = os.path.join(config_dir, "io.github.archisman_panigrahi.typhoon")
        os.makedirs(app_config_dir, exist_ok=True)
        return app_config_dir

    def _get_last_window_size(self):
        config_file = os.path.join(self._get_config_dir(), "typhoon_size_qt.conf")
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                size = file.read().strip().split("x")
                width, height = int(size[0]), int(size[1])
                return width, height
        except (FileNotFoundError, ValueError):
            return 300, 500

    def _save_window_size(self, width, height):
        config_file = os.path.join(self._get_config_dir(), "typhoon_size_qt.conf")
        with open(config_file, "w", encoding="utf-8") as file:
            file.write(f"{width}x{height}")

    def _get_last_window_position(self):
        config_file = os.path.join(self._get_config_dir(), "typhoon_position_qt.conf")
        try:
            with open(config_file, "r", encoding="utf-8") as file:
                position = file.read().strip().split(",")
                x, y = int(position[0]), int(position[1])
                return x, y
        except (FileNotFoundError, ValueError):
            return None

    def _save_window_position(self):
        config_file = os.path.join(self._get_config_dir(), "typhoon_position_qt.conf")
        with open(config_file, "w", encoding="utf-8") as file:
            file.write(f"{self.x()},{self.y()}")

    def _get_primary_monitor(self):
        try:
            xrandr_output = subprocess.check_output(
                "xrandr --current | grep -w connected", shell=True, text=True
            )
            primary_monitor = None
            for line in xrandr_output.splitlines():
                if "primary" in line:
                    primary_monitor = line.split()[0]
                    break
            if not primary_monitor and xrandr_output.splitlines():
                primary_monitor = xrandr_output.splitlines()[0].split()[0]
            return primary_monitor
        except Exception:
            return None

    def get_wallpaper_path(self):
        if os.environ.get("FLATPAK_ID") is not None or os.environ.get("SNAP") is not None:
            raise RuntimeError("Flatpak or Snap detected, use xprop/accent fallback.")

        de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        wallpaper = None

        if "gnome" in de:
            command = "gsettings get org.gnome.desktop.background picture-uri"
            wallpaper = (
                subprocess.check_output(command, shell=True)
                .decode()
                .strip()
                .strip("'")
                .split("file://")[-1]
            )
        elif "cinnamon" in de:
            command = "gsettings get org.cinnamon.desktop.background picture-uri"
            wallpaper = (
                subprocess.check_output(command, shell=True)
                .decode()
                .strip()
                .strip("'")
                .split("file://")[-1]
            )
        elif "mate" in de:
            command = "gsettings get org.mate.background picture-filename"
            wallpaper = (
                subprocess.check_output(command, shell=True)
                .decode()
                .strip()
                .strip("'")
                .split("file://")[-1]
            )
        elif "xfce" in de:
            primary_monitor = self._get_primary_monitor()
            if not primary_monitor:
                raise RuntimeError("Could not detect primary monitor for XFCE")
            key = f"/backdrop/screen0/monitor{primary_monitor}/workspace0/last-image"
            wallpaper = subprocess.check_output(
                f'xfconf-query -c xfce4-desktop -p "{key}"', shell=True, text=True
            ).strip()
        elif "kde" in de:
            config_file = os.path.expanduser(
                "~/.config/plasma-org.kde.plasma.desktop-appletsrc"
            )
            with open(config_file, "r", encoding="utf-8") as file:
                for line in file:
                    if line.strip().startswith("Image="):
                        wallpaper = line.strip().split("=", 1)[1]
                        if wallpaper.endswith("/"):
                            images_dir = os.path.join(wallpaper, "contents", "images")
                            for candidate in os.listdir(images_dir):
                                if candidate.lower().endswith((".jpg", ".png")):
                                    wallpaper = os.path.join(images_dir, candidate)
                                    break
                        break
        elif "lxde" in de or "labwc:wlroots" in de:
            config_pattern = os.path.expanduser(
                "~/.config/pcmanfm/*/desktop-items-*.conf"
            )
            config_files = glob.glob(config_pattern)
            primary_monitor = self._get_primary_monitor()
            if primary_monitor:
                config_files.sort(key=lambda path: 0 if primary_monitor in path else 1)
            for config_file in config_files:
                try:
                    config = configparser.ConfigParser()
                    config.read(config_file)
                    if config.has_option("*", "wallpaper"):
                        wallpaper = config.get("*", "wallpaper")
                        break
                except Exception:
                    continue
            if not wallpaper:
                raise RuntimeError("Could not find wallpaper in PCManFM config")
        else:
            raise RuntimeError(f"Unsupported desktop environment: {de}")

        parsed = urlparse(wallpaper)
        if parsed.scheme == "file":
            wallpaper = unquote(parsed.path)
        logger.info("Wallpaper path: %s", wallpaper)
        return wallpaper

    def _start_window_drag(self):
        window = self.windowHandle()
        if window and hasattr(window, "startSystemMove"):
            try:
                if window.startSystemMove():
                    return True
            except Exception:
                pass
        return False

    def _is_wayland_platform(self):
        app = QApplication.instance()
        if app:
            platform_name = (app.platformName() or "").lower()
            if "wayland" in platform_name:
                return True
            if "xcb" in platform_name:
                return False
        if os.environ.get("WAYLAND_DISPLAY"):
            return True
        return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"

    def _event_from_webview(self, obj):
        if obj is self.webview:
            return True
        if not isinstance(obj, QWidget):
            return False
        return self.webview.isAncestorOf(obj)

    def eventFilter(self, obj, event):
        if self._event_from_webview(obj):
            if event.type() == QT_EVENT_MOUSE_PRESS:
                if event.button() == QT_MOUSE_RIGHT:
                    return True
                if self.drag_enabled and event.button() in (
                    QT_MOUSE_LEFT,
                    QT_MOUSE_MIDDLE,
                ):
                    if self._start_window_drag():
                        return True
                    self._dragging = True
                    self._drag_start = (
                        event_global_point(event) - self.frameGeometry().topLeft()
                    )
                    return True
            elif event.type() == QT_EVENT_MOUSE_MOVE and self._dragging:
                self.move(event_global_point(event) - self._drag_start)
                return True
            elif event.type() == QT_EVENT_MOUSE_RELEASE:
                self._dragging = False
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        if not self._resizing_guard and not self.isMaximized():
            new_size = event.size()
            old_size = event.oldSize()

            use_width_driver = True
            if old_size.isValid():
                delta_w = abs(new_size.width() - old_size.width())
                delta_h = abs(new_size.height() - old_size.height())
                use_width_driver = delta_w >= delta_h

            if use_width_driver:
                target_w, target_h = self._aspect_size_from_width(new_size.width())
            else:
                target_w, target_h = self._aspect_size_from_height(new_size.height())

            if target_w != new_size.width() or target_h != new_size.height():
                self._resizing_guard = True
                self.resize(target_w, target_h)
                self._resizing_guard = False
                return

        super().resizeEvent(event)
        self.webview.setGeometry(0, 0, self.width(), self.height())
        self.grip_right.move(
            self.width() - self.grip_right.width(), self.height() - self.grip_right.height()
        )
        self.grip_left.move(0, self.height() - self.grip_left.height())
        self.grip_right.raise_()
        self.grip_left.raise_()

        self._save_window_size(self.width(), self.height())

    def moveEvent(self, event):
        super().moveEvent(event)
        self._save_window_position()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QT_EVENT_WINDOW_STATE_CHANGE and self.isMaximized():
            self.showNormal()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Typhoon")
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName("io.github.archisman_panigrahi.typhoon")
    window = TyphoonWindow()
    window.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
