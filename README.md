# Network-Performance-Testing
A simple, reliable tool to perform network performance testing using iperf3 and ping, tailored for automated logging and cron-based scheduled runs.
📖 What is iperf3?

iperf3 is a powerful network testing tool designed to measure bandwidth, jitter, loss, and latency between two systems using TCP or UDP traffic.

It consists of a client and a server.

It is widely used to benchmark and verify network performance and SLA.

Learn more: https://iperf.fr

🧱 Setup Architecture

      +-------------+              +---------------+
      |   Client    | <=====>     |    Server     |
      | (runs this  |   test via  | (runs iperf3   |
      |  script)    |   iperf3    |   in server    |
      +-------------+              +---------------+

🔧 On the Server (receiver):

sudo apt install iperf3
iperf3 -s

Keeps listening on TCP/UDP port 5201 by default.

🖥 On the Client (runs the script):

sudo apt install iperf3
chmod +x iperf_test_v1.7_syslog_temp_debug.py

🚀 How to Run (IPv4)

./iperf_test_v1.7_syslog_temp_debug.py --server <server_ipv4_address> --duration 60 --debug

Script Parameters:

--server : IP address of iperf3 server (IPv4 format, e.g., 192.168.1.100)

--duration : Duration of test in seconds (60, 300, or 600)

--debug : (Optional) Enable raw output logs in terminal for troubleshooting

📂 File Output & Logging

/tmp/
├─ ping_<timestamp>.log         # raw ping result
├─ iperf3_udp_<timestamp>.log   # raw UDP test result
├─ iperf3_tcp_<timestamp>.log   # raw TCP test result

/var/log/iperf_tests/
└─ iperf_summary.log            # system-log-style test summary

Example Summary Log:

2025-03-24_05-45-53 STATUS=OK SERVER=192.168.1.100:5201 DURATION=60s LATENCY=178.853ms PING_LOSS=0% UDP_BW=707 Mbits/sec UDP_JITTER=0.020ms UDP_LOSS=0% TCP_BW=68.1 Mbits/sec

⏱ Schedule Test Using Cron (Optional)

crontab -e

Add entry like:

0 11,15,0,3 * * * /usr/bin/python3 /path/to/iperf_test_v1.7_syslog_temp_debug.py --server 192.168.1.100 --duration 60 >> /var/log/iperf_tests/cron.log 2>&1

Optional Log Cleanup:

0 4 * * * find /tmp -name "ping_*.log" -o -name "iperf3_*.log" -mtime +7 -delete

📘 Troubleshooting Notes

Ensure iperf3 server is running and reachable (ping works)

Make sure UDP traffic is not blocked by firewall (port 5201)

Check permissions if /var/log/iperf_tests/ is not writable

💡 Ideas for Enhancement

CSV output support

Email alert/report

Web dashboard or Grafana/InfluxDB exporter

REST API integration

🛠 License

MIT License (customizable)

📁 .gitignore (recommended)

*.log
*.pyc
__pycache__/
/tmp/ping_*.log
/tmp/iperf3_udp_*.log
/tmp/iperf3_tcp_*.log
/var/log/iperf_tests/*.log

