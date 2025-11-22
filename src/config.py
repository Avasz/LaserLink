import os
import yaml

class Config:
    def __init__(self, config_path="config.yaml"):
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}

        # Laser
        laser_cfg = self.config.get('laser', {})
        self.bluetooth_mac = os.getenv("BLUETOOTH_MAC", laser_cfg.get('bluetooth_mac'))
        self.rfcomm_port = int(os.getenv("RFCOMM_PORT", laser_cfg.get('rfcomm_port', 1)))
        self.polling_interval = float(os.getenv("POLLING_INTERVAL", laser_cfg.get('polling_interval', 0.5)))
        self.framing_threshold = int(os.getenv("FRAMING_THRESHOLD", laser_cfg.get('framing_threshold', 20)))
        self.max_spindle_speed = int(os.getenv("MAX_SPINDLE_SPEED", laser_cfg.get('max_spindle_speed', 1000)))
        self.show_raw = os.getenv("SHOW_RAW", str(laser_cfg.get('show_raw', False))).lower() in ('true', '1', 'yes')
        self.log_level = os.getenv("LOG_LEVEL", laser_cfg.get('log_level', 'INFO')).upper()

        # MQTT
        mqtt_cfg = self.config.get('mqtt', {})
        self.mqtt_enabled = os.getenv("MQTT_ENABLED", str(mqtt_cfg.get('enabled', False))).lower() in ('true', '1', 'yes')
        self.mqtt_broker = os.getenv("MQTT_BROKER", mqtt_cfg.get('broker', 'localhost'))
        self.mqtt_port = int(os.getenv("MQTT_PORT", mqtt_cfg.get('port', 1883)))
        self.mqtt_topic = os.getenv("MQTT_TOPIC", mqtt_cfg.get('topic', 'laser/status'))
        self.mqtt_username = os.getenv("MQTT_USERNAME", mqtt_cfg.get('username'))
        self.mqtt_password = os.getenv("MQTT_PASSWORD", mqtt_cfg.get('password'))

        # Home Assistant
        ha_cfg = self.config.get('homeassistant', {})
        self.ha_enabled = os.getenv("HA_ENABLED", str(ha_cfg.get('enabled', False))).lower() in ('true', '1', 'yes')
        self.ha_discovery_prefix = os.getenv("HA_DISCOVERY_PREFIX", ha_cfg.get('discovery_prefix', 'homeassistant'))
        self.ha_node_id = os.getenv("HA_NODE_ID", ha_cfg.get('node_id', 'laserlink'))
        self.ha_device_name = os.getenv("HA_DEVICE_NAME", ha_cfg.get('device_name', 'Laser Cutter'))

        # Telegram
        tele_cfg = self.config.get('telegram', {})
        self.telegram_enabled = os.getenv("TELEGRAM_ENABLED", str(tele_cfg.get('enabled', False))).lower() in ('true', '1', 'yes')
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", tele_cfg.get('bot_token'))
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", tele_cfg.get('chat_id'))
        self.telegram_message_started = os.getenv("TELEGRAM_MESSAGE_STARTED", tele_cfg.get('message_started', "Laser Job Started!"))
        self.telegram_message_completed = os.getenv("TELEGRAM_MESSAGE_COMPLETED", tele_cfg.get('message_completed', "Laser Job Completed!"))

    def validate(self):
        if not self.bluetooth_mac or self.bluetooth_mac == "XX:XX:XX:XX:XX:XX":
            return False, "BLUETOOTH_MAC is missing or default in config.yaml."
        if self.mqtt_enabled and not self.mqtt_broker:
            return False, "MQTT enabled but broker address missing."
        if self.telegram_enabled and (not self.telegram_token or not self.telegram_chat_id):
            return False, f"Telegram enabled but token or chat_id missing. (Token: {self.telegram_token}, ChatID: {self.telegram_chat_id})"
        return True, ""
