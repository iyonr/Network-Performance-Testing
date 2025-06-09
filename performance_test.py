#!/usr/bin/env python3
# =====================================================
# Author       : Marion Renaldo Rotensulu
# Version      : v2.0
# Description  : Custom Performance test
# Log File     : /var/log/iperf_tests/iperf_summary.log (fallback: $HOME/.iperf_tests/)
# Last Updated : 2025-06-09
# Changelog    :
#   - v1.0 Basic summary output
#   - v1.1 Status check & debug output
#   - v1.2 Syslog-style one-line logging
#   - v1.3 live terminal output + debug mode
#   - v1.4 Added raw output capture in /tmp before parsing
#   - v1.5 Fixed regex parsing for UDP/TCP final summary lines (receiver block)
#   - v1.6
#       * Fixed UDP summary parsing (receiver line only)
#       * Improved jitter/loss regex extraction accuracy
#       * Supported both float and integer UDP bandwidth formats
#
#   - v1.7
#       * Refined UDP bandwidth regex for flexible numeric formats
#       * Graceful handling of missing receiver block
#       * Expanded debug output for UDP/TCP parsing visibility
#
#   - v1.8 (experimental)
#       * Introduced --direction flag for upload/download (via iperf3 -R)
#       * Early work on bidirectional mode (disabled)
#       * Improved temp file naming to avoid conflicts
#
#   - v1.9
#       * Added --port argument to allow custom iperf3 port usage
#       * Improved argparse help descriptions
#       * Updated documentation and README accordingly
#
#   - v2.0
#       * Auto-detect OS (Linux/macOS) and apply correct ping regex
#       * Added non-root log path fallback to ~/.iperf_tests/
#       * Made script safe to run as non-privileged user
#       * Restructured log directory logic and error handling
# =====================================================

import subprocess
import datetime
import os
import argparse
import re
import socket
import platform

# Argument Parser
parser = argparse.ArgumentParser(description="Network Test Summary Script (Cross-platform + Syslog Style + Fallback Logs)")
parser.add_argument("--duration", type=int, choices=[60, 300, 600], default=60,
                    help="Test duration in seconds")
parser.add_argument("--server", type=str, required=True, help="IP address of iperf3 server")
parser.add_argument("--port", type=int, default=5201, help="iperf3 server port")
parser.add_argument("--direction", type=str, choices=["upload", "download"], default="upload",
                    help="Traffic direction (upload or download)")
parser.add_argument("--debug", action="store_true", help="Enable debug mode with raw outputs")
args = parser.parse_args()

server_ip = args.server
port = args.port
duration = args.duration
direction = args.direction
debug_mode = args.debug

# Detect platform
current_os = platform.system()

# Directory setup
default_log_dir = "/var/log/iperf_tests"
fallback_log_dir = os.path.join(os.path.expanduser("~"), ".iperf_tests")
log_dir = default_log_dir if os.access("/var/log", os.W_OK) else fallback_log_dir
os.makedirs(log_dir, exist_ok=True)
tmp_dir = "/tmp"

# Timestamps and log paths
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
summary_log_file = os.path.join(log_dir, "iperf_summary.log")
ping_tmp = os.path.join(tmp_dir, f"ping_{timestamp}.log")
udp_tmp = os.path.join(tmp_dir, f"iperf3_udp_{timestamp}.log")
tcp_tmp = os.path.join(tmp_dir, f"iperf3_tcp_{timestamp}.log")

# Helper function
def run_and_save(cmd, tmpfile):
    try:
        with open(tmpfile, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True, timeout=duration + 30)
        with open(tmpfile, "r") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"

# Check reachability
ping_status = False
try:
    socket.gethostbyname(server_ip)
    ping_check = subprocess.run(["ping", "-c", "3", server_ip], capture_output=True, text=True)
    if "0% packet loss" in ping_check.stdout or "1% packet loss" in ping_check.stdout:
        ping_status = True
except Exception:
    ping_status = False

# Initialize result variables
status = "FAIL"
latency_avg = "-"
packet_loss = "-"
udp_bw = udp_jitter = udp_ploss = "-"
tcp_bw = "-"

if ping_status:
    status = "OK"
    print("[INFO] Running latency test (ping)...")
    ping_output = run_and_save(["ping", "-c", str(duration // 2), server_ip], ping_tmp)

    # OS-aware regex
    if current_os == "Linux":
        match = re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+", ping_output)
    elif current_os == "Darwin":  # macOS
        match = re.search(r"(?:rtt|round-trip).* = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+", ping_output)
    else:
        match = None

    if match:
        latency_avg = match.group(1) + "ms"

    ploss_match = re.search(r"(\d+)% packet loss", ping_output)
    if ploss_match:
        packet_loss = ploss_match.group(1) + "%"

    print("[INFO] Running UDP test (jitter, packet loss, bandwidth)...")
    udp_args = ["iperf3", "-c", server_ip, "-p", str(port), "-u", "-t", str(duration), "-b", "1000M"]
    if direction == "download":
        udp_args.append("-R")
    udp_output = run_and_save(udp_args, udp_tmp)

    udp_receiver_line = ""
    for line in udp_output.splitlines():
        if "receiver" in line and "bits/sec" in line:
            udp_receiver_line = line.strip()

    if udp_receiver_line:
        udp_bw_match = re.search(r"(\d+(?:\.\d+)? \wbits/sec)", udp_receiver_line)
        if udp_bw_match:
            udp_bw = udp_bw_match.group(1)

        udp_jitter_match = re.search(r"(\d+\.\d+)\s+ms\s+\d+/", udp_receiver_line)
        if udp_jitter_match:
            udp_jitter = udp_jitter_match.group(1) + "ms"

        udp_loss_match = re.search(r"\(([\d\.]+)%\)", udp_receiver_line)
        if udp_loss_match:
            udp_ploss = udp_loss_match.group(1) + "%"

    print("[INFO] Running TCP test (bandwidth)...")
    tcp_args = ["iperf3", "-c", server_ip, "-p", str(port), "-t", str(duration)]
    if direction == "download":
        tcp_args.append("-R")
    tcp_output = run_and_save(tcp_args, tcp_tmp)

    tcp_receiver_line = ""
    for line in tcp_output.splitlines():
        if "receiver" in line and "bits/sec" in line:
            tcp_receiver_line = line.strip()

    if tcp_receiver_line:
        tcp_bw_match = re.search(r"(\d+(?:\.\d+)? \wbits/sec)", tcp_receiver_line)
        if tcp_bw_match:
            tcp_bw = tcp_bw_match.group(1)

    if debug_mode:
        print("\n[DEBUG] Ping Output:\n", ping_output)
        print("\n[DEBUG] UDP Output:\n", udp_output)
        print("\n[DEBUG] UDP Parsed Line:\n", udp_receiver_line)
        print("\n[DEBUG] TCP Output:\n", tcp_output)
        print("\n[DEBUG] TCP Parsed Line:\n", tcp_receiver_line)
else:
    print(f"[ERROR] Server {server_ip} unreachable. Test aborted.")

# Final Summary
summary_line = (f"{timestamp} STATUS={status} SERVER={server_ip}:{port} DURATION={duration}s "
                f"LATENCY={latency_avg} PING_LOSS={packet_loss} "
                f"UDP_BW={udp_bw} UDP_JITTER={udp_jitter} UDP_LOSS={udp_ploss} "
                f"TCP_BW={tcp_bw}")

print("\n[RESULT] " + summary_line)
with open(summary_log_file, "a") as f:
    f.write(summary_line + "\n")