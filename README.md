# Zombieland
![Zombieland - Copie](https://github.com/infinition/Zombieland/assets/37984399/30c51924-9bc8-4455-a540-f2b23e6278a1)

## Description
Zombieland is a command and control (C2) server designed to manage and communicate with multiple client machines (referred to as "zombies"). Encrypted communication with clients allows for the execution of various commands and persistence on Zombies. Communication between the server and Zombie is secured using symmetric encryption with Fernet.


## Features
- **Secure Communication**: Utilizes Fernet symmetric encryption to ensure secure message exchange between the server and clients.
- **Dynamic Client Management**: Generates unique client IDs and encryption keys for each client.
- **Command Execution**: Supports execution of various commands on client machines, including creating users, establishing persistence, downloading and uploading files, searching for files, and listing directory contents.
- **Persistence**: Provides mechanisms for clients to maintain persistence on both systemd and init.d systems.
- **File Transfer**: Facilitates secure file uploads and downloads between the server and clients.

## Installation
To set up Zombieland, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/infinition/Zombieland.git
    cd Zombieland
    ```
2. Install dependencies:
    Ensure you have Python 3.x installed along with the required packages:
    ```bash
    pip install cryptography
    ```
3. Run the server:
    ```bash
    python Zombieland.py
    ```

## Usage

### Starting the Server
To start the server, run:
```bash
python Zombieland.py
The server will start listening on the default IP (0.0.0.0) and port (5555). It will generate necessary client files and update them with the server's IP and port information.

Connecting Clients
Clients are managed through dynamically generated scripts. Each client script is uniquely configured with its ID and encryption key.

Generate client script: The server will automatically generate a client script named zombie_client_<client_id>.py.
Deploy the client script: Transfer the generated client script to the target machine and execute it.
Command Execution
Once clients are connected, you can send commands to them via the server console. Example commands include:

createuser: Creates a new user with a randomly generated username and password.
persistence: Establishes persistence for the client on systemd or init.d systems.
download <file_path>: Downloads the specified file from the client.
upload <file_path> <file_data>: Uploads the specified data to a file on the client.
search <search_term>: Searches for files containing the search term.
ls -la: Lists the contents of the current directory on the client.
Example
bash
Copier le code
# Start the server
python Zombieland.py

# From the server console, after a client is connected
Enter command to send to client <client_id>: ls -la
Enter command to send to client <client_id>: createuser
Enter command to send to client <client_id>: persistence
Enter command to send to client <client_id>: download /path/to/file
Enter command to send to client <client_id>: upload /path/to/destination "file data content"
Security
The server uses Fernet encryption to ensure that all communications between the server and the clients are secure. Each client is assigned a unique key, which is stored securely in a JSON file (keys.json). Ensure this file is protected and not accessible to unauthorized users.

Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes. Ensure that your code follows the project's style guidelines and is well-documented.

License
This project is licensed under the MIT License. See the LICENSE file for details.

Educational Use and Disclaimer
This software is intended for educational purposes only. It is designed to help users understand the concepts of command and control servers, secure communication, and client management. The authors and contributors are not responsible for any misuse of this software. Users are encouraged to use this software responsibly and ethically. Any illegal use of this software is strictly prohibited, and the authors disclaim all liability for such actions.
