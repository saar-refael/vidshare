import socket
import os
import threading

def play_video_popup(filename):
    videos_dir = os.path.join(os.path.dirname(__file__), "videos")
    path = os.path.join(videos_dir, filename)

    if not os.path.isfile(path):
        print("CLIENT: video not found locally")
        return

    # Opens with default Windows video player
    os.startfile(path)
    print(f"CLIENT: playing {filename}")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("127.0.0.1", 9999))

print("Connected to server.")
print("Commands:")
print("  register|username|password")
print("  login|username|password")
print("  whoami")
print("  logout")
print("  videos")
print("  watch|video.mp4")
print("  quit\n")

while True:
    msg = input("> ")
    client_socket.sendall(msg.encode() + b"\n")

    reply = client_socket.recv(1024).decode().strip()
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
        threading.Thread(
            target=play_video_popup,
            args=(parts[2],),
            daemon=True
        ).start()

    if reply.startswith("OK|BYE"):
        break

client_socket.close()
print("Disconnected.")
