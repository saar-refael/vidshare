import os
import socket
import webbrowser

HOST = "127.0.0.1"
PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

print("Connected to server.")
print("Commands:")
print("  register|username|password")
print("  login|username|password")
print("  whoami")
print("  logout")
print("  videos")
print("  upload|C:\\path\\to\\video.mp4    (or ./video.mp4)")
print("  watch|video.mp4")
print("  quit\n")

def send_line(s: str):
    client_socket.sendall(s.encode() + b"\n")

def recv_line() -> str:
    data = b""
    while not data.endswith(b"\n"):
        chunk = client_socket.recv(1)
        if not chunk:
            return ""
        data += chunk
    return data.decode(errors="replace").strip()

while True:
    msg = input("> ").strip()
    if not msg:
        continue


    if msg.startswith("upload|"):
        path = msg.split("|", 1)[1].strip().strip('"')
        if not os.path.isfile(path):
            print("CLIENT: file not found:", path)
            continue

        filename = os.path.basename(path)
        size = os.path.getsize(path)

        # tell server we want to upload
        send_line(f"upload|{filename}|{size}")

        # wait for OK|READY or failure
        reply = recv_line()
        print("SERVER:", reply)
        if reply != "OK|READY":
            continue

        # send raw bytes
        with open(path, "rb") as f:
            client_socket.sendall(f.read())

        # server confirms
        reply2 = recv_line()
        print("SERVER:", reply2)
        continue


    send_line(msg)
    reply = recv_line()
    print("SERVER:", reply)

    parts = reply.split("|")

    if len(parts) >= 3 and parts[0] == "OK" and parts[1] == "VIDEOS":
        if parts[2] == "EMPTY":
            print("CLIENT: no videos available")
        else:
            print("CLIENT: available videos:")
            for v in parts[2].split(","):
                print(" -", v)

    if len(parts) >= 3 and parts[0] == "OK" and parts[1] == "WATCH":
        url = parts[2]
        print("CLIENT: opening:", url)
        webbrowser.open(url)

    if reply.startswith("OK|BYE"):
        break

client_socket.close()
print("Disconnected.")
