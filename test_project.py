import os
import time
import pytest
import database
import zero_trust
import firewall
from monitor import Flow

def test_flow_feature_extraction():
    # Create a flow: 192.168.1.100 -> 10.0.0.1 (TCP, ports 1234 -> 80)
    flow = Flow("192.168.1.100", "10.0.0.1", 1234, 80, "TCP")
    
    # Simulate adding packets in forward direction
    # Use mock packet length (e.g. 100 bytes)
    class MockPacket:
        def __len__(self):
            return 100
            
    pkt = MockPacket()
    flow.add_packet(pkt, "fwd")
    flow.add_packet(pkt, "fwd")
    
    # Simulate adding packet in backward direction (e.g. 150 bytes)
    class MockPacketBwd:
        def __len__(self):
            return 150
            
    pkt_bwd = MockPacketBwd()
    flow.add_packet(pkt_bwd, "bwd")
    
    # Add minor delay to simulate time duration
    time.sleep(0.05)
    flow.last_time = time.time()
    
    features = flow.get_features()
    
    assert features['protocol'] == 6
    assert features['src_pkts'] == 2
    assert features['dst_pkts'] == 1
    assert features['src_bytes'] == 200
    assert features['dst_bytes'] == 150
    assert features['duration'] >= 0.05
    assert features['rate'] > 0

def test_zero_trust_hashing_and_jwt():
    plain_pw = "supersecretpassword"
    hashed = zero_trust.hash_password(plain_pw)
    
    # 1. Hashing and verification
    assert zero_trust.verify_password(plain_pw, hashed) is True
    assert zero_trust.verify_password("wrongpassword", hashed) is False
    
    # 2. JWT Issuance
    payload = {"sub": "testuser", "role": "Analyst"}
    token = zero_trust.create_access_token(payload)
    assert token is not None
    
    # 3. JWT Decoding
    decoded = zero_trust.decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "testuser"
    assert decoded["role"] == "Analyst"
    
    # 4. RBAC Verification
    assert zero_trust.verify_role(decoded, "Viewer") is True
    assert zero_trust.verify_role(decoded, "Analyst") is True
    assert zero_trust.verify_role(decoded, "Admin") is False

def test_database_logging(tmp_path):
    # Initialize DB (creates database tables if not existing)
    database.init_db()
    
    # Log flow
    flow_id = "test-flow-uuid-1234"
    features = {'duration': 0.1, 'protocol': 6, 'src_bytes': 100, 'dst_bytes': 100, 'src_pkts': 1, 'dst_pkts': 1, 'rate': 20.0}
    database.log_flow(flow_id, "192.168.1.100", "10.0.0.1", 1234, 80, "TCP", features)
    
    # Verify logged flow exists in database
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM flows WHERE flow_id = ?", (flow_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row["src_ip"] == "192.168.1.100"
    assert row["dst_ip"] == "10.0.0.1"

def test_firewall_blocking():
    # Seed DB and firewall configurations
    database.init_db()
    firewall.set_dry_run(True)
    firewall.init_firewall()
    
    # Whitelist test
    assert firewall.block_ip("127.0.0.1") is False
    
    # Active block test
    test_ip = "203.0.113.88"
    blocked = firewall.block_ip(ip=test_ip, duration_seconds=5, reason="Test blocking")
    assert blocked is True
    
    # Fetch active blocks
    blocks = firewall.get_active_blocks()
    ips = [b["src_ip"] for b in blocks]
    assert test_ip in ips
    
    # Unblock test
    firewall.unblock_ip(test_ip)
    blocks_after = firewall.get_active_blocks()
    ips_after = [b["src_ip"] for b in blocks_after]
    assert test_ip not in ips_after
