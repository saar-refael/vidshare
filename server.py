import socket

HOST = "0.0.0.0"
PORT = 5000

users = {"saar":"zb"}

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(1)

print("Server listening on", HOST, PORT)

client, addr = server.accept()
print("Connected:", addr)

buffer = ""


logged_in = False
current_user = None

while True:
    data = client.recv(1024)
    if not data:
        print("Client disconnected")
        break

    buffer += data.decode()

    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        line = line.strip()
        if line == "":
            continue

        cmd = line.lower()


        if cmd == "quit":
            client.sendall("BYE\n".encode())
            client.close()
            server.close()
            raise SystemExit


        if cmd == "whoami":
            if logged_in:
                client.sendall(f"YOU ARE|{current_user}\n".encode())
            else:
                client.sendall("YOU ARE|NONE\n".encode())
            continue


        if cmd == "logout":
            logged_in = False
            current_user = None
            client.sendall("OK|LOGGED_OUT\n".encode())
            continue


        parts = line.split("|")
        if len(parts) != 3:
            client.sendall("ERROR|BAD_FORMAT\n".encode())
            continue

        action, username, password = parts[0], parts[1], parts[2]


        if logged_in and action in ("login", "register"):
            client.sendall("FAIL|ALREADY_LOGGED_IN\n".encode())
            continue

        if action == "register":
            if username in users:
                client.sendall("FAIL|USER_EXISTS\n".encode())
            else:
                users[username] = password
                logged_in = True
                current_user = username
                client.sendall("OK|REGISTERED_AND_LOGGED_IN\n".encode())

        elif action == "login":
            if username not in users:
                client.sendall("FAIL|NO_SUCH_USER\n".encode())
            elif users[username] != password:
                client.sendall("FAIL|WRONG_PASSWORD\n".encode())
            else:
                logged_in = True
                current_user = username
                client.sendall("OK|LOGGED_IN\n".encode())

        else:
            client.sendall("ERROR|UNKNOWN_ACTION\n".encode())
