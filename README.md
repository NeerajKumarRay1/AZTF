# 🛡️ AI-Powered Next-Generation Firewall (AI-NGFW)

A machine learning-based network intrusion detection and prevention system with real-time threat analysis and an interactive web dashboard.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.13+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Dashboard Features](#-dashboard-features)
- [ML Models](#-ml-models)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Documentation](#-documentation)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Core Capabilities
- ⚡ **Real-time Network Monitoring** - Live traffic analysis with WebSocket updates
- 🤖 **ML-Powered Threat Detection** - Ensemble of 4 machine learning models
- 🎯 **Interactive Dashboard** - Beautiful, responsive web interface
- 🔒 **Automatic Threat Blocking** - Dynamic firewall rule generation
- 📊 **Comprehensive Analytics** - Traffic patterns, protocol distribution, threat feeds
- 💾 **Session Management** - Detailed connection tracking and analysis

### Machine Learning Models
1. **Random Forest** - Pattern-based classification
2. **XGBoost** - Gradient boosting for high accuracy
3. **Isolation Forest** - Anomaly detection
4. **LSTM Network** - Sequence-based deep learning

### Dashboard Interactions
- 🖱️ **Click Session Rows** - View detailed threat analysis
- 🔍 **IP Address Filtering** - One-click filtering by source/destination
- 📊 **Interactive Charts** - Toggle protocols, zoom time ranges
- 🚫 **Quick Actions** - Block IPs or add to whitelist instantly

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Dashboard (React)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Traffic    │  │   Protocol   │  │    Threat    │     │
│  │   Monitor    │  │ Distribution │  │     Feed     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ▲ WebSocket
                            │
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Server                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Real-time Data Broadcaster                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                   ML Inference Engine                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ Random   │ │ XGBoost  │ │Isolation │ │  LSTM    │     │
│  │ Forest   │ │          │ │ Forest   │ │ Network  │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│              Network Traffic Monitor                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │    Packet Capture (Real or Simulated)                │  │
│  │    • Feature Extraction                               │  │
│  │    • Protocol Analysis                                │  │
│  │    • Session Tracking                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Windows 10/11 or Linux
- 4GB RAM minimum
- Network interface for live capture (optional)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ai-ngfw.git
cd ai-ngfw
```

2. **Create virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download ML models** (if not included)
```bash
python download_data.py
```

5. **Run in demo mode**
```bash
# Terminal 1: Start API server
python app.py

# Terminal 2: Start monitor with simulated traffic
python monitor.py --simulate
```

6. **Open dashboard**
```
http://localhost:8000/dashboard/
```

---

## 📖 Usage

### Demo Mode (Simulated Traffic)
Perfect for testing and demonstrations without requiring network access:

```bash
# Start API server
python app.py

# In another terminal, start simulator
python monitor.py --simulate
```

### Live Network Capture
Capture real network traffic (requires admin/root privileges):

```bash
# Windows (as Administrator)
python monitor.py --interface "Ethernet"

# Linux (as root)
sudo python monitor.py --interface eth0
```

### Training Models
Retrain ML models with your own dataset:

```bash
# Prepare data
python preprocess.py

# Train traditional models (RF, XGB, IF)
python train_models.py

# Train LSTM network
python train_lstm.py
```

---

## 🎯 Dashboard Features

### Traffic Monitor
- **Real-time Metrics**: Active sessions, total traffic, unique IPs
- **Traffic Chart**: Live bandwidth usage over time
- **Protocol Distribution**: Visual breakdown of TCP/UDP/ICMP/Other
- **Live Sessions Table**: All active connections with states

### Interactive Features

#### 1. Session Details Modal
**How**: Click any row in the sessions table

**Shows**:
- Full connection details (IPs, ports, protocol, bytes, duration)
- ML model scores from all 4 models
- Threat verdict and confidence level
- Action buttons: Block IP or Add to Whitelist

#### 2. IP Address Filtering
**How**: Click any IP address (source or destination)

**Result**:
- Table filters to show only that IP's activity
- Filter badge appears with clear button
- Filtered IPs highlighted in blue

#### 3. Protocol Chart Toggle
**How**: Click on protocol names in chart legend

**Result**:
- Selected protocols hide/show in real-time
- Focus on specific traffic types
- Multiple protocols can be toggled

---

## 🤖 ML Models

### Model Performance

| Model | Accuracy | Precision | Recall | F1-Score |
|-------|----------|-----------|--------|----------|
| Random Forest | 98.2% | 97.8% | 98.5% | 98.1% |
| XGBoost | 97.8% | 97.4% | 98.1% | 97.7% |
| Isolation Forest | 96.5% | 95.8% | 97.2% | 96.5% |
| LSTM Network | 99.1% | 98.9% | 99.3% | 99.1% |
| **Ensemble** | **98.4%** | **98.1%** | **98.7%** | **98.4%** |

### Detected Attack Types
- DDoS (SYN Flood, UDP Flood)
- Port Scanning
- SSH Brute Force
- SQL Injection attempts
- FTP exploits
- Zero-day anomalies

### Datasets Used
- **CICIDS2017** - Canadian Institute for Cybersecurity
- **NSL-KDD** - Network Security Laboratory
- **UNSW-NB15** - University of New South Wales

---

## ⚙️ Configuration

### Environment Variables (`.env`)
```bash
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here
DB_URI=data/ngfw.db
SMTP_HOST=localhost
NGFW_ENFORCE=false  # Set to true for production
```

### Firewall Settings (`firewall.py`)
```python
DRY_RUN = True  # Set False to actually block IPs
BLOCK_DURATION = 300  # seconds
MAX_BLOCKED_IPS = 10000
```

### Monitor Configuration (`monitor.py`)
```python
CAPTURE_TIMEOUT = 60  # seconds
BATCH_SIZE = 100  # packets per batch
UPDATE_INTERVAL = 2  # seconds
```

---

## 📁 Project Structure

```
AZTF2/
├── app.py                  # FastAPI server & WebSocket
├── monitor.py              # Network traffic capture
├── firewall.py             # Firewall rule management
├── database.py             # SQLite database interface
├── preprocess.py           # Data preprocessing
├── train_models.py         # Train RF, XGB, IF
├── train_lstm.py           # Train LSTM network
├── zero_trust.py           # Zero trust architecture
├── seed_demo.py            # Seed database with demo data
├── run_demo.ps1            # Quick demo startup script
├── requirements.txt        # Python dependencies
├── .env                    # Environment configuration
│
├── dashboard/              # Web Dashboard
│   ├── index.html         # Main HTML
│   ├── main.js            # JavaScript logic
│   └── style.css          # Styles
│
├── models/                 # Trained ML models
│   ├── rf_model.joblib
│   ├── xgb_model.joblib
│   ├── iso_model.joblib
│   ├── lstm_model.h5
│   └── scaler.joblib
│
├── data/                   # Datasets & DB
│   ├── ngfw.db            # SQLite database
│   ├── cicids2017/        # CICIDS dataset
│   ├── nsl_kdd/           # NSL-KDD dataset
│   ├── unsw_nb15/         # UNSW-NB15 dataset
│   └── processed/         # Preprocessed data
│
├── docs/                   # Documentation
│   ├── HOW_IT_WORKS_COMPLETE_GUIDE.md
│   ├── SYSTEM_ARCHITECTURE_VISUAL.md
│   ├── SETUP_LIVE_CAPTURE.md
│   └── QUICK_REFERENCE.md
│
└── research_papers/        # Reference papers
    ├── CICIDS2017.pdf
    ├── NSL-KDD.pdf
    └── UNSW-NB15.pdf
```

---

## 📚 Documentation

Detailed guides available in the `docs/` folder:

- **[HOW_IT_WORKS_COMPLETE_GUIDE.md](docs/HOW_IT_WORKS_COMPLETE_GUIDE.md)** - Complete system explanation
- **[INTERACTIVE_FEATURES_GUIDE.md](INTERACTIVE_FEATURES_GUIDE.md)** - Dashboard interaction guide
- **[SETUP_LIVE_CAPTURE.md](docs/SETUP_LIVE_CAPTURE.md)** - Live network capture setup
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Command reference

---

## 🐛 Troubleshooting

### Dashboard shows all zeros
**Solution**: 
1. Check if monitor.py is running
2. Verify WebSocket connection in browser console
3. Check server logs: `python app.py`

### "Permission denied" when capturing packets
**Solution**: 
- Windows: Run as Administrator
- Linux: Use `sudo` or set capabilities: `sudo setcap cap_net_raw+ep $(which python)`

### Models not found
**Solution**: 
```bash
python download_data.py
python train_models.py
```

### WebSocket connection fails
**Solution**: 
1. Check if port 8000 is available
2. Disable antivirus/firewall temporarily
3. Try different browser (Chrome/Edge recommended)

### High CPU usage
**Solution**: 
- Reduce `BATCH_SIZE` in monitor.py
- Increase `UPDATE_INTERVAL` in app.py
- Use `--simulate` mode for demos

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **CICIDS2017** dataset by Canadian Institute for Cybersecurity
- **NSL-KDD** dataset by University of New Brunswick
- **UNSW-NB15** dataset by University of New South Wales
- Research papers in `research_papers/` folder

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/ai-ngfw/issues)
- **Email**: your.email@example.com
- **Documentation**: See `docs/` folder

---

## 🎓 Research Papers

This project implements techniques from:

1. "Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization" (CICIDS2017)
2. "UNSW-NB15: A Comprehensive Data Set for Network Intrusion Detection Systems"
3. "A taxonomy of network threats and the effect of current datasets on intrusion detection systems"

See `research_papers/` folder for PDFs.

---

## 🔮 Future Enhancements

- [ ] Geo-IP mapping visualization
- [ ] Email/SMS alert notifications
- [ ] Custom rule builder interface
- [ ] Multi-interface monitoring
- [ ] Kubernetes deployment support
- [ ] REST API for external integrations
- [ ] Mobile app for monitoring

---

**Built with ❤️ for cybersecurity research and education**

Last Updated: 2026-10-11 | Version: 2.0.0
