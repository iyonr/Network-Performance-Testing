#!/usr/bin/env python3
# =====================================================
# Author       : Marion Renaldo Rotensulu
# Version      : v2.2
# Description  : Network Performance Test Script using iperf3 + ping (Syslog-style output)
#                Supports upload/download mode, UDP/TCP metrics, debug, cron jobs,
#                OS-aware ping parsing (Linux/MacOS), non-root logging, live ping, 
#                post-test ping, and temp file cleanup.
#
# Log File     : /var/log/iperf_tests/iperf_summary.log (or ~/iperf_logs if not root)
#
# Log Output   : /var/log/iperf_tests/iperf_summary.log (for root)
#              : ~/iperf_logs/iperf_summary.log (for non-root users)
#
# Temp Logs    : /tmp/ping_*.log, /tmp/iperf3_udp_*.log, /tmp/iperf3_tcp_*.log
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
#   - v2.3 Added --clean-tmp option to remove all temp log files after test,
#          live ping during iperf, post-test ping parsing, and combined debug log
# =====================================================

import subprocess
import datetime
import os
import argparse
import re
import socket
import platform
import shutil
import sys
import threading

# Argument Parser
parser = argparse.ArgumentParser(description="Network Performance Test Script (Syslog Style + Live Output + Cleanup)")
parser.add_argument("--duration", type=int, choices=[60, 300, 600], default=60, help="Test duration in seconds")
parser.add_argument("--server", type=str, required=True, help="IP address of iperf3 server")
parser.add_argument("--port", type=int, default=5201, help="iperf3 server port")
parser.add_argument("--udp-bandwidth", type=str, default="1000M", help="UDP test bandwidth")
parser.add_argument("--direction", choices=["upload", "download"], default="upload", help="Test direction")
parser.add_argument("--debug", action="store_true", help="Enable debug output")
parser.add_argument("--os-mode", choices=["Linux", "MacOS"], help="Override OS auto-detection")
parser.add_argument("--clean-tmp", action="store_true", help="Clean up temp files after test")
args = parser.parse_args()

# OS Detection
detected_os = platform.system()
os_mode = args.os_mode or ("MacOS" if detected_os.lower() == "darwin" else "Linux")
os_mode = os_mode.capitalize()

# Timestamp
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Logging Paths
is_root = os.geteuid() == 0
log_dir = "/var/log/iperf_tests" if is_root else os.path.expanduser("~/iperf_logs")
os.makedirs(log_dir, exist_ok=True)
summary_log_file = os.path.join(log_dir, "iperf_summary.log")

# Temp Paths
tmp_dir = "/tmp"
ping_tmp = os.path.join(tmp_dir, f"ping_{timestamp}.log")
ping_live_tmp = os.path.join(tmp_dir, f"ping_live_{timestamp}.log")
ping_post_tmp = os.path.join(tmp_dir, f"ping_post_{timestamp}.log")
udp_tmp = os.path.join(tmp_dir, f"iperf3_udp_{timestamp}.log")
tcp_tmp = os.path.join(tmp_dir, f"iperf3_tcp_{timestamp}.log")

# Helper Function

def run_and_save(cmd, tmpfile, live=False):
    with open(tmpfile, "w") as f:
        process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
        if live:
            return process
        try:
            process.wait(timeout=args.duration + 30)
        except subprocess.TimeoutExpired:
            process.kill()
            return f"ERROR: Command '{cmd}' timed out"
    with open(tmpfile, "r") as f:
        return f.read()

# Regex ping parser

def parse_ping(filepath):
    avg_latency = "-"
    loss = "-"
    with open(filepath, "r") as f:
        text = f.read()
        loss_match = re.search(r"(\d+)% packet loss", text)
        if loss_match:
            loss = loss_match.group(1) + "%"
        if os_mode == "Linux":
            match = re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+", text)
        else:
            match = re.search(r"(?:rtt|round-trip).* = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+", text)
        if match:
            avg_latency = match.group(1) + "ms"
    return avg_latency, loss

# Initial Ping Check
reachable = subprocess.run(["ping", "-c", "3", args.server], capture_output=True, text=True)
status = "OK" if "0% packet loss" in reachable.stdout else "FAIL"

if status == "FAIL":
    print(f"[ERROR] Server {args.server} unreachable. Test aborted.")
    sys.exit(1)

print("[INFO] Starting baseline ping...")
run_and_save(["ping", "-c", str(args.duration // 2), args.server], ping_tmp)
base_lat, base_loss = parse_ping(ping_tmp)

# Live Ping
print("[INFO] Starting live ping during iperf test...")
live_ping = run_and_save(["ping", args.server], ping_live_tmp, live=True)

# UDP Test
print("[INFO] Running UDP test...")
udp_cmd = ["iperf3", "-c", args.server, "-p", str(args.port), "-u", "-t", str(args.duration), "-b", args.udp_bandwidth]
if args.direction == "download":
    udp_cmd.append("--reverse")
udp_output = run_and_save(udp_cmd, udp_tmp)

# TCP Test
print("[INFO] Running TCP test...")
tcp_cmd = ["iperf3", "-c", args.server, "-p", str(args.port), "-t", str(args.duration)]
if args.direction == "download":
    tcp_cmd.append("--reverse")
tcp_output = run_and_save(tcp_cmd, tcp_tmp)

# Kill live ping
live_ping.terminate()
print("[INFO] Running post-test ping...")
run_and_save(["ping", "-c", str(args.duration // 2), args.server], ping_post_tmp)

live_lat, live_loss = parse_ping(ping_live_tmp)
post_lat, post_loss = parse_ping(ping_post_tmp)

# Parse UDP
udp_bw = udp_jitter = udp_loss = "-"
for line in udp_output.splitlines():
    if "receiver" in line and "bits/sec" in line:
        udp_bw_match = re.search(r"(\d+(?:\.\d+)? \wbits/sec)", line)
        if udp_bw_match:
            udp_bw = udp_bw_match.group(1)
        jitter_match = re.search(r"(\d+\.\d+) ms", line)
        if jitter_match:
            udp_jitter = jitter_match.group(1) + "ms"
        loss_match = re.search(r"\((\d+(?:\.\d+)?)%\)", line)
        if loss_match:
            udp_loss = loss_match.group(1) + "%"
        break

# Parse TCP
tcp_bw = "-"
for line in tcp_output.splitlines():
    if "receiver" in line and "bits/sec" in line:
        match = re.search(r"(\d+(?:\.\d+)? \wbits/sec)", line)
        if match:
            tcp_bw = match.group(1)
        break

# Summary
summary_line = (f"{timestamp} STATUS={status} SERVER={args.server}:{args.port} DURATION={args.duration}s "
                f"LATENCY={base_lat} PING_LOSS={base_loss} "
                f"LIVE_LAT={live_lat} LIVE_LOSS={live_loss} "
                f"POST_LAT={post_lat} POST_LOSS={post_loss} "
                f"UDP_BW={udp_bw} UDP_JITTER={udp_jitter} UDP_LOSS={udp_loss} "
                f"TCP_BW={tcp_bw}")
print("\n[RESULT]", summary_line)

with open(summary_log_file, "a") as f:
    f.write(summary_line + "\n")

if args.debug:
    print("\n[DEBUG] --- Ping Output (Base) ---\n", open(ping_tmp).read())
    print("\n[DEBUG] --- Ping Output (Live) ---\n", open(ping_live_tmp).read())
    print("\n[DEBUG] --- Ping Output (Post) ---\n", open(ping_post_tmp).read())
    print("\n[DEBUG] --- UDP Output ---\n", udp_output)
    print("\n[DEBUG] --- TCP Output ---\n", tcp_output)

# Clean temp logs if requested
if args.clean_tmp:
    for file in [ping_tmp, ping_live_tmp, ping_post_tmp, udp_tmp, tcp_tmp]:
        try:
            os.remove(file)
        except Exception:
            pass