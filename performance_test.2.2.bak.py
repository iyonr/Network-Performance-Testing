#!/usr/bin/env python3
# =====================================================
# Author       : Marion Renaldo Rotensulu
# Version      : v2.2
# Description  : Custom Performance test with OS detection, user-level logging, UDP BW default, RTT parsing
# Log File     : /var/log/iperf_tests/iperf_summary.log (or ~/iperf_logs if not root)
# Last Updated : 2025-06-13
# Changelog    :
#   - v1.0 Basic summary output
#   - v1.1 Status check & debug output
#   - v1.2 Syslog-style one-line logging
#   - v1.3 Live terminal output + debug mode
#   - v1.4 Added raw output capture in /tmp before parsing
#   - v1.5 Fixed regex parsing for UDP/TCP final summary lines (receiver block)
#   - v1.6 Fixed UDP regex from correct receiver line
#   - v1.7 Regex fix to correctly parse integer/float UDP bandwidth
#   - v2.0 Logging fallback to user dir if not root, macOS RTT parsing added
#   - v2.1 OS auto-detection + required fallback, reverse parsing for download mode
#   - v2.2 Default UDP bandwidth set to 1000M if not defined
# =====================================================

import subprocess
import datetime
import os
import argparse
import re
import socket
import platform
import sys

# --- Argument Parser ---
parser = argparse.ArgumentParser(description="Network Performance Test with iperf3 and ping.")
parser.add_argument("--duration", type=int, choices=[60, 300, 600], default=60,
                    help="Test duration in seconds")
parser.add_argument("--server", type=str, required=True, help="IP address of iperf3 server")
parser.add_argument("--port", type=int, default=5201, help="iperf3 server port (default: 5201)")
parser.add_argument("--debug", action="store_true", help="Enable debug output")
parser.add_argument("--udp-bandwidth", type=str, default="1000M", help="UDP test bandwidth (default: 1000M)")
parser.add_argument("--direction", type=str, choices=["upload", "download"], default="upload",
                    help="Test direction (default: upload)")
parser.add_argument("--os-mode", type=str, choices=["Linux", "MacOS"], required=False,
                    help="Override OS detection")
args = parser.parse_args()

# --- Auto-detect OS ---
auto_os = platform.system()
if auto_os == "Darwin":
    detected_os = "MacOS"
elif auto_os == "Linux":
    detected_os = "Linux"
else:
    detected_os = None

if args.os_mode:
    os_mode = args.os_mode
elif detected_os:
    os_mode = detected_os
    print(f"[INFO] OS auto-detected as {os_mode}")
else:
    print("[ERROR] Could not detect OS. Please provide --os-mode MacOS|Linux.")
    sys.exit(1)

# --- Define Paths ---
duration = args.duration
server_ip = args.server
port = args.port
debug_mode = args.debug
direction = args.direction
udp_bw = args.udp_bandwidth or "1000M"  # fallback if empty string

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
user_home = os.path.expanduser("~")
is_root = (os.geteuid() == 0)

log_dir = "/var/log/iperf_tests" if is_root else os.path.join(user_home, "iperf_logs")
tmp_dir = "/tmp"
os.makedirs(log_dir, exist_ok=True)

summary_log_file = os.path.join(log_dir, "iperf_summary.log")
ping_tmp = os.path.join(tmp_dir, f"ping_{timestamp}.log")
udp_tmp = os.path.join(tmp_dir, f"iperf3_udp_{timestamp}.log")
tcp_tmp = os.path.join(tmp_dir, f"iperf3_tcp_{timestamp}.log")

# --- Helper Functions ---
def run_and_save(cmd, tmpfile):
    try:
        with open(tmpfile, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True, timeout=duration + 30)
        with open(tmpfile, "r") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"

def check_mtu(ip):
    mtu_test = subprocess.run(["ping", "-c", "1", "-s", "1472", "-M", "do", ip], capture_output=True, text=True)
    if "frag needed" in mtu_test.stderr or "Message too long" in mtu_test.stderr:
        print("[WARNING] MTU issue detected. Consider adjusting MTU if UDP loss is high.")

# --- Reachability Check ---
ping_status = False
try:
    socket.gethostbyname(server_ip)
    ping_check = subprocess.run(["ping", "-c", "3", server_ip], capture_output=True, text=True)
    if "0% packet loss" in ping_check.stdout or "1% packet loss" in ping_check.stdout:
        ping_status = True
except Exception:
    ping_status = False

# --- Initialize Results ---
status = "FAIL"
latency_avg = "-"
packet_loss = "-"
udp_bw_result = udp_jitter = udp_ploss = "-"
tcp_bw_result = "-"

if ping_status:
    status = "OK"
    check_mtu(server_ip)

    print("[INFO] Running latency test (ping)...")
    ping_output = run_and_save(["ping", "-c", str(duration // 2), server_ip], ping_tmp)

    if os_mode == "Linux":
        match = re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+", ping_output)
    elif os_mode == "MacOS":
        match = re.search(r"(?:rtt|round-trip).* = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+", ping_output)
    else:
        match = None

    if match:
        latency_avg = match.group(1) + "ms"

    ploss_match = re.search(r"(\d+)% packet loss", ping_output)
    if ploss_match:
        packet_loss = ploss_match.group(1) + "%"

    print("[INFO] Running UDP test (jitter, loss, bandwidth)...")
    udp_args = ["iperf3", "-c", server_ip, "-p", str(port), "-u", "-t", str(duration), "-b", udp_bw]
    if direction == "download":
        udp_args.append("-R")

    udp_output = run_and_save(udp_args, udp_tmp)

    udp_line = ""
    for line in udp_output.splitlines():
        if direction == "download" and "sender" in line and "bits/sec" in line:
            udp_line = line.strip()
        elif direction == "upload" and "receiver" in line and "bits/sec" in line:
            udp_line = line.strip()

    if udp_line:
        udp_bw_match = re.search(r"(\d+(?:\.\d+)? \wbits/sec)", udp_line)
        if udp_bw_match:
            udp_bw_result = udp_bw_match.group(1)

        udp_jitter_match = re.search(r"(\d+\.\d+)\s+ms\s+\d+/", udp_line)
        if udp_jitter_match:
            udp_jitter = udp_jitter_match.group(1) + "ms"

        udp_loss_match = re.search(r"\(([\d\.]+)%\)", udp_line)
        if udp_loss_match:
            udp_ploss = udp_loss_match.group(1) + "%"

    print("[INFO] Running TCP test (bandwidth)...")
    tcp_args = ["iperf3", "-c", server_ip, "-p", str(port), "-t", str(duration)]
    if direction == "download":
        tcp_args.append("-R")

    tcp_output = run_and_save(tcp_args, tcp_tmp)

    tcp_line = ""
    for line in tcp_output.splitlines():
        if "receiver" in line and "bits/sec" in line:
            tcp_line = line.strip()

    if tcp_line:
        tcp_bw_match = re.search(r"(\d+(?:\.\d+)? \wbits/sec)", tcp_line)
        if tcp_bw_match:
            tcp_bw_result = tcp_bw_match.group(1)

    if debug_mode:
        print("\n[DEBUG] Ping Output:\n", ping_output)
        print("\n[DEBUG] UDP Output:\n", udp_output)
        print("\n[DEBUG] UDP Parsed Line:\n", udp_line)
        print("\n[DEBUG] TCP Output:\n", tcp_output)
        print("\n[DEBUG] TCP Parsed Line:\n", tcp_line)

else:
    print(f"[ERROR] Server {server_ip} unreachable. Test aborted.")

# --- Final Summary ---
summary_line = (f"{timestamp} STATUS={status} SERVER={server_ip}:{port} DURATION={duration}s "
                f"LATENCY={latency_avg} PING_LOSS={packet_loss} "
                f"UDP_BW={udp_bw_result} UDP_JITTER={udp_jitter} UDP_LOSS={udp_ploss} "
                f"TCP_BW={tcp_bw_result}")

print("\n[RESULT] " + summary_line)
with open(summary_log_file, "a") as f:
    f.write(summary_line + "\n")