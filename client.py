import socket

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((SERVER_IP, SERVER_PORT))

print("Connected.")
print("Commands:")
print("  register|user|pass")
print("  login|user|pass")
print("  whoami")
print("  logout")
print("  quit\n")

while True:
    cmd = input("> ").strip()
    s.sendall((cmd + "\n").encode())

    reply = ""
    while "\n" not in reply:
        chunk = s.recv(1024)
        if not chunk:
            print("Server disconnected")
            s.close()
            raise SystemExit
        reply += chunk.decode()

    reply_line = reply.split("\n", 1)[0].strip()
    print("SERVER:", reply_line)

    if reply_line == "BYE":
        s.close()
        break
