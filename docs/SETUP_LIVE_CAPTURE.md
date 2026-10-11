# Setting Up Live Network Capture in WSL2

## Issue: setcap doesn't work on symlinks

The error you're seeing happens because `/usr/bin/python3` is a symbolic link, not the actual binary.

## Solution: Multiple Options

### **Option 1: Use sudo (Easiest)**

Instead of setting capabilities, just run the monitor with sudo:

```bash
cd /mnt/c/Users/neera/OneDrive/Desktop/projects/AZTF2
sudo python3 monitor.py --live
```

This will:
- Capture real network packets
- Run ML detection
- Work immediately without setcap

---

### **Option 2: Find Real Python Binary**

Set capabilities on the actual binary, not the symlink:

```bash
# Find the real python3 binary
readlink -f $(which python3)
# Example output: /usr/bin/python3.10

# Set capabilities on the real binary
sudo setcap cap_net_raw,cap_net_admin+eip /usr/bin/python3.10

# Verify it worked
getcap /usr/bin/python3.10
# Should show: /usr/bin/python3.10 = cap_net_admin,cap_net_raw+eip

# Now run without sudo
python3 monitor.py --live
```

---

### **Option 3: Create Virtual Environment in WSL2**

Best practice for production:

```bash
# Install venv if not already installed
sudo apt update
sudo apt install python3.10-venv

# Create virtual environment
cd /mnt/c/Users/neera/OneDrive/Desktop/projects/AZTF2
python3 -m venv venv_wsl

# Activate it
source venv_wsl/bin/activate

# Install dependencies
pip install scapy scikit-learn xgboost tensorflow pandas numpy fastapi uvicorn pyjwt bcrypt python-dotenv psutil websockets imbalanced-learn joblib

# Set capabilities on venv python
sudo setcap cap_net_raw,cap_net_admin+eip venv_wsl/bin/python3

# Run monitor
venv_wsl/bin/python3 monitor.py --live
```

---

## Quick Test Commands

### Test 1: Check if Scapy can see network interfaces
```bash
sudo python3 -c "from scapy.all import get_if_list; print(get_if_list())"
```

Expected output:
```
['lo', 'eth0', 'docker0', ...]
```

### Test 2: Capture 5 packets (test only)
```bash
sudo python3 -c "from scapy.all import sniff; pkts = sniff(count=5, iface='eth0'); print(f'Captured {len(pkts)} packets')"
```

Expected output:
```
Captured 5 packets
```

---

## Running Live Monitor

Once capabilities are set OR using sudo:

### For Testing (won't block IPs):
```bash
sudo python3 monitor.py --live
```

### For Production (will execute iptables):
```bash
sudo python3 monitor.py --live --enforce
```

### Check what's happening:
```bash
# In another terminal, watch iptables rules
watch -n 1 sudo iptables -L -n -v
```

---

## Important: WSL2 Network Interface

WSL2 uses a virtual network interface. Find yours:

```bash
ip addr show
```

Look for something like:
```
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    inet 172.x.x.x/20 brd 172.x.x.x scope global eth0
```

Your interface is probably `eth0`. The monitor will use this by default.

---

## Troubleshooting

### Error: "Permission denied" even with sudo
```bash
# Check if you're actually running as root
sudo whoami
# Should output: root

# Try with explicit sudo -E to preserve environment
sudo -E python3 monitor.py --live
```

### Error: "No module named 'scapy'"
```bash
# Install in system Python (with sudo)
sudo apt install python3-pip
sudo pip3 install scapy scikit-learn xgboost

# Or install all dependencies
sudo pip3 install -r requirements.txt
```

### Error: "Interface eth0 does not exist"
```bash
# List available interfaces
ip link show

# Use the one that's UP (usually eth0 or ens33)
# Edit monitor.py line ~420 to change interface:
# sniff(iface="YOUR_INTERFACE", prn=process_packet, store=0)
```

### Error: "Models not found"
```bash
# The models are on Windows filesystem, accessible via /mnt/c/
# You're already in the right directory, so this should work

# Verify models exist
ls -lh models/
```

---

## Security Considerations

### Firewall Mode: Dry-Run vs Enforce

**Dry-Run (Default - Safe):**
```bash
sudo python3 monitor.py --live
```
- Logs firewall rules to database
- Does NOT execute iptables commands
- Safe for testing

**Enforce (Production - Caution):**
```bash
sudo python3 monitor.py --live --enforce
```
- Executes REAL iptables rules
- WILL block IPs on your network
- Can disrupt connectivity if misconfigured
- Use only after thorough testing

### Whitelist Important IPs

Before enabling --enforce mode, edit `firewall.py`:

```python
# firewall.py - Line ~15
WHITELIST = [
    '127.0.0.1',           # Localhost
    '192.168.1.0/24',      # Your local network
    '8.8.8.8',             # DNS servers
    '1.1.1.1',
    # Add your important servers here
]
```

---

## Performance Expectations

### Live Capture Performance

```
Low Traffic Network (Home):
├─ 10-100 flows/second
├─ CPU: 10-20%
└─ Memory: 2-3 GB

Medium Traffic (Office):
├─ 100-1000 flows/second
├─ CPU: 30-50%
└─ Memory: 3-4 GB

High Traffic (Production):
├─ 1000+ flows/second
├─ CPU: 60-80%
└─ Memory: 4-6 GB
└─ Consider hardware acceleration
```

---

## Running Both API and Monitor

### Terminal 1: Start API Server (Windows)
```powershell
# In Windows PowerShell
cd C:\Users\neera\OneDrive\Desktop\projects\AZTF2
py -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### Terminal 2: Start Live Monitor (WSL2)
```bash
# In WSL2 Ubuntu
cd /mnt/c/Users/neera/OneDrive/Desktop/projects/AZTF2
sudo python3 monitor.py --live
```

### Access Dashboard
Open browser: http://localhost:8000/dashboard/index.html

Now you'll see:
- ✅ Real network packets being captured
- ✅ Real ML detection
- ✅ Real-time dashboard updates
- ✅ True live threat detection system

---

## Recommended: Start with Dry-Run

```bash
# Step 1: Test with 10 packets only
sudo python3 -c "from scapy.all import sniff; sniff(count=10, iface='eth0')"

# Step 2: Run monitor in dry-run mode
sudo python3 monitor.py --live

# Step 3: Watch the output, verify models load correctly
# Expected: "Models loaded successfully"
# Expected: "Starting network traffic monitoring..."

# Step 4: Open dashboard, verify you see real detections

# Step 5: Only after thorough testing, enable --enforce
sudo python3 monitor.py --live --enforce
```

---

## Alternative: PCAP Replay (Safer than Live)

If you want to test with real attack data without risking your network:

```bash
# Download sample attack PCAP
wget https://www.malware-traffic-analysis.net/2017/06/02/2017-06-02-traffic-analysis-exercise.pcap.zip
unzip 2017-06-02-traffic-analysis-exercise.pcap.zip

# Replay it through the system
python3 monitor.py --pcap 2017-06-02-traffic-analysis-exercise.pcap

# This will:
# - Use real attack packets
# - Run ML detection
# - Safe (no live network)
# - Repeatable for demos
```

---

## Summary

**Simplest solution for you right now:**

```bash
# Just use sudo, forget about setcap
cd /mnt/c/Users/neera/OneDrive/Desktop/projects/AZTF2
sudo python3 monitor.py --live

# This will work immediately!
```

The `setcap` is just an optimization to avoid typing `sudo` every time. For testing and demos, using `sudo` directly is perfectly fine.
