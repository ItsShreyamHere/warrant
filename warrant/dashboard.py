"""`warrant dashboard`: a live local page of the session. Refreshes every 3 s.

Binds to 127.0.0.1 only: the record can hold unpublished results.
"""
import http.server
import threading
import webbrowser

from . import report


def serve(rec, port: int = 8765, open_browser: bool = True) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = report.html(rec, live=True).encode("utf-8") if self.path in ("/", "/index.html") else b""
            self.send_response(200 if body else 404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # keep the terminal quiet
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"warrant dashboard: {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
