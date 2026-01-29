import socket
import os

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('127.0.0.1', 9999))
server_socket.listen(5)

users = {}          # username -> password
logged_in = {}      # socket -> username

print("Server running on 127.0.0.1:9999...")

def safe_video_path(filename: str) -> str | None:
    """
    Returns absolute path to videos/filename if it exists and is safe.
    Prevents path traversal like ../../secret
    """
    base_dir = os.path.dirname(__file__)
    videos_dir = os.path.join(base_dir, "videos")

    # normalize
    requested = os.path.join(videos_dir, filename)
    videos_dir_abs = os.path.abspath(videos_dir)
    requested_abs = os.path.abspath(requested)

    if not requested_abs.startswith(videos_dir_abs + os.sep) and requested_abs != videos_dir_abs:
        return None

    if not os.path.isfile(requested_abs):
        return None

    return requested_abs

while True:
    client, addr = server_socket.accept()
    print("New client:", addr)

    while True:
        data = client.recv(1024)
        if not data:
            # disconnected
            if client in logged_in:
                print("Disconnected user:", logged_in[client])
                del logged_in[client]
            client.close()
            break

        line = data.decode().strip()
        if not line:
            continue

        # Special commands first (not in the 3-part command format)
        if line == "quit":
            if client in logged_in:
                print("User quit:", logged_in[client])
                del logged_in[client]
            client.sendall("OK|BYE\n".encode())
            client.close()
            break

        if line == "whoami":
            if client in logged_in:
                client.sendall(f"OK|YOUARE|{logged_in[client]}\n".encode())
            else:
                client.sendall("FAIL|NOT_LOGGED_IN\n".encode())
            continue

        if line == "logout":
            if client in logged_in:
                del logged_in[client]
                client.sendall("OK|LOGGED_OUT\n".encode())
            else:
                client.sendall("FAIL|NOT_LOGGED_IN\n".encode())
            continue

        # NEW: watch|filename (no login required)
        parts_watch = line.split("|")
        if len(parts_watch) == 2 and parts_watch[0].lower() == "watch":
            filename = parts_watch[1].strip()
            if not filename:
                client.sendall("FAIL|NO_FILENAME\n".encode())
                continue

            path = safe_video_path(filename)
            if path is None:
                client.sendall("FAIL|NO_SUCH_VIDEO\n".encode())
            else:
                client.sendall(f"OK|WATCH|{filename}\n".encode())
            continue

        # Standard format: command|username|password
        parts = line.split("|")
        if len(parts) != 3:
            client.sendall("FAIL|BAD_FORMAT\n".encode())
            continue

        command, username, password = parts

        if command == "register":
            if username in users:
                client.sendall("FAIL|USER_EXISTS\n".encode())
            else:
                users[username] = password
                client.sendall("OK|REGISTERED\n".encode())

        elif command == "login":
            if username in users and users[username] == password:
                logged_in[client] = username
                client.sendall("OK|LOGGED_IN\n".encode())
            else:
                client.sendall("FAIL|INVALID\n".encode())

        else:
            client.sendall("FAIL|UNKNOWN_COMMAND\n".encode())


#different types of users , role of video uploader , and how to actually approach a video , is it more about the creator of the video or general video list.