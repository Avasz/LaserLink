# LaserLink

**MQTT & Home Assistant Bridge with Telegram Notifications for Diode Lasers with Bluetooth**

A robust Python service to monitor GRBL-based diode laser machines via Bluetooth. It parses status updates, integrates with Home Assistant via MQTT, and sends Telegram notifications for job events.

> **Compatibility**
> - **Tested with**: Sculpfun S30 Ultra 33W
> - **Should work with**: Other GRBL-based diode lasers with Bluetooth (Sculpfun, Atomstack, Ortur, xTool, etc.)
> - **Controller Software**: Works independently of Lightburn or any other control software
> - **OS Tested**: Ubuntu (production) and Arch Linux (development)

> **Note**: This project is **vibe coded** 🎵

## Why this exists? (The Lightburn Gap)

**Lightburn** is fantastic software, but it currently lacks a native API or method to expose real-time job status (Start/Stop/Progress) to external systems like Home Assistant. This makes it difficult to integrate your laser into a smart workshop environment.

This project solves that by bypassing the software layer and monitoring the **hardware directly**. By listening to the GRBL controller via Bluetooth, we can accurately detect when a job starts, finishes, or if the machine is just framing, regardless of the control software being used. This makes it the perfect companion for monitoring laser works.

## Unlock Automation

By bridging your Laser Cutter to MQTT and Home Assistant, you can unlock powerful automation workflows:
*   **Notifications**: Get a Telegram message when a long job finishes.
*   **Smart Power**: Automatically turn off the exhaust fan, air assist pump, or lights 5 minutes after a job completes.
*   **Safety**: Trigger a smart plug to cut power if the laser is active for too long or if smoke is detected (via separate sensors).

> [!IMPORTANT]
> **Safety First**: Laser cutters are significant fire hazards. **NEVER leave your laser unattended while it is running.** This monitoring tool is designed to keep you informed and aid in automation, NOT to replace human supervision.

## Features

*   **Bluetooth Monitoring**: Connects to GRBL controllers wirelessly using RFCOMM.
*   **Smart Status Parsing**:
    *   Parses `MPos` (Machine Position), `FS` (Feed/Spindle), and `A` (Accessories).
    *   **Framing Detection**: Distinguishes between actual "Lasering" (Job) and "Framing" (Boundary Check) based on spindle speed and coolant status.
    *   **Job State Logic**: Accurately tracks "Job Started" and "Job Completed", ignoring brief travel moves.
*   **Home Assistant Integration**:
    *   **Auto-Discovery**: Automatically creates entities in Home Assistant via MQTT.
    *   **Sensors**: Status, Laser Power (%), Speed (mm/min), Position (X/Y).
    *   **Binary Sensor**: Job Active.
    *   **Availability**: Reports "Online"/"Offline" status.
*   **Notifications**: Sends Telegram messages when a job starts or finishes.
*   **Flexible Configuration**:
    *   **Dual Config**: Use `config.yaml` for general settings and **Environment Variables** for secrets (passwords, tokens).
    *   **Docker Support**: Ready-to-use `Dockerfile` and `docker-compose.yml`.
    *   **Systemd Support**: Run as a background service.

## Requirements

*   Linux (tested on Arch Linux)
*   Python 3.x
*   BlueZ (Bluetooth stack)
*   A GRBL-based laser cutter with Bluetooth module

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd laserlink
    ```

2.  **Install Dependencies**:
    ```bash
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
    ```

## Configuration

You can configure the application using `config.yaml` OR Environment Variables. **Environment Variables take precedence**, making them ideal for secrets.

### 1. config.yaml
Copy the example config and edit it:
```bash
cp config.yaml.example config.yaml # If applicable
nano config.yaml
```

### 2. Environment Variables
You can override any setting. This is the recommended way to handle passwords and tokens.

| Section | Config Option | Environment Variable | Description |
| :--- | :--- | :--- | :--- |
| **Laser** | `bluetooth_mac` | `BLUETOOTH_MAC` | **Required**. MAC address of the laser. |
| | `rfcomm_port` | `RFCOMM_PORT` | Bluetooth channel (Default: 1). |
| | `polling_interval` | `POLLING_INTERVAL` | Seconds between status queries (Default: 0.5). |
| | `framing_threshold` | `FRAMING_THRESHOLD` | Spindle RPM threshold for "Framing" vs "Lasering". |
| | `max_spindle_speed` | `MAX_SPINDLE_SPEED` | Max RPM ($30) for calculating Power % (Default: 1000). |
| | `show_raw` | `SHOW_RAW` | Set `true` to see raw GRBL responses in logs. |
| **MQTT** | `enabled` | `MQTT_ENABLED` | Enable MQTT integration (`true`/`false`). |
| | `broker` | `MQTT_BROKER` | MQTT Broker IP/Hostname. |
| | `port` | `MQTT_PORT` | MQTT Port (Default: 1883). |
| | `topic` | `MQTT_TOPIC` | Base topic for status (Default: `laser/status`). |
| | `username` | `MQTT_USERNAME` | MQTT Username. |
| | `password` | `MQTT_PASSWORD` | MQTT Password. |
| **Home Assistant** | `enabled` | `HA_ENABLED` | Enable HA Auto-Discovery (`true`/`false`). |
| | `discovery_prefix` | `HA_DISCOVERY_PREFIX` | MQTT Discovery Prefix (Default: `homeassistant`). |
| | `node_id` | `HA_NODE_ID` | Unique ID for the device (Default: `laserlink`). |
| | `device_name` | `HA_DEVICE_NAME` | Display name in HA (Default: `Laser Cutter`). |
| **Telegram** | `enabled` | `TELEGRAM_ENABLED` | Enable Telegram notifications (`true`/`false`). |
| | `bot_token` | `TELEGRAM_BOT_TOKEN` | Your Telegram Bot Token. |
| | `chat_id` | `TELEGRAM_CHAT_ID` | Your Telegram Chat ID. |
| | `message_started` | `TELEGRAM_MESSAGE_STARTED` | Message sent on job start. |
| | `message_completed` | `TELEGRAM_MESSAGE_COMPLETED` | Message sent on job completion. |

## Usage

### Manual Run
**Important**: Bluetooth access usually requires `sudo`. To pass environment variables (like your secrets) to the sudo session, use the `-E` flag.

```bash
# Export secrets first
export MQTT_PASSWORD="your_password"
export TELEGRAM_BOT_TOKEN="your_token"

# Run with sudo -E
sudo -E venv/bin/python3 src/monitor.py
```

### Systemd Service
To run LaserLink as a background service:

1.  **Configure the Application**:
    Edit `config.yaml` with all your settings including MQTT credentials, Telegram tokens, and Bluetooth MAC address.

2.  **Install to System Directory**:
    ```bash
    sudo mkdir -p /opt/laserlink
    sudo cp -r . /opt/laserlink/
    cd /opt/laserlink
    ```

3.  **Set up Python Virtual Environment**:
    ```bash
    sudo python3 -m venv /opt/laserlink/venv
    sudo /opt/laserlink/venv/bin/pip install -r requirements.txt
    ```

4.  **Install Service File**:
    ```bash
    sudo cp laserlink.service /etc/systemd/system/
    sudo systemctl daemon-reload
    ```

5.  **Enable and Start**:
    ```bash
    sudo systemctl enable laserlink
    sudo systemctl start laserlink
    ```

6.  **Check Status**:
    ```bash
    sudo systemctl status laserlink
    sudo journalctl -u laserlink -f
    ```

### Docker
1.  **Edit `config.yaml`** with your non-secret settings.
2.  **Secrets**: You can put secrets in `config.yaml`, OR use a `.env` file (uncomment the `env_file` section in `docker-compose.yml`).
3.  **Run**:
    ```bash
    docker-compose up -d
    ```
    *Note: Uses `network_mode: host` and mounts `/var/run/dbus` for Bluetooth access.*

## Troubleshooting

### Clearing Old Home Assistant Entities
If you have old or duplicate entities in Home Assistant (e.g., after renaming sensors), you can clear them using the included script:

1.  Stop the monitor service.
2.  Run the cleanup script:
    ```bash
    sudo -E venv/bin/python3 src/clear_mqtt.py
    ```
3.  Restart Home Assistant (optional, but recommended).
4.  Start the monitor service again.
