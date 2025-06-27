import socket
import selectors
import struct

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


# Read IPv4s from /etc/myhosts
ipv4s = []
path = "/etc/myhosts"
with open(path) as myhosts:
    for line in myhosts:
        line = line.strip()
        if not line.startswith('#') and line:
            parts = line.split()
            if len(parts) > 1 and parts[0].count('.') == 3:
                ipv4s.append(line)            


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

    # start parsing after 12-bytes header
    offset = 12

    for _ in range(quescount):
        domain_name, offset = decode_domain_name(message, offset)
        qtype, qclass = struct.unpack(">HH", message[offset:offset+4])
        offset += 4
        print(f"Query for: {domain_name}, Type: {qtype}, Class: {qclass}")

    return{
        "id" : dns_id,
        "flags" : flags,
        "questions" : quescount,
        "answers" : anscount,
        "domain": domain_name,
        "qtype" : qtype,
        "qclass" : qclass
    }


def decode_domain_name(message, offset):
    labels = []
    while True:
        length = message[offset]
        if length == 0:
            offset += 1
            break
        labels.append(message[offset+1:offset+length+1].decode())
        offset += length+1
    return '.'.join(labels), offset

# for now we just want to answer type A queries
def create_typeA_answer(message):
    
# create the myhosts file to read from
create_myhosts()

# listening on port 5353
sel = selectors.DefaultSelector()

host = "127.0.0.1"
port = 5335
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((host, port))
print(f"Listening on {(host, port)}")
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, data=None)

try:
    while True:
        # wait for events
        events = sel.select(timeout=None)
        for key, mask in events:
            sock = key.fileobj
            if mask & selectors.EVENT_READ:
                data, addr = sock.recvfrom(512)
                print(f"Recieved DNS query from {addr}")
                parsed = parse_message(data)
                print(parsed)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()