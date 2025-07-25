# 📦 Network Performance Testing Script (iperf3 + ping) — Syslog Style

A simple and reliable tool for network performance testing using `iperf3` and `ping`, designed for automated logging, debug mode, and optional cleanup — suitable for Linux & macOS clients.

---

## 📖 What is iperf3?
`iperf3` is a powerful network testing tool used to measure:
- **Bandwidth (throughput)**
- **Jitter**
- **Packet loss**
- **Latency**

It uses **client-server architecture**:
- The **server** runs `iperf3 -s` and listens for incoming tests.
- The **client** initiates the test using `iperf3 -c <server-ip>`.

💼 Learn more: [https://iperf.fr](https://iperf.fr)

---

## 🧱 Setup Architecture
```
      +-------------+              +---------------+
      |   Client    | <=====>     |    Server     |
      | (runs this  |   test via  | (runs iperf3   |
      |  script)    |   iperf3    |   in server    |
      +-------------+              +---------------+
```

---

## ⚙️ Setup Instructions

### 🔧 Server Setup (receiver):
```bash
sudo apt install iperf3
iperf3 -s
```
➡ The server will listen on TCP/UDP port 5201 by default.

### 🖥 Client Setup (runs the script):
```bash
sudo apt install iperf3
chmod +x performance_test.py
```

---

## 🚀 How to Run the Script (IPv4)

```bash
python3 performance_test.py --server <server_ipv4_address> --duration 60 --port 5201 --udp-bandwidth 1000M --direction upload --os-mode Linux --debug
```

### Script Parameters:
- `--server` : IP address of iperf3 server (IPv4 only)
- `--duration` : Duration in seconds (`60`, `300`, `600`)
- `--port` : Optional, default `5201`
- `--udp-bandwidth` : Optional, default `1000M` (used only for UDP test)
- `--direction` : `upload` (default) or `download` for reverse test
- `--debug` : Show raw result output in terminal
- `--clean-tmp` : Remove all related `/tmp/` test files after execution
- `--os-mode` : Optional override for OS auto-detection (`Linux` or `MacOS`, case-insensitive)

---

## 📂 Output & Logging Structure

```
/tmp/
├── ping_<timestamp>.log         # Initial ping
├── ping_live_<timestamp>.log    # Ping during iperf
├── ping_post_<timestamp>.log    # Ping after iperf
├── iperf3_udp_<timestamp>.log   # Raw UDP test
├── iperf3_tcp_<timestamp>.log   # Raw TCP test

~/iperf_logs/ (or /var/log/iperf_tests if run as root)
└── iperf_summary.log            # Parsed single-line summary
```

### Example Summary Log:
```
2025-06-13_16-05-29 STATUS=OK SERVER=10.184.0.2:5201 DURATION=60s LATENCY=32.415ms PING_LOSS=0% LIVE_LAT=35.2ms LIVE_LOSS=1% POST_LAT=30.5ms POST_LOSS=0% UDP_BW=88.8 Mbits/sec UDP_JITTER=0.200ms UDP_LOSS=90% TCP_BW=39.8 Mbits/sec
```

---

## ✅ Supported Use Cases

### 1. Basic Upload Bandwidth Test
```bash
python3 performance_test.py --server <server_ip>
```

### 2. Basic Download Bandwidth Test
```bash
python3 performance_test.py --server <server_ip> --direction download
```

### 3. Longer Duration Testing
```bash
python3 performance_test.py --server <server_ip> --duration 300
```

### 4. Custom UDP Bandwidth Test
```bash
python3 performance_test.py --server <server_ip> --udp-bandwidth 500M
```

### 5. Debug Mode for Investigations
```bash
python3 performance_test.py --server <server_ip> --debug
```

### 6. Manual OS Override
```bash
python3 performance_test.py --server <server_ip> --os-mode MacOS
```

### 7. Non-root Logging
```bash
python3 performance_test.py --server <server_ip>
```
(Logs will be written to `~/iperf_logs/` automatically.)

### 8. Full Upload Test with Custom Duration, Bandwidth, and Debug
```bash
python3 performance_test.py --server <server_ip> --duration 300 --udp-bandwidth 500M --direction upload --port 5201 --debug
```

### 9. Full Download Test with Custom Duration, Bandwidth, and Debug
```bash
python3 performance_test.py --server <server_ip> --duration 300 --udp-bandwidth 500M --direction download --port 5201 --debug
```

### 10. Upload Test with Cleanup After Completion
```bash
python3 performance_test.py --server <server_ip> --duration 60 --direction upload --clean-tmp
```

---

## 🌐 Use Case: Over VPN/IPsec Tunnel

Example:
```
MacBook → LAN → FortiGate → IPsec → GCP Instance
```

Useful for verifying advanced tunneling stability before deployment to clients.

---

## 🧪 How UDP vs TCP Metrics Differ

- **UDP Loss (%):** Packet loss due to network congestion or MTU mismatch.
- **UDP Jitter (ms):** Variability in packet delay; important for VoIP/Video.
- **UDP Bandwidth:** Receiver-side bandwidth (may be limited by loss).
- **TCP Bandwidth:** Effective throughput measured via TCP acknowledgments.

---

## ⏱ Automate with Cron (Optional)

Run 4 times a day:
```bash
crontab -e
```

Example:
```cron
0 0,6,12,18 * * * /usr/bin/python3 /path/to/performance_test.py --server 192.168.1.100 --duration 60 >> ~/iperf_logs/cron.log 2>&1
```

Optional daily cleanup:
```cron
0 4 * * * find /tmp -name "ping_*.log" -o -name "iperf3_*.log" -mtime +7 -delete
```

---

## 💡 Ideas for Future Enhancements
- Export to CSV/JSON
- Slack/email alerts
- REST API or webhook
- Grafana integration via InfluxDB

---

## 📄 License
MIT License — Free to use, modify, distribute.

---

## 📁 .gitignore
```gitignore
*.log
*.pyc
__pycache__/
/tmp/ping_*.log
/tmp/ping_live_*.log
/tmp/ping_post_*.log
/tmp/iperf3_udp_*.log
/tmp/iperf3_tcp_*.log
/var/log/iperf_tests/*.log
~/iperf_logs/*.log
```