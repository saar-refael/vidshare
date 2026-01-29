import socket
import os

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("127.0.0.1", 9999))
server_socket.listen(5)

users = {}          # username -> password
logged_in = {}      # socket -> username

print("Server running on 127.0.0.1:9999...")

def list_videos(max_count=5):
    videos_dir = os.path.join(os.path.dirname(__file__), "videos")
    if not os.path.isdir(videos_dir):
        return []

    files = [
        f for f in os.listdir(videos_dir)
        if os.path.isfile(os.path.join(videos_dir, f))
    ]
    files.sort()
    return files[:max_count]

def video_exists(filename):
    videos_dir = os.path.join(os.path.dirname(__file__), "videos")
    path = os.path.abspath(os.path.join(videos_dir, filename))
    if not path.startswith(os.path.abspath(videos_dir)):
        return False
    return os.path.isfile(path)

while True:
    client, addr = server_socket.accept()
    print("New client:", addr)

    while True:
        data = client.recv(1024)
        if not data:
            if client in logged_in:
                del logged_in[client]
            client.close()
            break

        line = data.decode().strip()
        if not line:
            continue

        # quit
        if line == "quit":
            client.sendall(b"OK|BYE\n")
            client.close()
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
            vids = list_videos(5)
            if not vids:
                client.sendall(b"OK|VIDEOS|EMPTY\n")
            else:
                client.sendall(f"OK|VIDEOS|{','.join(vids)}\n".encode())
            continue

        # watch|filename
        parts = line.split("|")
        if len(parts) == 2 and parts[0] == "watch":
            filename = parts[1]
            if video_exists(filename):
                client.sendall(f"OK|WATCH|{filename}\n".encode())
            else:
                client.sendall(b"FAIL|NO_SUCH_VIDEO\n")
            continue

        # register / login
        if len(parts) != 3:
            client.sendall(b"FAIL|BAD_FORMAT\n")
            continue

        command, username, password = parts

        if command == "register":
            if username in users:
                client.sendall(b"FAIL|USER_EXISTS\n")
            else:
                users[username] = password
                client.sendall(b"OK|REGISTERED\n")

        elif command == "login":
            if username in users and users[username] == password:
                logged_in[client] = username
                client.sendall(b"OK|LOGGED_IN\n")
            else:
                client.sendall(b"FAIL|INVALID\n")

        else:
            client.sendall(b"FAIL|UNKNOWN_COMMAND\n")
