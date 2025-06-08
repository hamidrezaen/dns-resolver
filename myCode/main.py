import socket
import selectors

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

# create /etc/myhosts
path = "/etc/myhosts"
try:
    with open(path, mode='x') as myhosts:
        for line in ipv4s:
            myhosts.write(line + '\n')
except FileExistsError:
    print(f"File already exists: {path}")
except PermissionError:
    print(f"Permission denied: You need to run this script as root to write to {path}")

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
    query = {}

    queryid, flags, qdcount, ancount, nscount, arcount = s

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
        events = sel.select(timeout=None)
        for key, mask in events:
            if mask & selectors.EVENT_READ:
                sock = key.fileobj
                message, addr = sock.recvfrom(1024)
                