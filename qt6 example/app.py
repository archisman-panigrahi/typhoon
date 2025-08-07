import os
import sys
from PyQt6.QtCore import Qt, QUrl, QPoint, QEvent, QObject, pyqtSlot
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
import subprocess
import time

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Draggable Window with HTML")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.95)


        # Start local HTTP server in background
        self.server_process = subprocess.Popen([
            sys.executable, "-m", "http.server", "8765"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        # Wait briefly to ensure server starts
        time.sleep(1)

        self.browser = QWebEngineView(self)
        self.browser.load(QUrl("http://localhost:8765/index.html"))
        self.setCentralWidget(self.browser)
        # QWebChannel setup
        self.channel = QWebChannel()
        self.drag_handler = DragHandler(self)
        self.channel.registerObject("dragHandler", self.drag_handler)
        self.browser.page().setWebChannel(self.channel)

        self.resize(800, 600)

        # Track drag state
        self._drag_active = False
        self._drag_pos = QPoint()

    def closeEvent(self, event):
        # Clean up the server process when closing the app
        if hasattr(self, "server_process"):
            self.server_process.terminate()
        super().closeEvent(event)

    # Remove eventFilter, use DragHandler instead


class DragHandler(QObject):
    @pyqtSlot(float)
    def setOpacity(self, value):
        # Clamp value between 0.3 and 1.0
        value = max(0.3, min(1.0, value))
        self.window.setWindowOpacity(value)
    @pyqtSlot()
    # def printAddress(self):
    #     import requests
    #     try:
    #         resp = requests.get("https://ipapi.co/json/")
    #         if resp.status_code == 200:
    #             data = resp.json()
    #             address = data.get("city", "") + ", " + data.get("region", "") + ", " + data.get("country_name", "")
    #             print("Address:", address)
    #         else:
    #             print("Failed to fetch address. Status:", resp.status_code)
    #     except Exception as e:
    #         print("Error fetching address:", e)
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._drag_active = False
        self._drag_offset = QPoint()

    @pyqtSlot()
    def closeWindow(self):
        self.window.close()

    @pyqtSlot()
    def goToGoogle(self):
        self.window.browser.load(QUrl("https://www.google.com"))

    @pyqtSlot(int, int)
    def startDrag(self, x, y):
        # x, y are global screen coordinates from JS
        self._drag_active = True
        self._drag_offset = QPoint(x, y) - self.window.frameGeometry().topLeft()

    @pyqtSlot(int, int)
    def dragMove(self, x, y):
        if self._drag_active:
            self.window.move(QPoint(x, y) - self._drag_offset)

    @pyqtSlot()
    def endDrag(self):
        self._drag_active = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
