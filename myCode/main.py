import socket
import selectors
import struct
import types


# create /etc/myhosts
def create_myhosts():
    path = "/etc/myhosts"
    try:
        with open(path, mode='x') as myhosts:
            for line in ipv4s:
                myhosts.write(line + '\n')
    except FileExistsError:
        print(f"File already exists: {path}")
    except PermissionError:
        print(f"Permission denied: You need to run this script as root to write to {path}")


# Read IPv4s from /etc/hosts
ipv4s = []
path = "/etc/hosts"
with open(path) as hosts:
    for line in hosts:
        line = line.strip()
        if not line.startswith('#') and line:
            parts = line.split()
            if len(parts) > 1 and parts[0].count('.') == 3:
                ipv4s.append(line)


# accept a new connection
def accept_wrapper(sock):

    # Because the listening socket was registered for the event selectors.EVENT_READ,
    # it should be ready to read
    conn, addr = sock.accept()  
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)

    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"") # !!!
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


# handle the events for existing connections
def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            parse_message(recv_data)
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"Echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


# find ipv4 address from /etc/myhosts
def get_ipv4_address(domain_name):
    with open('/etc/myhosts', 'r') as myhosts:
        for line in myhosts:
            line = line.strip()
            if not line.startswith('#') and line:
                parts = line.split()
                if parts[1] == domain_name:
                    return parts[0].split('.')
                
        return None

# parsing recieved message
def parse_message(message):
    header = struct.unpack(">HHHHHH", message[:12])
    dns_id, flags, quescount, anscount, nscount, arcount = header

    print(f"ID : {dns_id}, Flags:{flags:016b}, Questions = {quescount}, Answers: {anscount}")
    
    

# listening on port 5353
sel = selectors.DefaultSelector()

host = "127.0.0.1"
port = 5335
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((host, port))
print(f"Listening on {(host, port)}")
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, data=None)

print("listening for UDP on: " + host + ' ' + port)

try:
    while True:
        # wait for events
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None: # check if this is a new connection request.
                accept_wrapper(key.fileobj) # accept a new connection
            else:
                # handle the events for existing connections
                service_connection(key, mask)

except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()