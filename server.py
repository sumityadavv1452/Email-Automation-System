"""
Optional HTTP Web Control Dashboard Server for Email Automation System.
"""

import os
import json
import subprocess
import csv
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class EmailAutomationServer(BaseHTTPRequestHandler):
    """Custom HTTP Server serving control dashboard & REST API endpoints."""

    def _set_json_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _set_html_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            index_path = os.path.join(BASE_DIR, "web", "index.html")
            if os.path.exists(index_path):
                self._set_html_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "index.html not found")

        elif path.startswith("/preview/"):
            filename = os.path.basename(path)
            preview_path = os.path.join(BASE_DIR, "preview", filename)
            if os.path.exists(preview_path):
                self._set_html_headers()
                with open(preview_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Preview file not found")

        elif path == "/api/users":
            csv_path = os.path.join(BASE_DIR, "data", "users.csv")
            users = []
            if os.path.exists(csv_path):
                try:
                    with open(csv_path, mode="r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        users = list(reader)
                except Exception as e:
                    print(f"Error reading users.csv: {e}")
            self._set_json_headers()
            self.wfile.write(json.dumps(users).encode("utf-8"))

        elif path == "/api/logs":
            log_path = os.path.join(BASE_DIR, "logs", "email_log.csv")
            logs = []
            if os.path.exists(log_path):
                try:
                    with open(log_path, mode="r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        logs = list(reader)
                except Exception as e:
                    print(f"Error reading logs: {e}")
            self._set_json_headers()
            self.wfile.write(json.dumps(logs).encode("utf-8"))

        elif path == "/api/previews":
            preview_dir = os.path.join(BASE_DIR, "preview")
            files = []
            if os.path.exists(preview_dir):
                files = [f for f in os.listdir(preview_dir) if f.endswith(".html")]
            self._set_json_headers()
            self.wfile.write(json.dumps(sorted(files)).encode("utf-8"))

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/run-dry-run":
            res = subprocess.run(["python", "main.py", "--dry-run"], capture_output=True, text=True)
            self._set_json_headers()
            self.wfile.write(json.dumps({"success": res.returncode == 0, "output": res.stdout + res.stderr}).encode("utf-8"))

        elif path == "/api/run-test-send":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
            try:
                body = json.loads(post_body.decode('utf-8'))
                target_email = body.get("email", "").strip()
                if not target_email:
                    self._set_json_headers(400)
                    self.wfile.write(json.dumps({"success": False, "error": "Email required"}).encode("utf-8"))
                    return

                res = subprocess.run(["python", "main.py", "--test-send", target_email], capture_output=True, text=True)
                self._set_json_headers()
                self.wfile.write(json.dumps({
                    "success": res.returncode == 0,
                    "output": res.stdout + res.stderr,
                    "error": res.stderr if res.returncode != 0 else ""
                }).encode("utf-8"))
            except Exception as e:
                self._set_json_headers(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

        elif path == "/api/run-bulk-send":
            res = subprocess.run(["python", "main.py", "--now"], capture_output=True, text=True)
            self._set_json_headers()
            self.wfile.write(json.dumps({"success": res.returncode == 0, "output": res.stdout + res.stderr}).encode("utf-8"))

        else:
            self.send_error(404, "POST endpoint not found")

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, EmailAutomationServer)
    print(f"\n==================================================================")
    print(f"  Email Automation Control Dashboard running at:")
    print(f"  http://localhost:{PORT}")
    print(f"==================================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web dashboard server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
