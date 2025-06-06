#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import threading
import logging

# Nastavenie loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/museum-mqtt.log')
        #sudo touch /var/log/museum-mqtt.log
        #sudo chown pi:pi /var/log/museum-mqtt.log
        #sudo chmod 664 /var/log/museum-mqtt.log
    ]
)
logger = logging.getLogger('mqtt_client')

class MQTTClient:
    def __init__(self, broker_ip, client_id="rpi_controller", port=1883, use_logging=True):
        self.client = mqtt.Client(client_id)
        self.broker_ip = broker_ip
        self.port = port
        self.connected = False
        self.stopping = False
        self.reconnect_thread = None
        self.reconnect_delay = 5  # sekundy
        self.max_reconnect_delay = 300  # max 5 minút
        self.use_logging = use_logging
        
        # Setup callback functions
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
    def log_info(self, message):
        if self.use_logging:
            logger.info(message)
        else:
            print(message)
            
    def log_warning(self, message):
        if self.use_logging:
            logger.warning(message)
        else:
            print(f"WARNING: {message}")
            
    def log_error(self, message):
        if self.use_logging:
            logger.error(message)
        else:
            print(f"ERROR: {message}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log_info(f"Pripojené k MQTT brokeru na {self.broker_ip}")
            self.connected = True
            self.reconnect_delay = 5  # reset delay po úspešnom pripojení
        else:
            self.log_error(f"Nepodarilo sa pripojiť k MQTT brokeru, návratový kód: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        self.log_warning("Odpojené od MQTT brokera")
        self.connected = False
        
        # Automatické opätovné pripojenie, ak nejde o úmyselné zastavenie
        if not self.stopping and self.reconnect_thread is None:
            self.reconnect_thread = threading.Thread(target=self.reconnect_loop)
            self.reconnect_thread.daemon = True
            self.reconnect_thread.start()
    
    def reconnect_loop(self):

        while not self.connected and not self.stopping:
            self.log_info(f"Pokus o opätovné pripojenie k MQTT za {self.reconnect_delay} sekúnd...")
            time.sleep(self.reconnect_delay)
            
            try:
                self.client.reconnect()
                # Ak sa dostaneme sem bez výnimky, on_connect sa spustí samostatne
            except Exception as e:
                self.log_error(f"Chyba pri pokuse o opätovné pripojenie: {e}")
                # Zvýš interval pre ďalší pokus (exponenciálny backoff)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
        self.reconnect_thread = None
        
    def connect(self):
        try:
            self.client.connect(self.broker_ip, self.port, 60)
            self.client.loop_start()
            # Počkaj na pripojenie
            for _ in range(5):
                if self.connected:
                    return True
                time.sleep(1)
            
            # Ak sme sa nedostali sem, začni automatické opätovné pripojenie
            if not self.connected and self.reconnect_thread is None:
                self.reconnect_thread = threading.Thread(target=self.reconnect_loop)
                self.reconnect_thread.daemon = True
                self.reconnect_thread.start()
            
            return self.connected
        except Exception as e:
            self.log_error(f"Chyba pri pripájaní k MQTT brokeru: {e}")
            
            # Začni automatické opätovné pripojenie
            if self.reconnect_thread is None:
                self.reconnect_thread = threading.Thread(target=self.reconnect_loop)
                self.reconnect_thread.daemon = True
                self.reconnect_thread.start()
            
            return False
    
    def publish(self, topic, message, retain=False):

        if not self.connected:
            self.log_warning(f"Nie je pripojené k MQTT brokeru, správa do {topic} nebola odoslaná")
            return False
        
        result = self.client.publish(topic, message, retain=retain)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            self.log_info(f"Správa publikovaná do {topic}: {message}")
            return True
        else:
            self.log_error(f"Chyba pri publikovaní správy: {result.rc}")
            return False
    
    def subscribe(self, topic, callback=None):

        if callback:
            # Nastav lokálny callback pre túto tému
            self.client.message_callback_add(topic, callback)
        
        self.client.subscribe(topic)
        self.log_info(f"Prihlásené na odber témy: {topic}")
    
    def disconnect(self):
        self.stopping = True
        self.client.loop_stop()
        self.client.disconnect()
        self.log_info("MQTT klient odpojený")

# Example usage
if __name__ == "__main__":
    client = MQTTClient("localhost", use_logging=False)  # MQTT broker address
    if client.connect():
        client.publish("test/topic", "Test message")
        time.sleep(2)
        client.disconnect()
