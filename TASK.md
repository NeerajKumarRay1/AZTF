# AI-Driven NGFW — Implementation Task List

**Project:** AI-Driven Next-Generation Firewall for Dynamic Threat Detection and Zero Trust Implementation  
**Stack:** Python 3.10+ · Scikit-learn · XGBoost · TensorFlow/Keras · Scapy · Flask/FastAPI · SQLite/MySQL · iptables  
**Environment:** Windows 10/11 + WSL2 (Ubuntu 22.04+)

> **WSL2 Strategy:** All development (ML training, API, dashboard) runs on Windows using VS Code with the WSL2 extension. Only the packet capture (Scapy) and firewall enforcement (iptables) components run inside WSL2, where they have full Linux kernel access. PCAP replay mode is used for demos to avoid raw socket permission issues.

---

## Phase 0 — WSL2 Setup (Before Everything Else)

> Complete this phase first. All subsequent phases depend on it.

### 0.1 Enable WSL2 on Windows
- [x] Open PowerShell as Administrator and run: `wsl --install`
- [x] Restart Windows when prompted
- [x] On reboot, Ubuntu will launch automatically — set a UNIX username and password
- [x] Verify WSL2 is active: `wsl --list --verbose` (should show `VERSION 2`)
- [x] Update WSL2 kernel: `wsl --update`

### 0.2 Configure Ubuntu inside WSL2
- [x] Update package lists: `sudo apt update && sudo apt upgrade -y`
- [x] Install system tools: `sudo apt install -y python3 python3-pip python3-venv git curl wget net-tools ipset`
- [x] Install network tools: `sudo apt install -y tshark wireshark-common libpcap-dev`
- [x] Install Suricata: `sudo apt install -y suricata`
- [x] Verify iptables is available: `sudo iptables -L` (should list default chains)
- [x] Install ipset: `sudo apt install -y ipset`

### 0.3 Install IDE Integration
- [x] Use Antigravity IDE for development (active)
- [x] Access project folder in the IDE
- [x] Confirm workspace connection is active

### 0.4 Configure Networking for Scapy in WSL2
- [x] Identify your WSL2 network interface inside Ubuntu: `ip link show` (usually `eth0`)
- [x] Grant Scapy raw socket access without root every time:  
  `sudo setcap cap_net_raw,cap_net_admin+eip $(readlink -f $(which python3))`
- [x] Test Scapy import inside WSL2 (requires venv python after Phase 1.1): `python3 -c "from scapy.all import *; print('Scapy OK')"`
- [x] **Note:** For live capture, always run Scapy scripts from inside WSL2 terminal, not Windows terminal
- [x] Set up PCAP replay as the default demo mode (place sample PCAP files in `/home/<user>/pcaps/`)

### 0.5 Set Up Shared Project Folder
- [x] Create project folder inside WSL2 home: `mkdir ~/ai-ngfw && cd ~/ai-ngfw`
- [x] Access this folder from Windows Explorer at: `\\wsl$\Ubuntu-22.04\home\<user>\ai-ngfw`
- [x] Create Python virtual environment: `python3 -m venv venv && source venv/bin/activate`
- [x] Initialize Git repo: `git init` and connect to GitHub remote

---

## Phase 1 — Project Setup & Data Acquisition (Weeks 1–4)

### 1.1 Python Environment (Inside WSL2)
- [x] Activate venv: `source ~/ai-ngfw/venv/bin/activate`
- [x] Install all Python dependencies:  
  `pip install scikit-learn xgboost tensorflow pandas numpy flask fastapi uvicorn pyjwt bcrypt joblib imbalanced-learn scapy python-dotenv websockets`
- [x] Install dev tools: `pip install pytest black flake8 jupyter`
- [x] Freeze requirements: `pip freeze > requirements.txt`
- [x] Set up SQLite for dev (no install needed — built into Python)
- [x] Install MySQL inside WSL2 for prod: `sudo apt install -y mysql-server`
- [x] Configure `.env` file with: `SECRET_KEY`, `DB_URI`, `JWT_SECRET`, `SMTP_HOST`

### 1.2 GitHub Repository Setup
- [x] Create GitHub repo: `ai-ngfw`
- [x] Set up branch strategy: `main` (stable), `dev` (active), feature branches per module
- [x] Add `.gitignore` (exclude `venv/`, `.env`, `*.h5`, `*.joblib`, `pcaps/`, datasets)
- [x] Add initial `README.md` with project title and tech stack

### 1.3 Dataset Acquisition & EDA
- [x] Download **CICIDS2017** dataset from University of New Brunswick (store in WSL2 at `~/ai-ngfw/data/cicids2017/`)
- [x] Download **UNSW-NB15** dataset from UNSW Canberra (`~/ai-ngfw/data/unsw_nb15/`)
- [x] Download **NSL-KDD** dataset (`~/ai-ngfw/data/nsl_kdd/`)
- [x] Run EDA notebook: check shape, class distribution, null values, data types for each dataset
- [x] Document feature columns and attack label mappings per dataset
- [x] Identify and resolve schema differences across the three datasets

---

## Phase 2 — Data Preprocessing & Model Training (Weeks 5–10)

> Run all training inside WSL2 using Jupyter or plain Python scripts. Models train faster here due to direct memory access vs. Windows overhead.

### 2.1 Data Preprocessing Pipeline
- [x] Merge datasets with a unified schema (aligned column names and label format)
- [x] Remove duplicate flows and rows with `inf` / `NaN` values
- [x] Encode categorical labels with `LabelEncoder`
- [x] Apply **SMOTE** to balance minority attack classes
- [x] Normalize features with `StandardScaler` (zero mean, unit variance)
- [x] Split data: 70% train / 15% validation / 15% test (stratified)
- [x] Save scaler and encoder objects with `joblib` for later inference use

### 2.2 Random Forest Classifier
- [x] Train Random Forest (`n_estimators=200`, `class_weight='balanced'`, `n_jobs=-1`)
- [x] Evaluate: accuracy, precision, recall, F1, confusion matrix
- [x] Generate feature importance report
- [x] Serialize trained model: `joblib.dump(rf_model, 'models/rf_model.joblib')`

### 2.3 XGBoost Classifier
- [x] Train XGBoost (`n_estimators=300`, `learning_rate=0.05`, `max_depth=6`, `subsample=0.8`)
- [x] Compute `scale_pos_weight` per class for imbalance handling
- [x] Evaluate with same metrics as Random Forest
- [x] Serialize trained model: `joblib.dump(xgb_model, 'models/xgb_model.joblib')`

### 2.4 Isolation Forest (Anomaly Detection)
- [x] Train Isolation Forest on **benign traffic only** (`n_estimators=100`, `contamination=0.05`)
- [x] Evaluate anomaly detection rate on attack samples (FPR < 5%)
- [x] Serialize model: `joblib.dump(iso_model, 'models/iso_model.joblib')`

### 2.5 Hyperparameter Tuning
- [x] Run `GridSearchCV` or `RandomizedSearchCV` on RF and XGBoost
- [x] Document best parameters and resulting metric improvements
- [x] Target: ≥ 95% accuracy on validation set for all supervised models

---

## Phase 3 — Core Backend Modules (Weeks 11–16)

> All modules run inside WSL2. Edit code from VS Code on Windows (via WSL extension); run scripts from WSL2 terminal.

### 3.1 Traffic Monitoring Module
- [x] Implement packet sniffer using **Scapy** on WSL2 interface `eth0`
- [x] Build TCP/UDP flow tracker using 5-tuple key (src IP, dst IP, src port, dst port, protocol)
- [x] Implement feature extraction for 78 flow-level features mirroring CICIDS2017 feature set
- [x] Implement **PCAP replay mode** as the primary demo path:  
  `sniff(offline='pcaps/cicids_attack.pcap', prn=process_packet)`
- [x] Integrate **Suricata** inside WSL2 as parallel signature-based pre-filter:  
  `sudo suricata -c /etc/suricata/suricata.yaml -i eth0`
- [x] Publish completed flow feature vectors to internal detection queue (`queue.Queue` or Redis)

### 3.2 Threat Detection Module
- [x] Load serialized RF, XGBoost, and Isolation Forest models at startup
- [x] Implement preprocessing at inference time (load saved `StandardScaler`, impute missing values)
- [x] Run all three models in **parallel threads** per feature vector
- [x] Implement **weighted ensemble voting** (RF: 0.30, XGBoost: 0.35, IF: 0.20, LSTM: 0.15)
- [x] Apply configurable confidence threshold (default: 0.60) to produce final verdict
- [x] Generate `ThreatEvent` object (attack type, confidence, source IP, timestamp)
- [x] Forward high-confidence threats to the Firewall Module
- [x] Log all predictions (benign and malicious) to the database

### 3.3 Dynamic Firewall Module (iptables via WSL2)
- [x] Design `Rule` schema (rule_id UUID, source_ip, action, reason, created_at, expires_at, created_by)
- [x] Implement IP blacklisting via `iptables` inside WSL2 using Python `subprocess`:  
  `subprocess.run(['sudo', 'iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'], check=True)`
- [x] Implement **rate limiting** rules for suspicious but unconfirmed IPs
- [x] Implement rule TTL: schedule auto-removal using Python `threading.Timer`
- [x] Use **ipset** inside WSL2 for batch IP blocking: `sudo ipset create blacklist hash:ip`
- [x] Implement **dry-run mode** that logs rules to DB without calling iptables (useful for Windows-only testing)
- [x] Implement rule conflict resolution: skip rules conflicting with whitelist entries
- [x] Maintain full timestamped audit log of all rule changes in DB

### 3.4 Zero Trust Engine
- [x] Implement HTTPS login endpoint with `bcrypt` password verification
- [x] Issue **JWT access token** (15-min TTL) and **refresh token** (7-day TTL) using `PyJWT`
- [x] Implement **device fingerprinting** (OS, browser user-agent, MAC address)
- [x] Match device fingerprint against registered profile on each login
- [x] Implement **RBAC** with three roles: Admin, Analyst, Viewer
- [x] Enforce least-privilege: each role has a defined permission set
- [x] Monitor session activity; terminate idle sessions after configurable timeout
- [x] Require re-authentication for privileged actions regardless of session age
- [x] Log all auth events: login attempts, device verifications, RBAC access decisions

### 3.5 REST API Layer
- [x] Set up **FastAPI** app inside WSL2: `uvicorn main:app --host 0.0.0.0 --port 8000`
- [x] Access API from Windows browser at `http://localhost:8000` (WSL2 ports auto-forwarded)
- [x] Create endpoints: `/auth/login`, `/auth/refresh`, `/threats`, `/rules`, `/rules/{id}`, `/dashboard/stats`
- [x] Secure all endpoints with JWT middleware (except `/auth/login`)
- [x] Implement WebSocket endpoint for real-time dashboard streaming

---

## Phase 4 — LSTM Model & Dashboard (Weeks 17–22)

### 4.1 LSTM Model
- [x] Build LSTM architecture: Input `(seq_len=10, features=78)` → LSTM(128, dropout=0.2, return_sequences=True) → LSTM(64, dropout=0.2) → Dense(32, ReLU) → Output(Softmax)
- [x] Train with Adam optimizer, Categorical Cross-Entropy loss, 50 epochs, batch size 64
- [x] Implement **sequence buffer** to feed sliding windows of 10 consecutive flows per source IP
- [x] Evaluate on temporal attack scenarios (botnet C2, slow DDoS)
- [x] Save trained model: `model.save('models/lstm_model.h5')`
- [x] Integrate LSTM output into ensemble voting pipeline (weight: 0.15 when buffer is filled)

### 4.2 Dashboard & Analytics Module
- [x] Build frontend (HTML/JS + Chart.js/Plotly, or React) — accessible from Windows browser
- [x] Panel: **Live Traffic Monitor** — real-time packet rate, bytes/sec, protocol pie chart (WebSocket)
- [x] Panel: **Threat Feed** — streaming list of threats with severity, IP, attack type, timestamp
- [x] Panel: **Firewall Rules** — active rules table, rule history, manual override controls
- [x] Panel: **Zero Trust Audit** — login attempts, device verifications, RBAC events
- [x] Panel: **Model Performance** — per-model accuracy, precision, recall, F1
- [x] Panel: **Geo-IP Map** — world map of threat origins using MaxMind GeoLite2
- [x] Panel: **System Health** — CPU/memory/disk of WSL2 instance; per-module status indicators
- [x] Implement **alert system**: WebSocket in-app banners + SMTP email for Critical severity
- [x] Implement alert acknowledgment workflow with analyst notes
- [x] Support 4 severity levels: Critical, High, Medium, Low, Informational

### 4.3 Database Schema
- [x] Table: `flows` (flow_id, src_ip, dst_ip, src_port, dst_port, protocol, features_json, timestamp)
- [x] Table: `threat_events` (event_id, flow_id, attack_type, confidence, verdict, model_votes_json, timestamp)
- [x] Table: `firewall_rules` (rule_id, src_ip, action, reason, created_at, expires_at, created_by, revoked)
- [x] Table: `auth_events` (event_id, user_id, event_type, device_fingerprint, ip, status, timestamp)
- [x] Table: `users` (user_id, username, password_hash, role, created_at)
- [x] Add indexes on `src_ip` and `timestamp` for query performance

---

## Phase 5 — Testing & Final Submission (Weeks 23–24)

### 5.1 Unit Testing (Run inside WSL2)
- [x] Write `pytest` tests for feature extractor (validate against known PCAP files)
- [x] Write tests for each ML model's inference output (class labels and confidence types)
- [x] Write tests for firewall rule engine in **dry-run mode** with simulated `ThreatEvent` inputs
- [x] Write tests for JWT issuance, validation, and expiry
- [x] Write tests for RBAC permission enforcement per role

### 5.2 Integration Testing
- [x] Replay CICIDS2017 PCAP samples end-to-end inside WSL2; verify threat events appear in DB
- [x] Verify blocked IP appears in `sudo iptables -L` within 2 seconds of detection
- [x] Test WebSocket push from WSL2 backend to Windows browser: confirm < 2s latency
- [x] Test TTL rule expiry: confirm iptables rules auto-removed after TTL elapses

### 5.3 Attack Simulation (Inside WSL2 — Isolated)
- [x] Install attack tools inside WSL2: `sudo apt install -y hping3 nmap hydra`
- [x] Simulate **DDoS (SYN Flood)**: `sudo hping3 -S --flood -p 80 <target_ip>`; verify detection
- [x] Simulate **SSH Brute Force** using `Hydra` against a local test SSH server
- [x] Simulate **Port Scan**: `nmap -sS <target_ip>`; verify probe detection
- [x] Simulate **HTTP Flood** using a Python script against local FastAPI server
- [x] Run **Metasploit** inside WSL2 (`sudo apt install metasploit-framework`) in isolated loopback test

### 5.4 Performance Validation
- [x] Confirm classification **accuracy ≥ 95%** on CICIDS2017 test set
- [x] Confirm **precision ≥ 93%**, **recall ≥ 95%**, **F1 ≥ 94%**
- [x] Confirm **FPR ≤ 2%** for all models
- [x] Confirm **detection latency ≤ 2 seconds** (PCAP packet → iptables rule insert)
- [x] Confirm system handles **≥ 5,000 flows/second** without queue backlog

### 5.5 Documentation & Submission
- [x] Write API reference (endpoints, request/response schemas, auth requirements)
- [x] Write deployment guide covering WSL2 setup, venv, systemd-equivalent startup, and iptables permissions
- [x] Write ML model card (dataset sources, training config, performance metrics)
- [x] Generate feature importance charts for RF and XGBoost
- [x] Finalize B.Tech project report
- [x] Prepare demo: PCAP replay inside WSL2 → detection → dashboard on Windows browser → live iptables block
- [x] Create GitHub README with architecture diagram, WSL2 setup instructions, and screenshots

---

## Key Performance Targets (Quick Reference)

| Metric | Target |
|---|---|
| Classification Accuracy | ≥ 95% |
| Precision | ≥ 93% |
| Recall | ≥ 95% |
| F1-Score | ≥ 94% |
| False Positive Rate | ≤ 2% |
| Detection Latency | ≤ 2 seconds |
| Throughput | ≥ 5,000 flows/sec |
| Dashboard Refresh | < 2 seconds |

---

## WSL2 Quick-Reference Commands

| Task | Command |
|---|---|
| Start WSL2 | Open Windows Terminal → select Ubuntu-22.04 |
| Activate Python venv | `source ~/ai-ngfw/venv/bin/activate` |
| Run FastAPI server | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| Replay PCAP file | `python3 monitor.py --pcap pcaps/attack.pcap` |
| Check iptables rules | `sudo iptables -L -n -v` |
| Flush all iptables rules | `sudo iptables -F` (use carefully) |
| Start Suricata | `sudo suricata -c /etc/suricata/suricata.yaml -i eth0` |
| Access project from Windows | `\\wsl$\Ubuntu-22.04\home\<user>\ai-ngfw` |
| Open project in VS Code | Run `code .` from inside WSL2 terminal |
