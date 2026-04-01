# 🕸️ Cabal Proxy Harvester

**By [OSINT Cabal](https://osintcabal.org)**

A lightweight, multithreaded Python tool that continuously fetches public proxies, validates them in real time over HTTP and SOCKS5, and writes verified working proxies to a local database file. Built for OSINT research workflows where reliable, rotating proxy infrastructure matters.

---

## Features

- 🔄 **Continuous harvesting** — runs in a loop, fetching fresh proxies every cycle
- ⚡ **Multithreaded validation** — tests all candidates in parallel for speed
- 🌐 **HTTP & SOCKS5 support** — tests both protocols per proxy
- 🗂️ **Deduplication** — skips proxies already confirmed working
- 🕒 **Timestamped output** — each verified proxy is logged with protocol and verification time
- 🖥️ **CLI flags** — configurable interval, fetch limit, and output file

---

## How It Works

```
┌──────────────────────────────────────────────────────┐
│  1. Fetch           │  Pulls proxy candidates from   │
│                     │  GeoNode's public API (sorted  │
│                     │  by most recently checked)     │
├──────────────────────────────────────────────────────┤
│  2. Deduplicate     │  Loads working_proxies.txt and │
│                     │  skips already-verified IPs    │
├──────────────────────────────────────────────────────┤
│  3. Validate        │  Each proxy is tested via      │
│  (multithreaded)    │  HTTP first, then SOCKS5, by   │
│                     │  hitting httpbin.org/ip        │
├──────────────────────────────────────────────────────┤
│  4. Save            │  Working proxies are appended  │
│                     │  to working_proxies.txt with   │
│                     │  protocol + timestamp metadata │
├──────────────────────────────────────────────────────┤
│  5. Sleep & Repeat  │  Waits (default 60s), then     │
│                     │  fetches a fresh batch         │
└──────────────────────────────────────────────────────┘
```

The proxy source is the [GeoNode Public Proxy API](https://proxylist.geonode.com/), which provides regularly updated free proxy lists sorted by last-checked time — meaning you get the freshest candidates on every cycle.

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/cabal-proxy-harvester.git
cd cabal-proxy-harvester
pip install -r requirements.txt
```

> Requires Python 3.7+

---

## Usage

### Basic (default settings)

```bash
python cabal_proxy_harvester.py
```

Runs continuously, fetching 50 proxies every 60 seconds, saving results to `working_proxies.txt`.

### Custom options

```bash
python cabal_proxy_harvester.py --interval 120 --limit 100 --output my_proxies.txt
```

| Flag | Default | Description |
|------|---------|-------------|
| `--interval` | `60` | Seconds between harvest cycles |
| `--limit` | `50` | Number of proxies to fetch per cycle |
| `--output` | `working_proxies.txt` | Output file for verified proxies |

### Stop the harvester

```
Ctrl+C
```

---

## Output Format

Each verified proxy is written to the output file in the following format:

```
123.45.67.89:8080 | HTTP | verified: 2025-04-01 14:32:10
98.76.54.32:1080 | SOCKS5 | verified: 2025-04-01 14:32:14
```

Fields: `IP:PORT | PROTOCOL | verified: TIMESTAMP`

---

## Querying the Database

The output file is plain text, making it easy to filter and parse with standard tools.

### View all working proxies

```bash
cat working_proxies.txt
```

### Count total verified proxies

```bash
wc -l working_proxies.txt
```

### Filter by protocol

```bash
# HTTP only
grep "| HTTP |" working_proxies.txt

# SOCKS5 only
grep "| SOCKS5 |" working_proxies.txt
```

### Get just the IP:PORT list (no metadata)

```bash
awk '{print $1}' working_proxies.txt
```

### Get proxies verified today

```bash
grep "$(date +%Y-%m-%d)" working_proxies.txt
```

### Extract a random proxy for use

```bash
shuf -n 1 working_proxies.txt | awk '{print $1}'
```

---

## Using Proxies in Your Workflow

### curl

```bash
# HTTP proxy
curl -x http://123.45.67.89:8080 https://example.com

# SOCKS5 proxy
curl --socks5 123.45.67.89:1080 https://example.com
```

### Python (requests)

```python
import random

def load_proxies(path="working_proxies.txt"):
    proxies = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(" | ")
            if len(parts) >= 2:
                ip_port = parts[0]
                proto = parts[1].lower()
                proxies.append((ip_port, proto))
    return proxies

def get_random_proxy(proxies):
    ip_port, proto = random.choice(proxies)
    scheme = "socks5" if proto == "socks5" else "http"
    return {
        "http": f"{scheme}://{ip_port}",
        "https": f"{scheme}://{ip_port}"
    }

proxies = load_proxies()
proxy = get_random_proxy(proxies)

import requests
r = requests.get("https://httpbin.org/ip", proxies=proxy, timeout=5)
print(r.json())
```

### Rotating through proxies in a loop

```python
import itertools

proxy_cycle = itertools.cycle(load_proxies())

for target in my_targets:
    ip_port, proto = next(proxy_cycle)
    scheme = "socks5" if proto == "socks5" else "http"
    proxy = {"http": f"{scheme}://{ip_port}", "https": f"{scheme}://{ip_port}"}
    try:
        r = requests.get(target, proxies=proxy, timeout=5)
        # process r
    except:
        pass  # proxy may have gone dead, cycle to next
```

### Proxychains integration

Export a clean list for use with proxychains:

```bash
# Generate proxychains-compatible lines
awk '{print $1}' working_proxies.txt | awk -F: '{print "socks5 " $1 " " $2}' > proxychains_list.txt
```

---

## Notes

- Public proxies are **ephemeral** — they come and go. Running the harvester continuously ensures your list stays fresh.
- This tool does **not** guarantee anonymity. Free public proxies may log traffic, be honeypots, or be operated by adversarial parties. Use appropriately and layer with VPN/Tor where operational security matters.
- The tool tests connectivity only — it does not verify whether a proxy leaks your real IP via WebRTC or DNS. For high-stakes ops, verify proxies manually.

---

## License

MIT — free to use, modify, and redistribute.

---

*Built for the OSINT Cabal community. Tip the tipline: tipline@osintcabal.org*
