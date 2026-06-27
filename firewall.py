import os
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import database

# Load environment configuration
load_dotenv()

# Whitelist to prevent blocking core infrastructure
WHITELIST_IPS = {"127.0.0.1", "localhost", "10.0.2.2", "0.0.0.0"}

# Global active timers to handle rule TTLs
active_timers = {}
# Enforce firewall blocking if NGFW_ENFORCE is set to 'true' in .env
dry_run = os.getenv("NGFW_ENFORCE", "false").lower() != "true"

def set_dry_run(mode: bool):
    global dry_run
    dry_run = mode
    print(f"Firewall: Dry Run mode set to {dry_run}")

def init_firewall():
    if dry_run:
        print("Firewall: Dry Run Mode enabled. No system commands will be executed.")
        return
        
    try:
        # Create ipset named 'blacklist' if it doesn't exist
        subprocess.run(['sudo', 'ipset', 'create', 'blacklist', 'hash:ip'], capture_output=True, text=True)
        # Check if the iptables rule linking to ipset is already present
        check_rule = subprocess.run(['sudo', 'iptables', '-C', 'INPUT', '-m', 'set', '--match-set', 'blacklist', 'src', '-j', 'DROP'], capture_output=True)
        if check_rule.returncode != 0:
            # Rule does not exist, insert it at the top (position 1)
            subprocess.run(['sudo', 'iptables', '-I', 'INPUT', '1', '-m', 'set', '--match-set', 'blacklist', 'src', '-j', 'DROP'], check=True)
            print("Firewall: Integrated ipset 'blacklist' with iptables successfully.")
        else:
            print("Firewall: ipset rule already present in iptables.")
    except Exception as e:
        print(f"Firewall warning (system configuration failed, falling back to dry-run): {e}")
        set_dry_run(True)

def block_ip(ip: str, duration_seconds: int = 300, reason: str = "Malicious traffic detected"):
    if ip in WHITELIST_IPS:
        print(f"Firewall: IP {ip} is in whitelist. Skipping block request.")
        return False
        
    # Cancel any existing timer for this IP to reset the TTL
    if ip in active_timers:
        active_timers[ip].cancel()
        del active_timers[ip]

    rule_id = str(uuid.uuid4())
    created_at = datetime.now()
    expires_at = created_at + timedelta(seconds=duration_seconds)

    print(f"Firewall: Blocking IP {ip} for {duration_seconds} seconds. Reason: {reason}")
    
    # 1. Execute system command if not in dry-run mode
    if not dry_run:
        try:
            # Add to ipset blacklist
            subprocess.run(['sudo', 'ipset', 'add', 'blacklist', ip], check=True)
        except Exception as e:
            print(f"Firewall error blocking {ip}: {e}")
            return False

    # 2. Log rule to database
    database.log_firewall_rule(
        rule_id=rule_id,
        src_ip=ip,
        action="BLOCK",
        reason=reason,
        created_at=created_at.strftime('%Y-%m-%d %H:%M:%S'),
        expires_at=expires_at.strftime('%Y-%m-%d %H:%M:%S'),
        created_by="ThreatDetectionModule"
    )

    # 3. Schedule automatic unblock timer
    timer = threading.Timer(duration_seconds, unblock_ip, args=[ip, rule_id])
    active_timers[ip] = timer
    timer.start()
    return True

def unblock_ip(ip: str, rule_id: str = None):
    print(f"Firewall: Unblocking IP {ip} (TTL expired)...")
    
    # 1. Execute system command if not in dry-run mode
    if not dry_run:
        try:
            # Remove from ipset blacklist
            subprocess.run(['sudo', 'ipset', 'del', 'blacklist', ip], check=True)
        except Exception as e:
            print(f"Firewall error unblocking {ip}: {e}")
            # Do not return, log the revocation in the DB anyway

    # 2. Update rule in database
    conn = database.get_db_connection()
    cursor = conn.cursor()
    if rule_id:
        cursor.execute("UPDATE firewall_rules SET revoked = 1 WHERE rule_id = ?", (rule_id,))
    else:
        cursor.execute("UPDATE firewall_rules SET revoked = 1 WHERE src_ip = ? AND revoked = 0", (ip,))
    conn.commit()
    conn.close()

    # 3. Remove timer reference
    if ip in active_timers:
        del active_timers[ip]

def get_active_blocks():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM firewall_rules WHERE revoked = 0 AND expires_at > ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
