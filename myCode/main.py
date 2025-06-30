import socket
import selectors
import struct

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
                    return [int(octet) for octet in parts[0].split('.')]
                
        return None


# parsing recieved message
def parse_message(message):
    header = struct.unpack(">HHHHHH", message[:12])
    dns_id, flags, quescount, anscount, nscount, arcount = header

    print(f"ID : {dns_id}, Flags:{flags:016b}, Questions = {quescount}, Answers: {anscount}")

    # start parsing after 12-bytes header
    offset = 12

    for _ in range(quescount):
        start_i = offset
        decoded_domain_name, offset = decode_domain_name(message, offset)
        raw_domain_name = message[start_i:offset]
        qtype, qclass = struct.unpack(">HH", message[offset:offset+4])
        offset += 4

    print({
        "id" : dns_id,
        "flags" : flags,
        "questions" : quescount,
        "answers" : anscount,
        "domain": decoded_domain_name,
        "qtype" : qtype,
        "qclass" : qclass
    }, '\n'
    )
    return dns_id, flags, quescount, anscount, raw_domain_name, decoded_domain_name, qtype, qclass


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
def create_answer(dns_id, raw_domain_name, decoded_domain_name, qtype, qclass, quescount):
    ipv4_address = get_ipv4_address(decoded_domain_name)
    
    answer = struct.pack('!H', dns_id)

    is_type_class_valid = qclass==1 and qtype==1
    does_exist = ipv4_address is not None

    if not is_type_class_valid:
        # the falg should be 1(QR)000 0(OPCODE)1(AA)0(TC)0(RD) 0(RA)000(Zero) 0100(RCODE)
        answer += struct.pack('!HHHHH', 0x8404, quescount, 0, 0, 0)

    elif does_exist:
        # the falg should be 1(QR)000 0(OPCODE)1(AA)0(TC)0(RD) 0(RA)000(Zero) 0000(RCODE)
        # so it is 1000 0100 0000 0000 = 0x8400
        # then quescount=quscount, then anscount=1, nscount=0, arcount=0
        answer += struct.pack('!HHHHH', 0x8400, quescount, 1, 0, 0)

        answer += raw_domain_name
        # add type and class
        answer += struct.pack('!HH', qtype, qclass)
        # ???
        answer += b'\xc0\x0c'
        # add type and class to the answer
        answer += struct.pack('!HH', qtype, qclass)
        # add TTL and datalength
        answer += struct.pack('!LH', 0x0064, 4)

        answer += struct.pack('!BBBB', *(ipv4_address))

    else: # the domain name does not exist in the DNS
        # the falg should be 1(QR)000 0(OPCODE)1(AA)0(TC)0(RD) 0(RA)000(Zero) 0011(RCODE)
        answer += struct.pack('!HHHHH', 0x8403, quescount, 0, 0, 0)

    return answer

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
                message, addr = sock.recvfrom(512)
                print(f"Recieved DNS query from {addr}")
                dns_id, flags, quescount, anscount, raw_domain_name, decoded_domain_name, qtype, qclass = parse_message(message)
                response = create_answer(dns_id, raw_domain_name, decoded_domain_name, qtype, qclass, quescount)
                sock.sendto(response, addr)

except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()