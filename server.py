import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

HOST = "127.0.0.1"
TCP_PORT = 9999
HTTP_PORT = 8000

BASE_DIR = os.path.dirname(__file__)
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)


users = {}
logged_in = {}

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


def safe_video_path(filename: str) -> str | None:
    # r eturn absolute path inside videos , or None if path traversal attack.
    # prevent ".." tricks
    path = os.path.abspath(os.path.join(VIDEOS_DIR, filename))
    videos_abs = os.path.abspath(VIDEOS_DIR)
    if not path.startswith(videos_abs + os.sep) and path != videos_abs:
        return None
    return path


def list_videos(max_count=50):
    files = []
    for f in os.listdir(VIDEOS_DIR):
        p = os.path.join(VIDEOS_DIR, f)
        if os.path.isfile(p):
            files.append(f)
    files.sort()
    return files[:max_count]


class VideoHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        #  only /videos/filename
        path = unquote(self.path)
        if not path.startswith("/videos/"):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        filename = path[len("/videos/"):]
        if not filename:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing filename")
            return

        file_path = safe_video_path(filename)
        if not file_path or not os.path.isfile(file_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"No such video")
            return

        file_size = os.path.getsize(file_path)

        # Range support
        range_header = self.headers.get("Range")
        start, end = 0, file_size - 1

        if range_header:
            m = RANGE_RE.match(range_header.strip())
            if m:
                g1, g2 = m.groups()
                if g1:
                    start = int(g1)
                if g2:
                    end = int(g2)

                # suffix range: bytes=-500 , meaning last __ bytes
                if not g1 and g2:
                    length = int(g2)
                    start = max(file_size - length, 0)
                    end = file_size - 1

        if start > end or start >= file_size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.end_headers()
            return

        chunk_len = end - start + 1
        status = 206 if range_header else 200

        self.send_response(status)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(chunk_len))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()

        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_len
            bufsize = 1024 * 512
            while remaining > 0:
                data = f.read(min(bufsize, remaining))
                if not data:
                    break
                self.wfile.write(data)
                remaining -= len(data)

    def log_message(self, fmt, *args):
        #for future..
        return


def start_http_server():
    httpd = ThreadingHTTPServer((HOST, HTTP_PORT), VideoHTTPHandler)
    print(f"[HTTP] Serving videos at http://{HOST}:{HTTP_PORT}/videos/<filename>")
    httpd.serve_forever()


def recv_line(sock: socket.socket) -> str | None:
    #Read until new line
    buf = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None
        if chunk == b"\n":
            break
        buf += chunk
    return buf.decode(errors="replace").strip()


def recv_exact(sock: socket.socket, n: int) -> bytes | None:
    #here we recieve exact amount of data for accuracy.
    out = bytearray()
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            return None
        out += chunk
    return bytes(out)


def handle_client(client: socket.socket, addr):
    print("[TCP] New client:", addr)
    try:
        while True:
            line = recv_line(client)
            if line is None:
                break
            if not line:
                continue

            # quit
            if line == "quit":
                client.sendall(b"OK|BYE\n")
                break

            # whoami
            if line == "whoami":
                if client in logged_in:
                    client.sendall(f"OK|YOUARE|{logged_in[client]}\n".encode())
                else:
                    client.sendall(b"FAIL|NOT_LOGGED_IN\n")
                continue

            # logout
            if line == "logout":
                if client in logged_in:
                    del logged_in[client]
                    client.sendall(b"OK|LOGGED_OUT\n")
                else:
                    client.sendall(b"FAIL|NOT_LOGGED_IN\n")
                continue

            # list videos
            if line == "videos":
                vids = list_videos()
                if not vids:
                    client.sendall(b"OK|VIDEOS|EMPTY\n")
                else:
                    client.sendall(("OK|VIDEOS|" + ",".join(vids) + "\n").encode())
                continue

            parts = line.split("|")

            # watch|filename
            if len(parts) == 2 and parts[0] == "watch":
                filename = parts[1]
                p = safe_video_path(filename)
                if p and os.path.isfile(p):
                    url = f"http://{HOST}:{HTTP_PORT}/videos/{filename}"
                    client.sendall(f"OK|WATCH|{url}\n".encode())
                else:
                    client.sendall(b"FAIL|NO_SUCH_VIDEO\n")
                continue

            #here we upload filesz
            if len(parts) == 3 and parts[0] == "upload":
                if client not in logged_in:
                    client.sendall(b"FAIL|NOT_LOGGED_IN\n")
                    continue

                filename = parts[1]
                try:
                    size = int(parts[2])
                except ValueError:
                    client.sendall(b"FAIL|BAD_SIZE\n")
                    continue

                if size <= 0 or size > 2_000_000_000:
                    client.sendall(b"FAIL|BAD_SIZE\n")
                    continue

                file_path = safe_video_path(filename)
                if not file_path:
                    client.sendall(b"FAIL|BAD_FILENAME\n")
                    continue


                if not filename.lower().endswith(".mp4"):
                    client.sendall(b"FAIL|ONLY_MP4_ALLOWED\n")
                    continue


                client.sendall(b"OK|READY\n")

                data = recv_exact(client, size)
                if data is None:
                    break

                with open(file_path, "wb") as f:
                    f.write(data)

                client.sendall(b"OK|UPLOADED\n")
                continue

            # register / login
            if len(parts) == 3:
                command, username, password = parts

                if command == "register":
                    if username in users:
                        client.sendall(b"FAIL|USER_EXISTS\n")
                    else:
                        users[username] = password
                        client.sendall(b"OK|REGISTERED\n")
                    continue

                if command == "login":
                    if username in users and users[username] == password:
                        logged_in[client] = username
                        client.sendall(b"OK|LOGGED_IN\n")
                    else:
                        client.sendall(b"FAIL|INVALID\n")
                    continue

            client.sendall(b"FAIL|UNKNOWN_OR_BAD_FORMAT\n")

    finally:
        if client in logged_in:
            del logged_in[client]
        client.close()
        print("[TCP] Client disconnected:", addr)


def main():
    # start HTTP server in background
    threading.Thread(target=start_http_server, daemon=True).start()

    # TCP server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, TCP_PORT))
    server_socket.listen(20)

    print(f"[TCP] Server running on {HOST}:{TCP_PORT} ...")
    print(f"[DIR] Videos folder: {VIDEOS_DIR}")

    while True:
        client, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()


if __name__ == "__main__":
    main()
