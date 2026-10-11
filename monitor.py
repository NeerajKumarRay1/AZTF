import pandas as pd
import os
import time
import argparse
import random
import uuid
import numpy as np
import joblib
from scapy.all import sniff, IP, TCP, UDP, ICMP
import database
import firewall

# Paths to models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Global variables for models
rf_model = None
xgb_model = None
iso_model = None
lstm_model = None
scaler = None

# Flow tracker dictionary
# Key: 5-tuple (src_ip, dst_ip, src_port, dst_port, protocol)
active_flows = {}
FLOW_TIMEOUT = 5.0  # seconds

# LSTM sliding window buffers per source IP
lstm_buffers = {}
SEQUENCE_LENGTH = 10

def load_all_models():
    global rf_model, xgb_model, iso_model, lstm_model, scaler
    try:
        scaler = joblib.load(os.path.join(MODELS_DIR, "scaler.joblib"))
        rf_model = joblib.load(os.path.join(MODELS_DIR, "rf_model.joblib"))
        xgb_model = joblib.load(os.path.join(MODELS_DIR, "xgb_model.joblib"))
        iso_model = joblib.load(os.path.join(MODELS_DIR, "iso_model.joblib"))
        print("Models loaded successfully.")
    except Exception as e:
        print(f"Error loading models: {e}")
        print("Ensure you run train_models.py before starting the monitor.")
        
    try:
        from tensorflow.keras.models import load_model
        lstm_model_path = os.path.join(MODELS_DIR, "lstm_model.h5")
        if os.path.exists(lstm_model_path):
            lstm_model = load_model(lstm_model_path)
            print("LSTM model loaded successfully.")
    except Exception as e:
        print(f"LSTM loading skipped or failed: {e}")

class Flow:
    def __init__(self, src_ip, dst_ip, src_port, dst_port, protocol):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.protocol = protocol
        
        self.start_time = time.time()
        self.last_time = time.time()
        
        self.src_bytes = 0
        self.dst_bytes = 0
        self.src_pkts = 0
        self.dst_pkts = 0
        
    def add_packet(self, pkt, direction):
        self.last_time = time.time()
        pkt_len = len(pkt)
        
        if direction == "fwd":
            self.src_pkts += 1
            self.src_bytes += pkt_len
        else:
            self.dst_pkts += 1
            self.dst_bytes += pkt_len
            
    def get_features(self):
        duration = self.last_time - self.start_time
        total_pkts = self.src_pkts + self.dst_pkts
        rate = total_pkts / (duration + 1e-6)
        
        # Protocol mapping
        proto_num = 0
        if self.protocol == "TCP":
            proto_num = 6
        elif self.protocol == "UDP":
            proto_num = 17
        elif self.protocol == "ICMP":
            proto_num = 1
            
        return {
            'duration': duration,
            'protocol': proto_num,
            'src_bytes': self.src_bytes,
            'dst_bytes': self.dst_bytes,
            'src_pkts': self.src_pkts,
            'dst_pkts': self.dst_pkts,
            'rate': rate
        }

def process_packet(pkt):
    try:
        if IP not in pkt:
            return

        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst

        protocol = "OTHER"
        src_port = 0
        dst_port = 0

        if TCP in pkt:
            protocol = "TCP"
            src_port = pkt[TCP].sport
            dst_port = pkt[TCP].dport
        elif UDP in pkt:
            protocol = "UDP"
            src_port = pkt[UDP].sport
            dst_port = pkt[UDP].dport
        elif ICMP in pkt:
            protocol = "ICMP"

        endpoint_a = (src_ip, src_port)
        endpoint_b = (dst_ip, dst_port)

        if endpoint_a <= endpoint_b:
            flow_key = (
                src_ip, dst_ip, src_port, dst_port, protocol
            )
            direction = "fwd"
        else:
            flow_key = (
                dst_ip, src_ip, dst_port, src_port, protocol
            )
            direction = "bwd"

        now = time.time()

        expired_keys = [
            key for key, existing_flow in active_flows.items()
            if now - existing_flow.last_time >= FLOW_TIMEOUT
        ]

        for key in expired_keys:
            expired_flow = active_flows.pop(key)
            print(
                f"[Flow expired] {expired_flow.src_ip} -> "
                f"{expired_flow.dst_ip}, packets="
                f"{expired_flow.src_pkts + expired_flow.dst_pkts}"
            )
            evaluate_flow(expired_flow)

        if flow_key not in active_flows:
            active_flows[flow_key] = Flow(
                src_ip, dst_ip, src_port, dst_port, protocol
            )

        flow = active_flows[flow_key]
        flow.add_packet(pkt, direction)

        if TCP in pkt:
            flags = pkt[TCP].flags
            if 'F' in flags or 'R' in flags:
                active_flows.pop(flow_key, None)
                print(f"[Flow closed] {src_ip} -> {dst_ip}")
                evaluate_flow(flow)

    except Exception:
        import traceback
        print("[Packet processing error]")
        traceback.print_exc()

def evaluate_flow(flow):
    global rf_model, xgb_model, iso_model, lstm_model, scaler
    
    if scaler is None or rf_model is None:
        # Dry-run logging to database without ML inference
        flow_id = str(uuid.uuid4())
        features = flow.get_features()
        database.log_flow(
            flow_id, flow.src_ip, flow.dst_ip,
            flow.src_port, flow.dst_port, flow.protocol, features
        )
        return        
    features = flow.get_features()
    flow_id = str(uuid.uuid4())
    
    # 1. Log flow metadata to database
    database.log_flow(flow_id, flow.src_ip, flow.dst_ip, flow.src_port, flow.dst_port, flow.protocol, features)
    

    # 2. Extract features with the expected column names
    feature_names = [
        'duration', 'protocol', 'src_bytes', 'dst_bytes',
        'src_pkts', 'dst_pkts', 'rate'
    ]

    feat_vector = pd.DataFrame(
        [[features[name] for name in feature_names]],
        columns=feature_names
    )

    # Preprocess
    feat_scaled = scaler.transform(feat_vector)    
    # 3. Model Predictions
    votes = {}
    
    # Random Forest Prediction
    prob_rf = rf_model.predict_proba(feat_scaled)[0][1]
    votes["Random Forest"] = float(prob_rf)
    
    # XGBoost Prediction
    prob_xgb = xgb_model.predict_proba(feat_scaled)[0][1]
    votes["XGBoost"] = float(prob_xgb)
    
    # Isolation Forest Anomaly Prediction
    # 1 = Normal, -1 = Anomaly (map anomaly to 1.0, normal to 0.0)
    pred_iso = iso_model.predict(feat_scaled)[0]
    prob_iso = 1.0 if pred_iso == -1 else 0.0
    votes["Isolation Forest"] = float(prob_iso)
    
    # LSTM Prediction if window buffer is complete
    prob_lstm = 0.0
    if lstm_model is not None:
        src_ip = flow.src_ip
        if src_ip not in lstm_buffers:
            lstm_buffers[src_ip] = []
        lstm_buffers[src_ip].append(feat_scaled[0])
        
        # Keep buffer length to SEQUENCE_LENGTH
        if len(lstm_buffers[src_ip]) > SEQUENCE_LENGTH:
            lstm_buffers[src_ip].pop(0)
            
        if len(lstm_buffers[src_ip]) == SEQUENCE_LENGTH:
            # Build input shape: (1, 10, 7)
            lstm_input = np.array([lstm_buffers[src_ip]])
            prob_lstm = float(lstm_model.predict(lstm_input, verbose=0)[0][0])
            votes["LSTM"] = prob_lstm
            
    # 4. Ensemble Verdict
    # Weights: RF: 0.30, XGBoost: 0.35, Isolation Forest: 0.20, LSTM: 0.15
    if "LSTM" in votes:
        verdict_score = (0.30 * prob_rf) + (0.35 * prob_xgb) + (0.20 * prob_iso) + (0.15 * prob_lstm)
    else:
        # Re-normalize weights without LSTM: RF: 0.35, XGBoost: 0.45, IF: 0.20
        verdict_score = (0.35 * prob_rf) + (0.45 * prob_xgb) + (0.20 * prob_iso)
        
    verdict = 1 if verdict_score >= 0.60 else 0
    attack_type = "BENIGN"
    
    if verdict == 1:
        # Classify attack type based on dominant prediction signatures
        if prob_rf > 0.8 and features['rate'] > 500:
            attack_type = "DDoS SYN Flood"
        elif prob_xgb > 0.8 and features['dst_pkts'] == 0:
            attack_type = "Port Scan"
        elif prob_lstm > 0.7:
            attack_type = "Botnet Traffic"
        else:
            attack_type = "Anomaly/Zero-Day Intrusion"
            
    # 5. Log Threat Event
    event_id = str(uuid.uuid4())
    database.log_threat_event(
        event_id=event_id,
        flow_id=flow_id,
        attack_type=attack_type,
        confidence=float(verdict_score),
        verdict=verdict,
        votes=votes
    )
    
    # 6. Apply Firewall Rule if malicious
    if verdict == 1:
        firewall.block_ip(
            ip=flow.src_ip,
            duration_seconds=300,
            reason=f"{attack_type} detected (confidence: {verdict_score*100:.1f}%)"
        )

# --- Rich Simulation Engine for Demos ---
def run_simulation():
    print("Starting network traffic simulation...")
    ips = [f"192.168.1.{i}" for i in range(10, 100)]
    external_ips = ["45.79.112.203", "185.190.140.23", "203.0.113.5", "198.51.100.77"]
    
    while True:
        mode = random.choices(["benign", "ddos", "portscan", "bruteforce"], weights=[70, 15, 10, 5])[0]
        
        if mode == "benign":
            # Normal HTTP or DNS flow
            src = random.choice(ips)
            dst = random.choice(external_ips)
            proto = random.choice(["TCP", "UDP"])
            sport = random.randint(49152, 65535)
            dport = 80 if proto == "TCP" else 53
            
            flow = Flow(src, dst, sport, dport, proto)
            flow.src_pkts = random.randint(5, 20)
            flow.dst_pkts = random.randint(5, 30)
            flow.src_bytes = flow.src_pkts * random.randint(64, 1500)
            flow.dst_bytes = flow.dst_pkts * random.randint(64, 1500)
            flow.last_time = flow.start_time + random.uniform(0.1, 2.0)
            evaluate_flow(flow)
            
        elif mode == "ddos":
            # SYN Flood simulation
            src = random.choice(external_ips)
            dst = "192.168.1.5"  # Local server
            proto = "TCP"
            sport = random.randint(1024, 65535)
            dport = 80
            
            print(f"[Sim] Generating DDoS SYN Flood from {src} to {dst}")
            # Generate 5 concurrent dense flows
            for _ in range(5):
                flow = Flow(src, dst, sport, dport, proto)
                flow.src_pkts = random.randint(100, 500)
                flow.dst_pkts = 0  # No response in SYN Flood
                flow.src_bytes = flow.src_pkts * 64
                flow.dst_bytes = 0
                flow.last_time = flow.start_time + random.uniform(0.01, 0.05)
                evaluate_flow(flow)
                time.sleep(0.1)
                
        elif mode == "portscan":
            # Port Scan simulation
            src = random.choice(external_ips)
            dst = "192.168.1.10"
            proto = "TCP"
            
            print(f"[Sim] Generating Port Scan from {src} to {dst}")
            # Scan multiple ports sequentially
            start_port = random.randint(20, 100)
            for port in range(start_port, start_port + 15):
                flow = Flow(src, dst, random.randint(40000, 60000), port, proto)
                flow.src_pkts = 1
                flow.dst_pkts = 0
                flow.src_bytes = 64
                flow.dst_bytes = 0
                flow.last_time = flow.start_time + 0.001
                evaluate_flow(flow)
                time.sleep(0.05)
                
        elif mode == "bruteforce":
            # Repeated SSH login attempts
            src = random.choice(external_ips)
            dst = "192.168.1.22"
            proto = "TCP"
            dport = 22
            
            print(f"[Sim] Generating Brute-Force SSH attempts from {src}")
            # Repeated flows in sequence
            for _ in range(10):
                flow = Flow(src, dst, random.randint(50000, 60000), dport, proto)
                flow.src_pkts = random.randint(8, 15)
                flow.dst_pkts = random.randint(8, 15)
                flow.src_bytes = flow.src_pkts * 120
                flow.dst_bytes = flow.dst_pkts * 150
                flow.last_time = flow.start_time + random.uniform(0.5, 1.5)
                evaluate_flow(flow)
                time.sleep(0.2)
                
        time.sleep(random.uniform(1.0, 3.0))

def main():
    parser = argparse.ArgumentParser(description="AI-NGFW Traffic Monitor")
    parser.add_argument("--pcap", type=str, help="PCAP file to replay offline")
    parser.add_argument("--simulate", action="store_true", help="Run simulated network traffic engine")
    parser.add_argument("--live", action="store_true", help="Sniff live packets on eth0")
    parser.add_argument("--enforce", action="store_true", help="Enable actual iptables/ipset blocking rules")
    
    args = parser.parse_args()
    
    # Database check
    database.init_db()
    
    # Firewall setup
    if args.enforce:
        firewall.set_dry_run(False)
    firewall.init_firewall()
    
    # Load ML models
    load_all_models()
    
    if args.simulate:
        run_simulation()
    elif args.pcap:
        print(f"Replaying PCAP file: {args.pcap}")
        sniff(offline=args.pcap, prn=process_packet, store=0)
    elif args.live:
        print("Sniffing live packets on eth0...")
        sniff(iface="eth0", prn=process_packet, store=0)
    else:
        print("No ingestion mode specified. Run with --simulate, --pcap <file>, or --live.")

if __name__ == "__main__":
    main()
