import http.server
import http.client
import urllib.parse
import hashlib
import os
import json
import sys
import secrets
import http.cookies

CAMERA_IP = "172.27.34.173"
USERNAME = "root"
PASSWORD = "pass"
PORT = 8080

LOGIN_USER = "oscar"
LOGIN_PASS = "pass"

# Active session tokens
sessions = set()


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def make_digest_header(method, uri, www_auth):
    """Build a Digest Authorization header from a WWW-Authenticate challenge."""
    parts = {}
    for item in www_auth.replace("Digest ", "").split(","):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            parts[k.strip()] = v.strip().strip('"')

    realm = parts.get("realm", "")
    nonce = parts.get("nonce", "")
    qop = parts.get("qop", "")
    nc = "00000001"
    cnonce = hashlib.md5(os.urandom(8)).hexdigest()[:16]

    ha1 = md5(f"{USERNAME}:{realm}:{PASSWORD}")
    ha2 = md5(f"{method}:{uri}")

    if qop:
        response = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
        return (f'Digest username="{USERNAME}", realm="{realm}", nonce="{nonce}", '
                f'uri="{uri}", qop={qop}, nc={nc}, cnonce="{cnonce}", '
                f'response="{response}"')
    else:
        response = md5(f"{ha1}:{nonce}:{ha2}")
        return (f'Digest username="{USERNAME}", realm="{realm}", nonce="{nonce}", '
                f'uri="{uri}", response="{response}"')


def camera_request(method, path, body=None, content_type=None):
    """Make a request to the camera with Digest auth. Returns (status, headers, body_bytes)."""
    conn = http.client.HTTPConnection(CAMERA_IP, timeout=10)

    headers = {}
    if content_type:
        headers["Content-Type"] = content_type

    # First request — expect 401
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    resp_body = resp.read()

    if resp.status == 401:
        www_auth = resp.getheader("WWW-Authenticate", "")
        if "Digest" in www_auth:
            auth_header = make_digest_header(method, path, www_auth)
            headers["Authorization"] = auth_header

            conn2 = http.client.HTTPConnection(CAMERA_IP, timeout=10)
            conn2.request(method, path, body=body, headers=headers)
            resp = conn2.getresponse()
            return resp
    return resp


def camera_request_stream(method, path):
    """Make streaming request to camera, returns response object for chunked reading."""
    conn = http.client.HTTPConnection(CAMERA_IP, timeout=10)
    conn.request(method, path)
    resp = conn.getresponse()
    resp_body = resp.read()

    if resp.status == 401:
        www_auth = resp.getheader("WWW-Authenticate", "")
        if "Digest" in www_auth:
            auth_header = make_digest_header(method, path, www_auth)
            conn2 = http.client.HTTPConnection(CAMERA_IP, timeout=300)
            conn2.request(method, path, headers={"Authorization": auth_header})
            return conn2.getresponse()
    return None


class CameraProxyHandler(http.server.SimpleHTTPRequestHandler):

    def _get_session(self):
        """Return session token from cookie, or None."""
        cookie_header = self.headers.get("Cookie", "")
        c = http.cookies.SimpleCookie(cookie_header)
        if "session" in c:
            return c["session"].value
        return None

    def _is_authenticated(self):
        token = self._get_session()
        return token is not None and token in sessions

    def _require_auth(self):
        """Return True if request is allowed, False if redirected to login."""
        if self._is_authenticated():
            return True
        # Redirect to login page
        self.send_response(302)
        self.send_header("Location", "/login.html")
        self.end_headers()
        return False

    def do_GET(self):
        # Public paths: login page and login API
        if self.path == "/login.html" or self.path == "/favicon.ico":
            super().do_GET()
            return
        if self.path.startswith("/cam/"):
            if not self._require_auth():
                return
            self._proxy_get()
        elif self.path == "/logout":
            token = self._get_session()
            if token:
                sessions.discard(token)
            self.send_response(302)
            self.send_header("Location", "/login.html")
            self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0")
            self.end_headers()
        else:
            if not self._require_auth():
                return
            super().do_GET()

    def do_POST(self):
        if self.path == "/login":
            self._handle_login()
        elif self.path.startswith("/cam/"):
            if not self._is_authenticated():
                self.send_error(401, "Not authenticated")
                return
            self._proxy_post()
        else:
            self.send_error(405)

    def _handle_login(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}
        user = data.get("username", "")
        pw = data.get("password", "")
        if user == LOGIN_USER and pw == LOGIN_PASS:
            token = secrets.token_hex(32)
            sessions.add(token)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", f"session={token}; Path=/; HttpOnly; SameSite=Strict")
            resp = json.dumps({"ok": True}).encode()
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            resp = json.dumps({"ok": False, "error": "Fel användarnamn eller lösenord"}).encode()
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

    def _proxy_get(self):
        cam_path = self.path[4:]  # strip /cam

        # Check if this is a stream request
        if "/mjpg/" in cam_path:
            self._proxy_stream(cam_path)
            return

        try:
            resp = camera_request("GET", cam_path)
            data = resp.read()
            ct = resp.getheader("Content-Type", "text/plain")
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(502, f"Camera error: {e}")

    def _proxy_stream(self, cam_path):
        try:
            resp = camera_request_stream("GET", cam_path)
            if not resp:
                self.send_error(502, "Could not authenticate for stream")
                return
            ct = resp.getheader("Content-Type", "multipart/x-mixed-replace")
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            pass  # stream ended

    def _proxy_post(self):
        cam_path = self.path[4:]
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None
        ct = self.headers.get("Content-Type", "application/json")

        try:
            resp = camera_request("POST", cam_path, body=body, content_type=ct)
            data = resp.read()
            resp_ct = resp.getheader("Content-Type", "application/json")
            self.send_response(200)
            self.send_header("Content-Type", resp_ct)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(502, f"Camera error: {e}")

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except Exception:
            pass  # never let a single request kill the server

    def log_message(self, format, *args):
        msg = format % args
        if "/axis-cgi/mjpg" not in msg:  # don't spam stream logs
            print(f"  {self.address_string()} - {msg}")


class ResilientServer(http.server.ThreadingHTTPServer):
    daemon_threads = True  # threads die when main thread exits

    def handle_error(self, request, client_address):
        # Suppress per-connection errors so the server stays up
        print(f"  [warn] Error from {client_address}, continuing...")


def main():
    server = ResilientServer(("0.0.0.0", PORT), CameraProxyHandler)
    print(f"\n  Axis Camera Dashboard")
    print(f"  http://localhost:{PORT}/index.html")
    print(f"  Camera proxy: /cam/* -> {CAMERA_IP}")
    print(f"  Press Ctrl+C to stop\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
