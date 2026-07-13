"""
NetOps Agent
Pings a configurable list of hosts and exposes latency/uptime metrics
in Prometheus exposition format on /metrics.
"""

import os
import time
import subprocess
import threading
import platform
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---- Configuration ----
# Comma-separated list of hosts to monitor, e.g. "8.8.8.8,1.1.1.1,google.com"
HOSTS = [h.strip() for h in os.environ.get("MONITOR_HOSTS", "8.8.8.8,1.1.1.1").split(",") if h.strip()]
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "15"))
LISTEN_PORT = int(os.environ.get("AGENT_PORT", "9105"))
WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL", "")  # optional Slack/Discord webhook
DOWN_THRESHOLD = int(os.environ.get("DOWN_THRESHOLD", "3"))  # consecutive failures before alert

# ---- Shared state ----
lock = threading.Lock()
metrics = {}  # host -> {"up": 0/1, "latency_ms": float, "consecutive_failures": int}


def ping_host(host: str):
    """Returns (is_up: bool, latency_ms: float|None) using the system ping command."""
    count_flag = "-n" if platform.system().lower() == "windows" else "-c"
    timeout_flag = "-w" if platform.system().lower() == "windows" else "-W"
    cmd = ["ping", count_flag, "1", timeout_flag, "2", host]
    try:
        start = time.time()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        elapsed_ms = (time.time() - start) * 1000
        if result.returncode == 0:
            return True, round(elapsed_ms, 2)
        return False, None
    except Exception:
        return False, None


def send_alert(host: str):
    if not WEBHOOK_URL:
        return
    try:
        import urllib.request
        import json
        payload = json.dumps({"text": f":rotating_light: NetOps Alert: {host} has been DOWN for {DOWN_THRESHOLD}+ checks"}).encode()
        req = urllib.request.Request(WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[alert] failed to send webhook: {e}")


def monitor_loop():
    # Initialize state
    with lock:
        for h in HOSTS:
            metrics[h] = {"up": 0, "latency_ms": 0.0, "consecutive_failures": 0}

    while True:
        for host in HOSTS:
            is_up, latency = ping_host(host)
            with lock:
                state = metrics[host]
                if is_up:
                    state["up"] = 1
                    state["latency_ms"] = latency
                    state["consecutive_failures"] = 0
                else:
                    state["up"] = 0
                    state["latency_ms"] = 0.0
                    state["consecutive_failures"] += 1
                    if state["consecutive_failures"] == DOWN_THRESHOLD:
                        send_alert(host)
            print(f"[monitor] {host}: up={is_up} latency_ms={latency}")
        time.sleep(CHECK_INTERVAL_SECONDS)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        lines = [
            "# HELP netops_host_up Host reachability (1 = up, 0 = down)",
            "# TYPE netops_host_up gauge",
        ]
        with lock:
            for host, state in metrics.items():
                lines.append(f'netops_host_up{{host="{host}"}} {state["up"]}')

        lines.append("# HELP netops_host_latency_ms Ping latency in milliseconds")
        lines.append("# TYPE netops_host_latency_ms gauge")
        with lock:
            for host, state in metrics.items():
                lines.append(f'netops_host_latency_ms{{host="{host}"}} {state["latency_ms"]}')

        body = "\n".join(lines) + "\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass  # silence default HTTP logging


def main():
    print(f"[netops-agent] Starting. Monitoring hosts: {HOSTS}")
    print(f"[netops-agent] Check interval: {CHECK_INTERVAL_SECONDS}s, Down threshold: {DOWN_THRESHOLD}")
    
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), MetricsHandler)
    print(f"[netops-agent] Listening on port {LISTEN_PORT}. Metrics endpoint: http://0.0.0.0:{LISTEN_PORT}/metrics")
    server.serve_forever()


if __name__ == "__main__":
    main()
