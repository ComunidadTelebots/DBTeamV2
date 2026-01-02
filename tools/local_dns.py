#!/usr/bin/env python3
"""
Simple local DNS server for development that maps *.torrents.local to 127.0.0.1

Requires: pip install dnslib

Run as administrator/root because binding UDP port 53 requires elevated privileges on many systems.

Usage:
  python tools/local_dns.py --domain torrents.local --address 127.0.0.1

This is intended for local development only.
"""
import argparse
import socket
import threading
from dnslib import DNSRecord, QTYPE, RR, A


def serve(domain, address, port=53):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    print(f"local DNS listening on 0.0.0.0:{port} mapping *.{domain} -> {address}")
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            try:
                req = DNSRecord.parse(data)
                qname = str(req.q.qname)
                qtype = QTYPE[req.q.qtype]
                # strip trailing dot
                if qname.endswith('.'):
                    qname = qname[:-1]

                if qname.endswith('.' + domain) or qname == domain:
                    reply = req.reply()
                    reply.add_answer(RR(rname=req.q.qname, rtype=QTYPE.A, rclass=1, ttl=60, rdata=A(address)))
                    sock.sendto(reply.pack(), addr)
                else:
                    # respond NXDOMAIN
                    reply = req.reply()
                    reply.header.rcode = 3
                    sock.sendto(reply.pack(), addr)
            except Exception as e:
                # ignore malformed requests
                print('dns-err', e)
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', default='torrents.local', help='Local domain to map (default torrents.local)')
    parser.add_argument('--address', default='127.0.0.1', help='IP address to resolve to (default 127.0.0.1)')
    parser.add_argument('--port', type=int, default=53, help='UDP port to bind (default 53)')
    args = parser.parse_args()
    try:
        serve(args.domain, args.address, args.port)
    except PermissionError:
        print('Permission denied: binding to port. Try running as administrator/root or use a non-privileged port and a DNS forwarder.')


if __name__ == '__main__':
    main()
