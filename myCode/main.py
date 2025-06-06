import socket
import selectors

sel = selectors.DefaultSelector()

host = ""
port = 5353
lsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {(host, port)}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

