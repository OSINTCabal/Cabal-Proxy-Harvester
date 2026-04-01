#!/usr/bin/env python3
"""
Cabal Proxy Harvester
=====================
OSINT Cabal - https://osintcabal.org
Author: Andreas Johansson
License: MIT

Continuously fetches, validates, and stores working HTTP/SOCKS5 proxies
from public proxy lists. Designed for OSINT research workflows.
"""

import requests
import time
import threading
import argparse
import sys
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

WORKING_FILE = "working_proxies.txt"
TEST_URL = "http://httpbin.org/ip"
TIMEOUT = 5
SLEEP_INTERVAL = 60  # seconds between harvest cycles
FETCH_LIMIT = 50     # proxies to pull per cycle

lock = threading.Lock()

# ─── Banner ───────────────────────────────────────────────────────────────────

BANNER = r"""
  ____      _           _   ____                      
 / ___|__ _| |__   __ _| | |  _ \ _ __ _____  ___   _ 
| |   / _` | '_ \ / _` | | | |_) | '__/ _ \ \/ / | | |
| |__| (_| | |_) | (_| | | |  __/| | | (_) >  <| |_| |
 \____\__,_|_.__/ \__,_|_| |_|   |_|  \___/_/\_\\__, |
  _   _                                           |___/ 
 | | | | __ _ _ ____   _____  ___| |_ ___ _ __        
 | |_| |/ _` | '__\ \ / / _ \/ __| __/ _ \ '__|       
 |  _  | (_| | |   \ V /  __/\__ \ ||  __/ |          
 |_| |_|\__,_|_|    \_/ \___||___/\__\___|_|           

        [ OSINT CABAL ] - Cabal Proxy Harvester
        Continuously harvesting & validating public proxies
"""

# ─── Fetch ────────────────────────────────────────────────────────────────────

def fetch_proxies(limit=FETCH_LIMIT):
    """Pull fresh proxies from GeoNode public proxy list API."""
    url = (
        f"https://proxylist.geonode.com/api/proxy-list"
        f"?limit={limit}&page=1&sort_by=lastChecked&sort_type=desc"
    )
    try:
        res = requests.get(url, timeout=10)
        data = res.json()["data"]
        proxies = [f"{p['ip']}:{p['port']}" for p in data]
        print(f"[>] Fetched {len(proxies)} candidates from GeoNode.")
        return proxies
    except Exception as e:
        print(f"[!] Fetch error: {e}")
        return []

# ─── Storage ──────────────────────────────────────────────────────────────────

def load_existing():
    """Load already-confirmed working proxies to avoid re-testing."""
    try:
        with open(WORKING_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_proxy(proxy, proto):
    """Append a verified working proxy to the output file with metadata."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{proxy} | {proto.upper()} | verified: {timestamp}\n"
    with lock:
        with open(WORKING_FILE, "a") as f:
            f.write(entry)

# ─── Testing ──────────────────────────────────────────────────────────────────

def test_proxy(proxy, scheme):
    """Test a proxy with a given scheme (http or socks5)."""
    try:
        proxies = {
            "http": f"{scheme}://{proxy}",
            "https": f"{scheme}://{proxy}",
        }
        r = requests.get(TEST_URL, proxies=proxies, timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False

def worker(proxy, existing):
    """Thread worker: test a proxy over HTTP then SOCKS5."""
    # Strip metadata if proxy came from existing file
    raw_proxy = proxy.split(" | ")[0].strip()

    if raw_proxy in existing:
        return

    print(f"    [*] Testing {raw_proxy}")

    if test_proxy(raw_proxy, "http"):
        print(f"    [+] HTTP  LIVE: {raw_proxy}")
        save_proxy(raw_proxy, "HTTP")
    elif test_proxy(raw_proxy, "socks5"):
        print(f"    [+] SOCKS5 LIVE: {raw_proxy}")
        save_proxy(raw_proxy, "SOCKS5")
    else:
        print(f"    [-] DEAD: {raw_proxy}")

# ─── Main Loop ────────────────────────────────────────────────────────────────

def run(interval=SLEEP_INTERVAL, limit=FETCH_LIMIT):
    """Main harvest loop."""
    cycle = 1
    while True:
        print(f"\n{'='*60}")
        print(f"  CYCLE #{cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        proxies = fetch_proxies(limit=limit)
        existing = load_existing()

        threads = []
        for proxy in proxies:
            t = threading.Thread(target=worker, args=(proxy, existing))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        total = len(load_existing())
        print(f"\n[=] Cycle #{cycle} complete. Total verified proxies: {total}")
        print(f"[=] Next cycle in {interval}s. Output: {WORKING_FILE}")
        cycle += 1
        time.sleep(interval)

# ─── Entry Point ──────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Cabal Proxy Harvester - OSINT proxy validation tool"
    )
    parser.add_argument(
        "--interval", type=int, default=SLEEP_INTERVAL,
        help=f"Seconds between harvest cycles (default: {SLEEP_INTERVAL})"
    )
    parser.add_argument(
        "--limit", type=int, default=FETCH_LIMIT,
        help=f"Proxies to fetch per cycle (default: {FETCH_LIMIT})"
    )
    parser.add_argument(
        "--output", type=str, default=WORKING_FILE,
        help=f"Output file for working proxies (default: {WORKING_FILE})"
    )
    return parser.parse_args()

if __name__ == "__main__":
    print(BANNER)
    args = parse_args()
    WORKING_FILE = args.output
    try:
        run(interval=args.interval, limit=args.limit)
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user. Exiting.")
        sys.exit(0)
