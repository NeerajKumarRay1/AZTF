"""
Demo data generator for AI-NGFW dashboard.
Continuously injects synthetic flows + threat events + firewall rules
so the dashboard (charts, threat feed, geo-map, rules panel) comes alive.

Usage:
    python seed_demo.py            # continuous stream (Ctrl+C to stop)
    python seed_demo.py --once     # single burst of historical data, then exit
"""
import sys
import time
import uuid
import random
from datetime import datetime

import database
import firewall

ATTACKS = [
    ("DDoS", 0.97), ("PortScan", 0.91), ("Bruteforce-SSH", 0.95),
    ("Botnet-C2", 0.88), ("SQL-Injection", 0.93), ("HTTP-Flood", 0.90),
    ("Infiltration", 0.86), ("Heartbleed", 0.99),
]
PROTOCOLS = ["TCP", "UDP", "ICMP"]
# Public-ish source IPs to spread across the geo-map
SRC_POOL = [
    "45.83.12.7", "103.21.244.9", "185.220.101.5", "212.83.45.190",
    "91.198.174.2", "200.123.45.6", "41.203.18.22", "159.65.20.11",
    "13.114.40.8", "77.88.55.60", "117.18.232.200", "5.45.207.10",
]
DST = "10.0.2.15"  # the protected host


def rand_features():
    return {
        "src_bytes": random.randint(40, 50000),
        "dst_bytes": random.randint(40, 50000),
        "packet_count": random.randint(1, 800),
        "duration": round(random.uniform(0.01, 12.0), 3),
    }


def emit_flow(malicious: bool):
    flow_id = str(uuid.uuid4())
    src = random.choice(SRC_POOL)
    proto = random.choice(PROTOCOLS)
    sport = random.randint(1024, 65535)
    dport = random.choice([22, 80, 443, 3389, 53, 8080])
    feats = rand_features()
    database.log_flow(flow_id, src, DST, sport, dport, proto, feats)

    if malicious:
        atk, base = random.choice(ATTACKS)
        conf = round(min(0.99, base + random.uniform(-0.05, 0.02)), 4)
        verdict = 1
    else:
        atk, conf, verdict = "BENIGN", round(random.uniform(0.05, 0.45), 4), 0

    votes = {
        "rf": round(conf + random.uniform(-0.04, 0.04), 3),
        "xgb": round(conf + random.uniform(-0.04, 0.04), 3),
        "iso": round(conf + random.uniform(-0.06, 0.06), 3),
        "lstm": round(conf + random.uniform(-0.05, 0.05), 3),
    }
    database.log_threat_event(str(uuid.uuid4()), flow_id, atk, conf, verdict, votes)

    # Block high-confidence malicious sources (dry-run -> DB rule only)
    if verdict == 1 and conf >= 0.90:
        firewall.block_ip(src, duration_seconds=300, reason=f"{atk} detected ({conf*100:.0f}%)")
    return src, atk, verdict, conf


def main():
    database.init_db()
    once = "--once" in sys.argv

    if once:
        print("Seeding 60 historical events...")
        for _ in range(60):
            emit_flow(malicious=random.random() < 0.4)
        print("Done.")
        return

    print("Streaming demo traffic. Ctrl+C to stop.")
    try:
        while True:
            mal = random.random() < 0.35  # ~35% malicious
            src, atk, verdict, conf = emit_flow(mal)
            tag = "THREAT" if verdict else "ok"
            print(f"[{datetime.now():%H:%M:%S}] {tag:6} {src:16} {atk:14} {conf*100:5.1f}%")
            time.sleep(random.uniform(0.4, 1.6))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
