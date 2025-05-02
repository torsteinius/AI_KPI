# oslo_feed_client.py
import socket, ssl, time, re
from datetime import datetime
from pathlib import Path

HOST = "146.72.205.26"     # production
PORT = 9403
USER = "your_login"
PWD  = "your_password"

BASE = Path("data/oslo")
BASE.mkdir(parents=True, exist_ok=True)

TD = b"\n"                 # transaction delimiter

def send(sock, msg):
    sock.sendall((msg + "\n").encode())

def main():
    with socket.create_connection((HOST, PORT)) as raw:
        # optional TLS wrap:
        # raw = ssl.wrap_socket(raw, do_handshake_on_connect=True)
        send(raw, "S_CONNECT_REQ")
        raw.recv(2048)                        # S_ACK
        send(raw, f"S_LOGON_REQ;{USER};{PWD}")
        raw.recv(2048)                        # S_ACK
        send(raw, "S_CMD_START_REQ;REALTIME;0")

        buf = b""
        while True:
            chunk = raw.recv(4096)
            if not chunk:
                break
            buf += chunk
            while TD in buf:
                line, buf = buf.split(TD, 1)
                handle_tx(line.decode(errors="ignore"))

def handle_tx(tx):
    if not tx or tx.startswith("S_"):
        return                                # control message
    parts = tx.split(";")
    tag  = parts[0]
    if tag == "n":                            # NewsItem
        row = parse_news(parts)
        day = row["published"].strftime("%Y-%m-%d")
        out = BASE / f"news_{day}.log"
        out.write_text(str(row) + "\n", encoding="utf-8", append=True)
        print("⤵", row["newsURL"])

def parse_news(p):
    # crude field map – refine as needed
    d = {}
    for field in p[1:]:
        if field.startswith("URLn"):
            d["newsURL"] = field[4:]
        elif field.startswith("t"):
            ts = field[1:]
            d["published"] = datetime.strptime(ts, "%Y%m%d%H%M%S")
        elif field.startswith("ISYm"):
            d["ticker"] = field[4:]
        elif field.startswith("Nt"):
            d["typeNO"] = field[2:]
        elif field.startswith("NTe"):
            d["typeEN"] = field[3:]
    return d

if __name__ == "__main__":
    main()
