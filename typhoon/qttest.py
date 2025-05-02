import sys
import threading
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
import os
import http.server
import socketserver

print("list of dependencies: sudo pacman -S python-pyqt6 python-pyqt6-webengine")

PORT = 8000

# Keep a reference to the server
httpd = None

def start_server():
    global httpd
    Handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), Handler)
    print(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()

# Start the HTTP server in a background thread
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# Give the server a moment to start
time.sleep(1)

app = QApplication(sys.argv)
view = QWebEngineView()
url = f"http://localhost:{PORT}/typhoon.html"
view.load(QUrl(url))
view.setWindowTitle("Typhoon HTML Viewer")
view.resize(300, 500)
view.show()

def stop_server():
    global httpd
    if httpd:
        print("Shutting down HTTP server...")
        httpd.shutdown()
        httpd.server_close()

app.aboutToQuit.connect(stop_server)

sys.exit(app.exec())