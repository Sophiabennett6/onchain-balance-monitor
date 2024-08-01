#!/usr/bin/env python3
# onchain-balance-monitor: watch balances and alert on increases
# Requirements: pip install web3 requests python-dotenv
import os, time, csv
from datetime import datetime
from web3 import Web3
import requests

RPC_URL = os.getenv("RPC_URL", "https://mainnet.infura.io/v3/YOUR_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID", "")
ADDRESSES_FILE = os.getenv("ADDRESSES_FILE", "addresses.txt")
POLL_SEC = int(os.getenv("POLL_SEC", "30"))
LOG_FILE = os.getenv("LOG_FILE", "balances.csv")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    raise SystemExit("RPC not connected")

def tg_send(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID, "text": msg, "disable_web_page_preview": True
        }, timeout=10)
    except Exception:
        pass

def load_addresses():
    addrs = []
    with open(ADDRESSES_FILE) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                addrs.append(Web3.to_checksum_address(s))
    return addrs

def read_last():
    last = {}
    if not os.path.exists(LOG_FILE): return last
    with open(LOG_FILE) as f:
        r = csv.DictReader(f)
        for row in r:
            last[row["address"]] = int(row["wei"])
    return last

def append_log(ts, address, wei):
    exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["ts","address","wei","eth"])
        w.writerow([ts, address, wei, Web3.from_wei(wei, "ether")])

def main():
    addresses = load_addresses()
    last = read_last()
    tg_send(f"Balance monitor started for {len(addresses)} addresses")
    while True:
        for a in addresses:
            wei = w3.eth.get_balance(a)
            prev = last.get(a, 0)
            if wei != prev:
                ts = datetime.utcnow().isoformat()
                append_log(ts, a, wei)
                if wei > prev:
                    diff = Web3.from_wei(wei - prev, "ether")
                    tg_send(f"Incoming funds: +{diff} ETH to {a}")
                last[a] = wei
        time.sleep(POLL_SEC)

if __name__ == "__main__":
    main()
