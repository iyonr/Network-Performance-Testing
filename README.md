# 📦 Network Performance Testing Script (iperf3 + ping) — Syslog Style

A simple and reliable tool for network performance testing using `iperf3` and `ping`, designed for automated logging and cron-based scheduling.

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

📚 Learn more: [https://iperf.fr](https://iperf.fr)

---

## 🧱 Setup Architecture
      +-------------+              +---------------+
      |   Client    | <=====>     |    Server     |
      | (runs this  |   test via  | (runs iperf3   |
      |  script)    |   iperf3    |   in server    |
      +-------------+              +---------------+
---

## ⚙️ Setup Instructions

### 🔧 Server Setup (receiver):
```
sudo apt install iperf3
iperf3 -s
```
➡ The server will listen on TCP/UDP port 5201 by default.

🖥 Client Setup (runs the script):
```
sudo apt install iperf3
chmod +x iperf_test_v1.7_syslog_temp_debug.py
```
🚀 How to Run the Script (IPv4)
```
./iperf_test_v1.7_syslog_temp_debug.py --server <server_ipv4_address> --duration 60 --debug
```

Script Parameters:
--server : IP address of iperf3 server (IPv4 only, e.g., 192.168.1.100)
--duration : Test duration in seconds (choose: 60, 300, or 600)
--debug : (Optional) Show full raw output in terminal for troubleshooting

📂 Output & Logging Structure
```
/tmp/
├── ping_<timestamp>.log         # Raw ping output
├── iperf3_udp_<timestamp>.log   # Raw UDP test output
├── iperf3_tcp_<timestamp>.log   # Raw TCP test output

/var/log/iperf_tests/
└── iperf_summary.log            # Parsed one-line summary logs
```
Example Summary Log Output:
```
2025-03-24_05-45-53 STATUS=OK SERVER=192.168.1.100:5201 DURATION=60s LATENCY=178.853ms PING_LOSS=0% UDP_BW=707 Mbits/sec UDP_JITTER=0.020ms UDP_LOSS=0% TCP_BW=68.1 Mbits/sec
```
⏱ Automate with Cron (Optional)
Add cron job to run 4x a day:
```
crontab -e
```
Add entry like:
```
0 11,15,0,3 * * * /usr/bin/python3 /path/to/iperf_test_v1.7_syslog_temp_debug.py --server 192.168.1.100 --duration 60 >> /var/log/iperf_tests/cron.log 2>&1
```
(Optional) Clean up old logs:
```
0 4 * * * find /tmp -name "ping_*.log" -o -name "iperf3_*.log" -mtime +7 -delete
```
🛠 Troubleshooting Tips
Make sure iperf3 server is running and reachable.
Ensure firewall allows UDP/TCP port 5201.
Check directory permissions for /var/log/iperf_tests/.

💡 Ideas for Future Enhancements
-- Export to CSV
-- Email or webhook notifications
-- Grafana dashboard (via InfluxDB/Prometheus)
-- REST API integration

📄 License
MIT License — You’re free to modify, distribute, and use it.

📁 .gitignore
*.log
*.pyc
__pycache__/
/tmp/ping_*.log
/tmp/iperf3_udp_*.log
/tmp/iperf3_tcp_*.log
/var/log/iperf_tests/*.log
