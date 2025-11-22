import sys
import time
import re
import socket
import json
import requests
import logging
import paho.mqtt.client as mqtt
from config import Config

class LaserMonitor:
    def __init__(self, config_path="config.yaml"):
        self.cfg = Config(config_path)
        
        # Configure Logging
        logging.basicConfig(
            level=getattr(logging, self.cfg.log_level, logging.INFO),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        valid, msg = self.cfg.validate()
        if not valid:
            logging.error(f"Configuration Error: {msg}")
            sys.exit(1)

        self.mqtt_client = None
        self.last_state = "Idle" # Assume Idle initially
        self.last_detailed_status = "Idle"
        self.job_in_progress = False

        if self.cfg.mqtt_enabled:
            self.setup_mqtt()

    def setup_mqtt(self):
        self.mqtt_client = mqtt.Client()
        if self.cfg.mqtt_username and self.cfg.mqtt_password:
            self.mqtt_client.username_pw_set(self.cfg.mqtt_username, self.cfg.mqtt_password)
        
        # Last Will and Testament (LWT)
        # Publish "offline" to availability topic if we disconnect unexpectedly
        availability_topic = f"{self.cfg.mqtt_topic}/availability"
        self.mqtt_client.will_set(availability_topic, "offline", retain=True)

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logging.info("Connected to MQTT Broker")
                # Publish "online" to availability topic
                client.publish(availability_topic, "online", retain=True)
                
                if self.cfg.ha_enabled:
                    self.publish_ha_discovery()
            else:
                logging.error(f"Failed to connect, return code {rc}")

        self.mqtt_client.on_connect = on_connect
        
        try:
            self.mqtt_client.connect(self.cfg.mqtt_broker, self.cfg.mqtt_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logging.error(f"Could not connect to MQTT Broker: {e}")
            self.mqtt_client = None

    def publish_ha_discovery(self):
        """Publishes Home Assistant Auto-Discovery payloads."""
        logging.info("Publishing Home Assistant Discovery payloads...")
        
        device_info = {
            "identifiers": [self.cfg.ha_node_id],
            "name": self.cfg.ha_device_name,
            "model": "GRBL Laser",
            "manufacturer": "LaserLink"
        }

        # Helper to publish a sensor config
        def publish_sensor(object_id, name, value_template, icon=None, unit=None, device_class=None):
            topic = f"{self.cfg.ha_discovery_prefix}/sensor/{self.cfg.ha_node_id}/{object_id}/config"
            payload = {
                "name": f"{self.cfg.ha_device_name} {name}",
                "state_topic": self.cfg.mqtt_topic,
                "value_template": value_template,
                "unique_id": f"{self.cfg.ha_node_id}_{object_id}",
                "device": device_info,
                "availability_topic": f"{self.cfg.mqtt_topic}/availability" # Optional: Implement LWT later
            }
            if icon: payload["icon"] = icon
            if unit: payload["unit_of_measurement"] = unit
            if device_class: payload["device_class"] = device_class
            
            self.mqtt_client.publish(topic, json.dumps(payload), retain=True)

        # Helper for binary sensor
        def publish_binary_sensor(object_id, name, value_template, device_class=None):
            topic = f"{self.cfg.ha_discovery_prefix}/binary_sensor/{self.cfg.ha_node_id}/{object_id}/config"
            payload = {
                "name": f"{self.cfg.ha_device_name} {name}",
                "state_topic": self.cfg.mqtt_topic,
                "value_template": value_template,
                "unique_id": f"{self.cfg.ha_node_id}_{object_id}",
                "device": device_info,
                "payload_on": True,
                "payload_off": False
            }
            if device_class: payload["device_class"] = device_class
            
            self.mqtt_client.publish(topic, json.dumps(payload), retain=True)

        # Sensors
        publish_sensor("status", "Status", "{{ value_json.detailed_status }}", icon="mdi:laser-pointer")
        publish_sensor("laser_power", "Laser Power", "{{ value_json.laser_power_pct }}", unit="%", icon="mdi:flash")
        publish_sensor("speed", "Speed", "{{ value_json.feed_rate }}", unit="mm/min", icon="mdi:speedometer")
        publish_sensor("pos_x", "Position X", "{{ value_json.mpos.x }}", unit="mm", icon="mdi:axis-x-arrow")
        publish_sensor("pos_y", "Position Y", "{{ value_json.mpos.y }}", unit="mm", icon="mdi:axis-y-arrow")
        
        # Binary Sensors
        publish_binary_sensor("job_active", "Job Active", "{{ value_json.job_in_progress }}", device_class="running")

    def send_telegram_notification(self, message):
        if not self.cfg.telegram_enabled:
            return

        url = f"https://api.telegram.org/bot{self.cfg.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.cfg.telegram_chat_id,
            "text": message
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code != 200:
                logging.error(f"Failed to send Telegram message: {response.text}")
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")

    def parse_response(self, line):
        """
        Parses a GRBL status line.
        Example: <Run|MPos:34.900,53.963,0.000|FS:1000,100|Ov:100,100,100|A:SF>
        Returns a dictionary with parsed data.
        """
        data = {"raw": line}
        
        # 1. State (Idle, Run, Alarm, etc.)
        state_match = re.search(r"^<([^|]+)\|", line)
        if state_match:
            data["state"] = state_match.group(1)
        else:
            return None

        # 2. Machine Position (MPos:x,y,z)
        mpos_match = re.search(r"MPos:([\d.-]+),([\d.-]+),([\d.-]+)", line)
        if mpos_match:
            data["mpos"] = {
                "x": float(mpos_match.group(1)),
                "y": float(mpos_match.group(2)),
                "z": float(mpos_match.group(3))
            }

        # 3. Feed and Spindle (FS:feed,spindle)
        fs_match = re.search(r"FS:(\d+),(\d+)", line)
        if fs_match:
            data["feed_rate"] = int(fs_match.group(1))
            data["spindle_speed"] = int(fs_match.group(2))
            # Calculate Laser Power Percentage
            # Ensure we don't divide by zero if config is weird, though default is 1000
            max_speed = self.cfg.max_spindle_speed if self.cfg.max_spindle_speed > 0 else 1000
            data["laser_power_pct"] = round((data["spindle_speed"] / max_speed) * 100, 1)
            
        # 4. Accessories (A:SF...)
        # S = Spindle On, F = Flood Coolant (Air Assist), M = Mist Coolant
        a_match = re.search(r"\|A:([^|>]+)", line)
        if a_match:
            acc_str = a_match.group(1)
            data["accessories"] = {
                "spindle_enabled": "S" in acc_str,
                "flood_coolant": "F" in acc_str,
                "mist_coolant": "M" in acc_str
            }
        else:
            data["accessories"] = {
                "spindle_enabled": False,
                "flood_coolant": False,
                "mist_coolant": False
            }

        # Derived status: Is the laser actually firing or framing?
        if data["state"] == "Run":
            spindle = data.get("spindle_speed", 0)
            coolant_on = data["accessories"]["flood_coolant"] or data["accessories"]["mist_coolant"]
            
            if spindle == 0:
                data["detailed_status"] = "Moving"
            else:
                # Spindle is ON (>0)
                # If Coolant is ON, it's likely a job (Lasering)
                # If Spindle > Threshold, it's likely a job (Lasering)
                # Otherwise, it's Framing
                if coolant_on or spindle > self.cfg.framing_threshold:
                    data["detailed_status"] = "Lasering"
                else:
                    data["detailed_status"] = "Framing"
        else:
            data["detailed_status"] = data["state"]

        return data

    def handle_state_change(self, parsed_data):
        current_state = parsed_data["state"]
        current_detailed = parsed_data.get("detailed_status", current_state)
        
        # Publish to MQTT
        if self.mqtt_client:
            # Add timestamp
            parsed_data["timestamp"] = time.time()
            # Add job status to MQTT
            parsed_data["job_in_progress"] = self.job_in_progress
            try:
                payload = json.dumps(parsed_data)
                self.mqtt_client.publish(self.cfg.mqtt_topic, payload)
            except Exception as e:
                logging.error(f"Error publishing to MQTT: {e}")

        # Job State Machine
        # 1. Start Job: If we hit "Lasering" and we weren't in a job.
        if current_detailed == "Lasering" and not self.job_in_progress:
            logging.info("Job Started! Sending notification...")
            self.job_in_progress = True
            self.send_telegram_notification(self.cfg.telegram_message_started)

        # 2. End Job: If we hit "Idle" and we WERE in a job.
        elif current_detailed == "Idle" and self.job_in_progress:
             logging.info("Job Completed! Sending notification...")
             self.job_in_progress = False
             self.send_telegram_notification(self.cfg.telegram_message_completed)
        
        # 3. Travel Moves (Moving):
        # If we are "Moving", we just stay in whatever job state we were in.
        # If job_in_progress was True, it stays True (traveling during job).
        # If job_in_progress was False, it stays False (jogging).

        self.last_state = current_state
        self.last_detailed_status = current_detailed

    def publish_offline_status(self):
        """Publishes an 'Offline' status to MQTT."""
        if self.mqtt_client:
            payload = {
                "state": "Offline",
                "detailed_status": "Offline",
                "job_in_progress": False,
                "timestamp": time.time()
            }
            try:
                logging.info("Publishing Offline status to MQTT...")
                self.mqtt_client.publish(self.cfg.mqtt_topic, json.dumps(payload))
            except Exception as e:
                logging.error(f"Error publishing Offline status: {e}")

    def run(self):
        logging.info(f"Connecting to {self.cfg.bluetooth_mac} on channel {self.cfg.rfcomm_port}...")
        
        while True:
            sock = None
            try:
                sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                sock.connect((self.cfg.bluetooth_mac, self.cfg.rfcomm_port))
                logging.info("Connected. Starting polling loop...")
                
                buffer = ""
                
                while True:
                    try:
                        sock.send(b"?\n")
                        
                        data = sock.recv(1024).decode('utf-8')
                        if not data:
                            logging.warning("Connection closed by remote device.")
                            self.publish_offline_status()
                            break
                            
                        buffer += data
                        
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if not line:
                                continue
                                
                            parsed_data = self.parse_response(line)
                            if parsed_data:
                                # Print a nice summary
                                status_str = f"State: {parsed_data['state']}"
                                if 'detailed_status' in parsed_data:
                                    status_str += f" ({parsed_data['detailed_status']})"
                                if 'mpos' in parsed_data:
                                    status_str += f" Pos: {parsed_data['mpos']['x']},{parsed_data['mpos']['y']}"
                                
                                if self.cfg.show_raw:
                                    status_str += f" | Raw: {line}"
                                    
                                logging.debug(status_str)
                                
                                self.handle_state_change(parsed_data)
                            elif line != "ok":
                                logging.debug(f"Response: {line}")
                        
                        time.sleep(self.cfg.polling_interval)
                        
                    except socket.error as e:
                        logging.error(f"Socket error: {e}")
                        self.publish_offline_status()
                        break
                        
            except socket.error as e:
                logging.error(f"Connection failed: {e}")
                self.publish_offline_status()
                logging.info(f"Retrying in 5 seconds...")
                time.sleep(5)
            except KeyboardInterrupt:
                logging.info("\nStopping...")
                break
            finally:
                if sock:
                    sock.close()
                if self.mqtt_client:
                    self.mqtt_client.loop_stop()
                
                if sys.exc_info()[0] == KeyboardInterrupt:
                    break

if __name__ == "__main__":
    monitor = LaserMonitor()
    monitor.run()
