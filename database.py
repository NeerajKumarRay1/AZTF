import sqlite3
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

DB_FILE = os.getenv("DB_URI", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ngfw.db"))

def get_db_connection():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    print(f"Initializing database at {DB_FILE}...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Flows table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS flows (
        flow_id TEXT PRIMARY KEY,
        src_ip TEXT,
        dst_ip TEXT,
        src_port INTEGER,
        dst_port INTEGER,
        protocol TEXT,
        features_json TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 2. Threat Events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS threat_events (
        event_id TEXT PRIMARY KEY,
        flow_id TEXT,
        attack_type TEXT,
        confidence REAL,
        verdict INTEGER, -- 0 for benign, 1 for malicious
        model_votes_json TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (flow_id) REFERENCES flows (flow_id)
    )
    ''')
    
    # 3. Firewall Rules table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS firewall_rules (
        rule_id TEXT PRIMARY KEY,
        src_ip TEXT,
        action TEXT,
        reason TEXT,
        created_at DATETIME,
        expires_at DATETIME,
        created_by TEXT,
        revoked INTEGER DEFAULT 0
    )
    ''')
    
    # 4. Auth Events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS auth_events (
        event_id TEXT PRIMARY KEY,
        user_id TEXT,
        event_type TEXT,
        device_fingerprint TEXT,
        ip TEXT,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 5. Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indexes for speed
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_flows_src_ip ON flows(src_ip)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_flows_timestamp ON flows(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_threat_events_timestamp ON threat_events(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_firewall_rules_src_ip ON firewall_rules(src_ip)')
    
    conn.commit()
    conn.close()
    print("Database initialization complete.")

def log_flow(flow_id, src_ip, dst_ip, src_port, dst_port, protocol, features):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO flows (flow_id, src_ip, dst_ip, src_port, dst_port, protocol, features_json)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (flow_id, src_ip, dst_ip, src_port, dst_port, protocol, json.dumps(features)))
    conn.commit()
    conn.close()

def log_threat_event(event_id, flow_id, attack_type, confidence, verdict, votes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO threat_events (event_id, flow_id, attack_type, confidence, verdict, model_votes_json)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (event_id, flow_id, attack_type, confidence, verdict, json.dumps(votes)))
    conn.commit()
    conn.close()

def log_firewall_rule(rule_id, src_ip, action, reason, created_at, expires_at, created_by):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO firewall_rules (rule_id, src_ip, action, reason, created_at, expires_at, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (rule_id, src_ip, action, reason, created_at, expires_at, created_by))
    conn.commit()
    conn.close()

def log_auth_event(event_id, user_id, event_type, fingerprint, ip, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO auth_events (event_id, user_id, event_type, device_fingerprint, ip, status)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (event_id, user_id, event_type, json.dumps(fingerprint), ip, status))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
