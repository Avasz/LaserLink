import time
import paho.mqtt.client as mqtt
from config import Config

def clear_mqtt():
    cfg = Config("config.yaml")
    valid, msg = cfg.validate()
    if not valid:
        print(f"Config error: {msg}")
        return

    client = mqtt.Client()
    if cfg.mqtt_username and cfg.mqtt_password:
        client.username_pw_set(cfg.mqtt_username, cfg.mqtt_password)

    try:
        client.connect(cfg.mqtt_broker, cfg.mqtt_port, 60)
        client.loop_start()
        print("Connected to MQTT Broker.")
        time.sleep(1) # Wait for connection
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # List of all possible sensors (old and new) to clear
    # We use the configured prefix and node_id
    prefix = cfg.ha_discovery_prefix
    node_id = cfg.ha_node_id
    
    sensors = [
        "status",
        "spindle_speed", # Old
        "feed_rate",     # Old
        "pos_x",
        "pos_y",
        "pos_z",         # Old
        "laser_power",   # New
        "speed"          # New
    ]
    
    binary_sensors = [
        "job_active"
    ]

    print("Clearing topics...")

    for s in sensors:
        topic = f"{prefix}/sensor/{node_id}/{s}/config"
        print(f"Clearing {topic}")
        client.publish(topic, "", retain=True)
        
    for s in binary_sensors:
        topic = f"{prefix}/binary_sensor/{node_id}/{s}/config"
        print(f"Clearing {topic}")
        client.publish(topic, "", retain=True)

    print("Done. Waiting for messages to send...")
    time.sleep(2)
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    clear_mqtt()
