#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py
Web Dashboard Portal & Simulated Client Orchestrator
- Serves the frontend (index.html / zombieland.html)
- Bridges C2 REST API requests to the socket-level C2Manager
- Operates a local Server-Sent Events (SSE) channel for real-time telemetry/log stream
- Spawns real, local socket-based simulated agents to demonstrate operations without setup
"""

import sys
import os
import json
import time
import threading
import socket
import struct
import random
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from cryptography.fernet import Fernet

# Set path relative to Zombieland root
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

try:
    from c2_manager import c2_manager, EventBus
except ImportError:
    print("Error: Could not import c2_manager from root directory.")
    sys.exit(1)

app = Flask(__name__, static_folder='.', template_folder='.')

# Simulation State Tracker
simulated_threads = []
simulation_active = False
sim_lock = threading.Lock()

# ---------- Static Dashboard Assets ----------
@app.route('/')
def index():
    return send_from_directory(str(BASE_DIR), 'index.html')

@app.route('/zombieland.html')
def zombieland_html():
    return send_from_directory(str(BASE_DIR), 'zombieland.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory(str(BASE_DIR), path)

# ---------- C2 Web API Route Bindings ----------
@app.route('/c2/status', methods=['GET'])
def c2_status():
    return jsonify(c2_manager.status())

@app.route('/c2/agents', methods=['GET'])
def c2_agents():
    return jsonify(c2_manager.list_agents())

@app.route('/c2/start', methods=['POST'])
def c2_start():
    data = request.json or {}
    port = data.get('port', 5555)
    return jsonify(c2_manager.start(port=int(port)))

@app.route('/c2/stop', methods=['POST'])
def c2_stop():
    return jsonify(c2_manager.stop())

@app.route('/c2/command', methods=['POST'])
def c2_command():
    data = request.json or {}
    cmd = data.get('command', '').strip()
    targets = data.get('targets', [])
    if not targets or not cmd:
        return jsonify({"status": "error", "message": "Targets and command required"}), 400
    res = c2_manager.send_command(targets, cmd)
    return jsonify(res)

@app.route('/c2/broadcast', methods=['POST'])
def c2_broadcast():
    data = request.json or {}
    cmd = data.get('command', '').strip()
    if not cmd:
        return jsonify({"status": "error", "message": "Command required"}), 400
    res = c2_manager.broadcast(cmd)
    return jsonify(res)

@app.route('/c2/generate_client', methods=['POST'])
def c2_generate_client():
    data = request.json or {}
    cid = data.get('client_id', '').strip()
    user = data.get('lab_user', 'student').strip()
    passwd = data.get('lab_password', 'cyberpass').strip()
    res = c2_manager.generate_client(client_id=cid, lab_user=user, lab_password=passwd)
    return jsonify(res)

@app.route('/c2/download_client/<filename>', methods=['GET'])
def c2_download_client(filename):
    client_path = BASE_DIR / "generated_clients"
    if not (client_path / filename).exists():
        return "File not found", 404
    return send_from_directory(str(client_path), filename, as_attachment=True)

@app.route('/c2/stale_agents', methods=['GET'])
def c2_stale_agents():
    threshold = int(request.args.get('threshold', 60))
    now = time.time()
    stale_count = 0
    with c2_manager._lock:
        for cid, (_, _, info) in c2_manager._clients.items():
            if now - info.get("lastSeen", now) > threshold:
                stale_count += 1
    return jsonify({"count": stale_count})

@app.route('/c2/purge_agents', methods=['POST'])
def c2_purge_agents():
    # Purging cleans up inactive agent metadata or simulated agents.
    return jsonify({"status": "ok", "purged": 0})

# ---------- Server-Sent Events (SSE) Stream ----------
@app.route('/c2/events')
def c2_events():
    def event_stream():
        # Yield initial status on subscription
        yield f"event: status\ndata: {json.dumps(c2_manager.status())}\n\n"
        
        # Local queue to buffer thread events
        queue = []
        def on_event(ev):
            queue.append(ev)
        
        c2_manager.bus.subscribe(on_event)
        
        try:
            while True:
                # Flush the event queue down the SSE connection
                while queue:
                    ev = queue.pop(0)
                    yield f"event: {ev.get('type', 'message')}\ndata: {json.dumps(ev)}\n\n"
                time.sleep(0.15)
        except GeneratorExit:
            c2_manager.bus.unsubscribe(on_event)
                
    return Response(event_stream(), mimetype="text/event-stream")

# ---------- Local Real TCP Socket Agent Simulator ----------
class SimulatedAgent(threading.Thread):
    """
    Simulates a Python Zombie Client connecting locally via raw TCP socket.
    Fulfills pings, varies telemetry, and generates realistic system payloads.
    """
    def __init__(self, client_id, hostname, os_name, ip, key, life_span=None):
        super().__init__(daemon=True)
        self.client_id = client_id
        self.hostname = hostname
        self.os_name = os_name
        self.ip = ip
        self.cipher = Fernet(key)
        self.life_span = life_span
        self.running = True
        self.sock = None

    def run(self):
        start_time = time.time()
        
        # Try to connect to localhost port 5555
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(("127.0.0.1", 5555))
            self.sock.sendall(self.client_id.encode())
        except Exception as e:
            c2_manager.bus.emit({
                "type": "log",
                "level": "error",
                "text": f"Simulation failed to connect client {self.client_id}: {e}"
            })
            return

        # Start simulated telemetry loop
        threading.Thread(target=self._telemetry_loop, daemon=True).start()

        # Command listener loop
        while self.running and simulation_active:
            if self.life_span and (time.time() - start_time) > self.life_span:
                # Trigger clean exit to showcase disconnected state
                c2_manager.bus.emit({
                    "type": "log",
                    "level": "warn",
                    "text": f"Simulation agent {self.client_id} reached lifecycle limit. Simulating flatline."
                })
                break
                
            try:
                self.sock.settimeout(1.0)
                hdr = self.sock.recv(4)
                if not hdr:
                    continue
                (length,) = struct.unpack(">I", hdr)
                enc = b""
                self.sock.settimeout(5.0)
                while len(enc) < length:
                    chunk = self.sock.recv(length - len(enc))
                    if not chunk:
                        break
                    enc += chunk
                
                cmd = self.cipher.decrypt(enc).decode().strip()
                response_data = self._execute_mock_command(cmd)
                
                # Encrypt and return command output
                enc_resp = self.cipher.encrypt(json.dumps(response_data).encode())
                self.sock.sendall(struct.pack(">I", len(enc_resp)) + enc_resp)
                
            except socket.timeout:
                continue
            except Exception:
                break
                
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass

    def _telemetry_loop(self):
        cpu = random.randint(5, 15)
        mem = random.randint(30, 45)
        
        while self.running and simulation_active:
            try:
                # Jitter cpu/ram telemetry values slightly
                cpu = max(1, min(99, cpu + random.randint(-4, 4)))
                mem = max(1, min(99, mem + random.randint(-2, 2)))
                
                # Alternate ping keepalives and telemetry reports
                ping_payload = self.cipher.encrypt(json.dumps({"ping": time.time()}).encode())
                self.sock.sendall(struct.pack(">I", len(ping_payload)) + ping_payload)
                
                time.sleep(3.0)
                
                tel_payload = self.cipher.encrypt(json.dumps({
                    "telemetry": {
                        "hostname": self.hostname,
                        "os": self.os_name,
                        "cpu_percent": cpu,
                        "mem_percent": mem,
                        "uptime": time.time() - float(int(time.time() - 5000))
                    }
                }).encode())
                self.sock.sendall(struct.pack(">I", len(tel_payload)) + tel_payload)
                
                time.sleep(5.0)
            except Exception:
                break

    def _execute_mock_command(self, cmd):
        cmd_parts = cmd.split(" ", 1)
        base_cmd = cmd_parts[0].lower()
        
        if base_cmd == "whoami":
            if self.os_name == "Windows":
                return {"result": f"NT AUTHORITY\\SYSTEM (simulated: {self.client_id})"}
            return {"result": f"root (simulated: {self.client_id})"}
            
        elif base_cmd == "ls" or base_cmd == "pwd":
            if self.os_name == "Windows":
                return {"result": f"C:\\Users\\Administrator\\zombie\n\n06/01/2026  23:18    <DIR>          .\n06/01/2026  23:18    <DIR>          ..\n06/01/2026  23:18               256 client.py\n06/01/2026  23:18             4,812 system_info.log"}
            return {"result": f"/root/zombie\ntotal 16\ndrwxr-xr-x 2 root root 4096 Jun  1 23:18 .\ndrwx------ 8 root root 4096 Jun  1 23:18 ..\n-rwxr-xr-x 1 root root  124 Jun  1 23:18 client.py\n-rw-r--r-- 1 root root 2155 Jun  1 23:18 loot.db"}
            
        elif base_cmd == "cat":
            target_file = cmd_parts[1] if len(cmd_parts) > 1 else ""
            if "passwd" in target_file or "shadow" in target_file:
                return {"result": "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\nstudent:x:1000:1000:Lab Student:/home/student:/bin/bash\nprofessor:x:1001:1001:Lab Coordinator:/home/professor:/bin/bash"}
            elif target_file:
                return {"result": f"[Content of {target_file}]\nSimulated training lab file content. Flag: {{ZOMBIE_LAB_FLAG_SECRET}}"}
            return {"error": "cat: missing operand"}
            
        elif base_cmd == "sysinfo":
            return {
                "result": {
                    "hostname": self.hostname,
                    "os": self.os_name,
                    "arch": "x86_64",
                    "cpu_percent": random.randint(10, 45),
                    "mem_percent": random.randint(40, 75)
                }
            }
            
        elif base_cmd == "lab_creds":
            return {"result": "User: labstudent / Pass: hackzombieland123!"}
            
        elif base_cmd == "persistence":
            return {"result": "Persistence scheduled successfully."}
            
        # Return generic shell output
        return {"result": f"[{self.hostname}] Executed: '{cmd}'\nOutput: Command simulated successfully in ethical laboratory environment."}

@app.route('/api/demo/start', methods=['POST'])
def demo_start():
    global simulation_active, simulated_threads
    with sim_lock:
        if simulation_active:
            return jsonify({"status": "already_active"})
        
        # 1. Ensure the C2 socket engine is running on port 5555
        c2_status = c2_manager.status()
        if not c2_status["running"]:
            c2_manager.start(port=5555)
            time.sleep(1.0) # Wait for thread initialization
            
        simulation_active = True
        simulated_threads = []
        
        # 2. Mock Agent Configurations
        configs = [
            {"id": "zombie-linux-web", "host": "WEBSERV-PROD", "os": "Linux", "ip": "10.0.1.25", "life": None},
            {"id": "zombie-win-ad", "host": "WIN-AD-CONTROLLER", "os": "Windows", "ip": "10.0.1.100", "life": None},
            {"id": "zombie-kali-rogue", "host": "KALI-PENTEST", "os": "Linux", "ip": "10.0.2.13", "life": None},
            {"id": "zombie-iot-cam", "host": "IOT-CAMERA", "os": "Linux", "ip": "192.168.1.90", "life": 45.0} # Disconnects after 45s
        ]
        
        for cfg in configs:
            # Register client ID with C2 keys
            key = Fernet.generate_key()
            c2_manager._save_key(cfg["id"], key)
            
            # Start simulated thread
            agent = SimulatedAgent(
                client_id=cfg["id"],
                hostname=cfg["host"],
                os_name=cfg["os"],
                ip=cfg["ip"],
                key=key,
                life_span=cfg["life"]
            )
            agent.start()
            simulated_threads.append(agent)
            
        c2_manager.bus.emit({
            "type": "log",
            "level": "info",
            "text": "Cyber Simulation Lab started: 4 socket agents injected."
        })
        return jsonify({"status": "started", "agents": len(configs)})

@app.route('/api/demo/stop', methods=['POST'])
def demo_stop():
    global simulation_active, simulated_threads
    with sim_lock:
        if not simulation_active:
            return jsonify({"status": "not_active"})
            
        simulation_active = False
        for t in simulated_threads:
            t.running = False
        simulated_threads = []
        
        c2_manager.bus.emit({
            "type": "log",
            "level": "warn",
            "text": "Simulation Lab stopped."
        })
        return jsonify({"status": "stopped"})


if __name__ == '__main__':
    # Auto-start C2 on port 5555
    c2_manager.start(port=5555)
    
    print("\n=======================================================")
    print("      ZOMBIELAND CYBER LAB DASHBOARD & BACKEND")
    print("=======================================================")
    print(" * C2 Socket listener running on port 5555")
    print(" * Flask Web Interface available at http://localhost:5000")
    print("=======================================================\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
