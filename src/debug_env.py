import os
import sys
from config import Config

def mask_secret(secret):
    if not secret:
        return "MISSING/EMPTY"
    if len(secret) < 8:
        return "***"
    return secret[:3] + "***" + secret[-3:]

def main():
    print("--- Environment Variable Check ---")
    print(f"BLUETOOTH_MAC: {os.getenv('BLUETOOTH_MAC', 'Not Set')}")
    print(f"TELEGRAM_BOT_TOKEN: {mask_secret(os.getenv('TELEGRAM_BOT_TOKEN'))}")
    print(f"TELEGRAM_CHAT_ID: {mask_secret(os.getenv('TELEGRAM_CHAT_ID'))}")
    print(f"MQTT_PASSWORD: {mask_secret(os.getenv('MQTT_PASSWORD'))}")
    
    print("\n--- Loaded Configuration ---")
    try:
        cfg = Config()
        print(f"Config File: config.yaml (Exists: {os.path.exists('config.yaml')})")
        print(f"Telegram Enabled: {cfg.telegram_enabled}")
        print(f"Telegram Token: {mask_secret(cfg.telegram_token)}")
        print(f"Telegram Chat ID: {mask_secret(cfg.telegram_chat_id)}")
        
        valid, msg = cfg.validate()
        print(f"\nValidation Result: {'PASS' if valid else 'FAIL'}")
        if not valid:
            print(f"Error: {msg}")
            
    except Exception as e:
        print(f"Error loading config: {e}")

if __name__ == "__main__":
    main()
