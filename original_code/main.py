from socket import *
from _thread import *
import struct


# getting ipv4 address from /etc/myhosts by iterating line by line
def get_ipv4_address(domain_name):
    with open('/etc/myhosts', 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            else:
                line = line.split()
                if line[1] == domain_name:
                    return map(int, line[0].split('.'))

    return None


# parsing message and printing it
def parse_message(message):
    transaction_id = message[:2]

    message = message.split(b' ')[1]
    questions, answer_rrs, authority_rrs, additional_rrs = struct.unpack('!HHHH', message[:8])

    name_end_index = message.find(0, 9)
    name = message[8:name_end_index + 1]
    domain_name = get_domain_name(name)
    type_, class_ = struct.unpack('!HH', message[name_end_index + 1:name_end_index + 5])

    print({
        'transaction_id': transaction_id,
        'questions': questions,
        'answer_rrs': answer_rrs,
        'authority_rrs': authority_rrs,
        'additional_rrs': additional_rrs,
        'name': domain_name,
        'type': get_type(type_),
        'class': get_class(class_)
    })
    return transaction_id, questions, name, domain_name, type_, class_


# parse binary domain name to string
# we know that domain name is split by '.'
# first byte is length of the first part of domain name
# then there is the first part of domain name
# then there is the second byte which is length of the second part of domain name
# and so on
# if length is 0, it means that we reached the end of domain name
def get_domain_name(name):
    domain_name = ''

    while True:
        length = int(name[0:1].hex(), 16)
        if length == 0:
            break

        domain_name += name[1:length + 1].decode('utf-8') + '.'
        name = name[length + 1:]

    return domain_name[:-1]


# get string type from type number
def get_type(type_):
    if type_ == 1:
        return 'A'
    elif type_ == 2:
        return 'NS'
    elif type_ == 5:
        return 'CNAME'
    elif type_ == 6:
        return 'SOA'
    elif type_ == 12:
        return 'PTR'
    elif type_ == 15:
        return 'MX'
    elif type_ == 16:
        return 'TXT'
    elif type_ == 28:
        return 'AAAA'
    else:
        return f'unknown ({type_})'


# get string class from class number
def get_class(class_):
    if class_ == 1:
        return 'IN'
    elif class_ == 2:
        return 'CS'
    elif class_ == 3:
        return 'CH'
    elif class_ == 4:
        return 'HS'
    else:
        return f'unknown ({class_})'


# creating answer
# if domain name is valid and type is A and class is IN
# then we return answer with transaction id and flags
# else if domain name is not valid
# then we return answer with transaction id and flags with status NXDOMAIN
# else if type is not A or class is not IN
# then we return answer with transaction id and flags with status NOTIMP
def create_answer(transaction_id, questions, name, domain_name, type_, class_):
    ipv4_address = get_ipv4_address(domain_name)
    is_valid = ipv4_address is not None and type_ == 1 and class_ == 1

    # add transaction id
    answer = transaction_id

    # add flags
    if is_valid:
        answer += struct.pack('!HHHHH', 0x8180, questions, 1, 0, 0)
    elif ipv4_address is None:
        answer += struct.pack('!HHHHH', 0x0003, questions, 0, 0, 0)
    else:
        answer += struct.pack('!HHHHH', 0x0004, questions, 0, 0, 0)

    # add requested domain name
    answer += name
    # add type and class to question section
    answer += struct.pack('!HH', type_, class_)
    # add domain name
    answer += b'\xc0\x0c'
    # add type and class to answer section
    answer += struct.pack('!HH', type_, class_)
    # add time to live and data length
    answer += struct.pack('!LH', 0x0064, 4)

    # add ipv4 address
    if is_valid:
        answer += struct.pack('!BBBB', *ipv4_address)

    return answer


# thread function
# parse message and print it
# then create answer and print it
def threaded(socket: socket, message: str, address: tuple):
    transaction_id, questions, name, domain_name, type_, class_ = parse_message(message)
    answer = create_answer(transaction_id, questions, name, domain_name, type_, class_)

    print({
        'transaction_id': transaction_id,
        'address': address,
        'message': message,
        'answer': answer
    })
    socket.sendto(answer, address)


# creating socket and binding it to port 5354
host = ''
port = 5354
server_socket = socket(AF_INET, SOCK_DGRAM)
server_socket.bind((host, port))
print('socket binded to port', port)

while True:
    message, address = server_socket.recvfrom(1024)
    start_new_thread(threaded, (server_socket, message, address))
