#!/usr/bin/env python3
"""Minimal RCON client for the M1 verification runtime (stdlib only).

Sends commands to a local Minecraft dedicated server over the RCON protocol
(Source RCON: int32-LE length prefix, request id, type 3=login / 2=command,
null-terminated payload). Used by the M1 harness workflow to drive the pinned
server empirically (e.g. runtime-generating structure `.nbt` files) instead of
guessing mechanics. It fabricates nothing: every effect happens inside the
running pinned runtime.

Usage:
  python rcon.py --password <pw> [--host 127.0.0.1] [--port 25575] "cmd1" "cmd2" ...

Prints each command followed by the server's response. Exit codes: 0 = all
commands sent, 1 = authentication failed, 2 = usage/connection errors.
"""

import argparse
import socket
import struct
import sys

__version__ = "0.1.0"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

TYPE_LOGIN = 3
TYPE_COMMAND = 2


def send_packet(sock, request_id, packet_type, payload):
    body = struct.pack("<ii", request_id, packet_type) + payload.encode("utf-8") + b"\x00\x00"
    sock.sendall(struct.pack("<i", len(body)) + body)


def recv_packet(sock):
    raw_len = sock.recv(4)
    if len(raw_len) < 4:
        raise ConnectionError("connection closed by server")
    (length,) = struct.unpack("<i", raw_len)
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("connection closed mid-packet")
        data += chunk
    request_id, packet_type = struct.unpack("<ii", data[:8])
    payload = data[8:-2].decode("utf-8", "replace")
    return request_id, packet_type, payload


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rcon.py",
        description="Send RCON commands to a local Minecraft dedicated server.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=25575)
    parser.add_argument("--password", required=True)
    parser.add_argument("commands", nargs="+", help="commands to send, in order")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    try:
        with socket.create_connection((args.host, args.port), timeout=10) as sock:
            send_packet(sock, 1, TYPE_LOGIN, args.password)
            request_id, _ptype, _payload = recv_packet(sock)
            if request_id == -1:
                print("error: RCON authentication failed", file=sys.stderr)
                return 1
            for i, command in enumerate(args.commands, start=2):
                send_packet(sock, i, TYPE_COMMAND, command)
                _rid, _ptype, payload = recv_packet(sock)
                print(f"> {command}")
                print(payload if payload else "(no response text)")
    except (OSError, ConnectionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    # cp932: stdout is strict by default and one unencodable
    # character costs the whole run. Why `errors=` and not
    # `encoding=`: tools/test_console_encoding.py.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(main())
