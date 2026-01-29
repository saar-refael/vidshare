import socket
import os
import threading

def play_video_popup(filename: str):
    """
    Plays videos/<filename> on the *client machine* using python-vlc.
    Runs in a background thread so the chat stays responsive.
    """
    try:
        import vlc
    except ImportError:
        print("CLIENT: python-vlc not installed. Run: pip install python-vlc")
        return

    videos_dir = os.path.join(os.path.dirname(__file__), "videos")
    path = os.path.join(videos_dir, filename)

    if not os.path.isfile(path):
        print(f"CLIENT: video not found locally: {path}")
        print("CLIENT: Put the video file in the client's ./videos folder too.")
        return

    player = vlc.MediaPlayer(path)
    player.play()
    print(f"CLIENT: playing '{filename}' (close the VLC window or stop playback to end)")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('127.0.0.1', 9999))

print("Connected to server.")
print("Commands:")
print("  register|username|password")
print("  login|username|password")
print("  whoami")
print("  logout")
print("  watch|video.mp4   (plays video in a popup window)")
print("  quit\n")

while True:
    msg = input("> ")
    client_socket.sendall(msg.encode() + b"\n")

    reply = client_socket.recv(1024).decode()
    reply_line = reply.split("\n", 1)[0].strip()

    if not reply_line:
        continue

    print("SERVER:", reply_line)

    parts = reply_line.split("|")

    # NEW: handle server telling us to watch
    if len(parts) >= 3 and parts[0] == "OK" and parts[1] == "WATCH":
        filename = parts[2]
        threading.Thread(target=play_video_popup, args=(filename,), daemon=True).start()

    if reply_line.startswith("OK|BYE"):
        break

client_socket.close()
print("Disconnected.")
