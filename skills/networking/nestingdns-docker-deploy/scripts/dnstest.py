#!/usr/bin/env python
# Simple DNS query tool for custom ports (Windows nslookup is stuck on port 53).
# Usage: python dnstest.py [domain=www.baidu.com] [server=127.0.0.1] [port=4053] [tcp]
import socket, struct, sys


def query(name, server, port, tcp=False, timeout=6.0):
    q = b''
    for part in name.split('.'):
        q += bytes([len(part)]) + part.encode()
    q += b'\x00\x00\x01\x00\x01'
    msg = b'\xab\x11\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00' + q
    if tcp:
        s = socket.create_connection((server, port), timeout)
        s.sendall(struct.pack('>H', len(msg)) + msg)
        ln = struct.unpack('>H', s.recv(2))[0]
        data = b''
        while len(data) < ln:
            data += s.recv(ln - len(data))
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(msg, (server, port))
        data, _ = s.recvfrom(4096)
    s.close()
    rcode = data[3] & 15
    ancount = struct.unpack('>H', data[6:8])[0]
    off = 12
    while data[off] != 0:
        off += 1 + data[off]
    off += 5
    ips = []
    for _ in range(ancount):
        if data[off] & 0xC0 == 0xC0:
            off += 2
        else:
            while data[off] != 0:
                off += 1 + data[off]
            off += 1
        typ, cls, ttl, rdlen = struct.unpack('>HHIH', data[off:off + 10])
        off += 10
        if typ == 1 and rdlen == 4:
            ips.append('.'.join(map(str, data[off:off + 4])))
        off += rdlen
    return rcode, ancount, ips


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'www.baidu.com'
    server = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 4053
    tcp = len(sys.argv) > 4 and sys.argv[4].lower() in ('1', 'tcp', 'true')
    try:
        rcode, ancount, ips = query(name, server, port, tcp)
        print(f"{name} @{server}:{port} {'TCP' if tcp else 'UDP'} -> rcode={rcode} answers={ancount} A={ips}")
    except Exception as e:
        print(f"FAIL {name} @{server}:{port} -> {type(e).__name__}: {e}")
        sys.exit(1)
