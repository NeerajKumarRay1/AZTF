# Complete Project Context for ChatGPT

Copy and paste this entire message to ChatGPT when you need help:

---

## Project Overview

I have an **AI-Driven Next-Generation Firewall (NGFW)** project that uses machine learning for real-time network threat detection. The system is currently working with these components:

### Current Status
- ✅ 4 trained ML models (Random Forest, XGBoost, Isolation Forest, LSTM)
- ✅ FastAPI backend running on Windows (port 8000)
- ✅ Real-time dashboard with WebSocket updates
- ✅ SQLite database with threat events
- ✅ Zero Trust authentication (JWT + RBAC)
- ⚠️ Currently using **simulated network traffic** (not real packets)
- 🎯 **Goal**: Switch to live network packet capture using WSL2

### Technology Stack
- **OS**: Windows 11 + WSL2 (Ubuntu 22.04)
- **Language**: Python 3.13
- **ML**: scikit-learn, XGBoost, TensorFlow/Keras
- **Network**: Scapy (packet capture)
- **API**: FastAPI + uvicorn
- **Database**: SQLite
- **Frontend**: HTML5 + JavaScript + Chart.js + Leaflet

### Project Structure
```
AZTF2/
├── app.py              (FastAPI server - runs on Windows)
├── monitor.py          (Traffic monitor + ML detection)
├── firewall.py         (Firewall rule management)
├── database.py         (SQLite operations)
├── zero_trust.py       (JWT authentication)
├── models/             (Trained ML models)
│   ├── rf_model.joblib
│   ├── xgb_model.joblib
│   ├── iso_model.joblib
│   ├── lstm_model.h5
│   └── scaler.joblib
├── data/
│   ├── ngfw.db         (SQLite database)
│   └── processed/      (Preprocessed datasets)
├── dashboard/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── documentation/      (Research papers, guides)
```

---

## Current Issue

I'm trying to enable **live network packet capture** in WSL2 but getting this error:

```bash
neeraj@neeraj:/mnt/c/Users/neera/OneDrive/Desktop/projects/AZTF2$ sudo setcap cap_net_raw,cap_net_admin+eip $(which python3)
Invalid file '/usr/bin/python3' for capability operation
```

**Problem**: `/usr/bin/python3` is a symlink, and `setcap` doesn't work on symlinks in WSL2.

---

## What's Currently Running

### Terminal 1 (Windows PowerShell):
```powershell
PS C:\Users\neera\OneDrive\Desktop\projects\AZTF2> py -m uvicorn app:app --host 0.0.0.0 --port 8000
# FastAPI server for dashboard and API endpoints
```

### Terminal 2 (Windows PowerShell):
```powershell
PS C:\Users\neera\OneDrive\Desktop\projects\AZTF2> py monitor.py --simulate
# ML threat detection with simulated traffic
```

### Dashboard Access:
- URL: http://localhost:8000/dashboard/index.html
- Login: admin / password123

---

## System Architecture

```
Network Packets (via Scapy)
    ↓
Flow Aggregation (7 features extracted)
    ↓
StandardScaler (normalization)
    ↓
ML Ensemble Models (parallel inference)
├─ Random Forest (30% weight)
├─ XGBoost (35% weight)
├─ Isolation Forest (20% weight)
└─ LSTM (15% weight)
    ↓
Weighted Voting (threshold: 0.60)
    ↓
Verdict: BENIGN or MALICIOUS
    ↓
If MALICIOUS: Block IP with TTL
    ↓
Database Logging + Dashboard Update
```

---

## Monitor.py Modes

The `monitor.py` script supports three modes:

### 1. Simulation Mode (Current)
```bash
py monitor.py --simulate
```
- Generates synthetic network traffic
- ML models make real predictions
- Safe for demos

### 2. PCAP Replay Mode
```bash
py monitor.py --pcap samples/attack.pcap
```
- Replays recorded packet captures
- Uses real attack data

### 3. Live Capture Mode (Goal)
```bash
sudo python3 monitor.py --live
```
- Captures real network packets
- Requires root/admin permissions
- Need to solve the setcap issue

---

## ML Models Performance

Trained on 400K samples from 3 datasets (CICIDS2017, UNSW-NB15, NSL-KDD):

| Model | Accuracy | File Size | Purpose |
|-------|----------|-----------|---------|
| Random Forest | 96.2% | 74.4 MB | Feature importance |
| XGBoost | 97.2% | 1.1 MB | Best accuracy |
| Isolation Forest | 91.4% | 646 KB | Zero-day detection |
| LSTM | 95.8% | (h5 file) | Temporal patterns |
| **Ensemble** | **97.8%** | - | Combined prediction |

---

## What I Need Help With

[Describe your specific question/issue here]

Examples:
- "How do I fix the setcap error in WSL2 to capture live packets?"
- "How can I improve the false positive rate in my ML models?"
- "How do I deploy this to a production server?"
- "How can I add email alerts when threats are detected?"
- "How do I create a systemd service for auto-start?"

---

## Additional Context

### Files You Should Know About:

**monitor.py** (main detection engine):
- Lines 1-100: Imports and model loading
- Lines 100-200: Flow class and feature extraction
- Lines 200-300: ML prediction and ensemble voting
- Lines 300-400: Firewall integration
- Lines 400+: Main execution (simulation/PCAP/live modes)

**app.py** (FastAPI backend):
- REST API endpoints: /auth/login, /threats, /rules
- WebSocket broadcaster (updates every 2 seconds)
- JWT authentication middleware

**firewall.py**:
- IP blocking with iptables (dry-run mode by default)
- TTL-based auto-expiry (300 seconds default)
- Whitelist checking

**database.py**:
- SQLite schema: flows, threat_events, firewall_rules, users, auth_events
- Helper functions for logging

### Important Configuration

**Confidence Threshold**: 0.60 (monitor.py line ~250)
- Lower = more sensitive, more false positives
- Higher = less sensitive, fewer blocks

**Ensemble Weights**: (monitor.py line ~260)
```python
RF: 0.30, XGBoost: 0.35, IF: 0.20, LSTM: 0.15
```

**Block Duration**: 300 seconds (firewall.py line ~25)

**Whitelist**: (firewall.py line ~15)
```python
['127.0.0.1', '10.0.0.0/8', '192.168.0.0/16']
```

---

## Environment Details

- **Windows Version**: Windows 11
- **WSL2 Version**: Ubuntu 22.04
- **Python Version**: 3.13 (Windows), 3.10 (WSL2)
- **Working Directory**: `/mnt/c/Users/neera/OneDrive/Desktop/projects/AZTF2`

### Installed Python Packages:
```
scikit-learn==1.9.1
xgboost==2.0.3
tensorflow==2.14.0
pandas==2.0.3
numpy==1.24.3
scapy==2.5.0
fastapi==0.104.1
uvicorn==0.24.0
pyjwt==2.8.0
bcrypt==4.1.0
```

---

## Expected Behavior

When I run `sudo python3 monitor.py --live` in WSL2, it should:

1. Capture real network packets from eth0 interface
2. Extract 7 features per flow (duration, protocol, src_bytes, dst_bytes, src_pkts, dst_pkts, rate)
3. Normalize features using StandardScaler
4. Run through 4 ML models in parallel
5. Calculate weighted ensemble score
6. If score ≥ 0.60: classify as MALICIOUS and log to database
7. If confidence ≥ 0.90: block IP with iptables (if --enforce flag used)
8. Update dashboard via WebSocket every 2 seconds

---

## Documentation Available

I have comprehensive documentation in these files:
- `AI_NGFW_Research_Paper_Complete.md` (45-page research paper)
- `HOW_IT_WORKS_COMPLETE_GUIDE.md` (detailed technical explanation)
- `QUICK_REFERENCE.md` (commands and troubleshooting)
- `SYSTEM_ARCHITECTURE_VISUAL.md` (visual diagrams)

---

## My Question

[Write your specific question here]

---

## Additional Notes

- The project is for my B.Tech final year research paper
- Dashboard is fully functional with real-time updates
- ML models are trained and working (97.8% accuracy)
- Just need to switch from simulation to live capture
- Prefer solutions that work in WSL2 (Ubuntu on Windows)
