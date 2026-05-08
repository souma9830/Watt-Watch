import paho.mqtt.client as mqtt
import time
import json
from typing import Dict, Any, Optional

class MQTTManager:
    """
    Manages MQTT connections and publishing for CamSense.ai automation.
    Connects to the public HiveMQ broker for demo purposes.
    """
    
    def __init__(self, broker: str = "broker.hivemq.com", port: int = 1883, client_id: Optional[str] = None):
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"camsense-client-{int(time.time())}"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        
        # Room states to avoid redundant publishing
        self._last_state = {} # room_id -> 'ON'/'OFF'
        self._connected = False
        
    def connect(self) :
        """Connect to the MQTT broker."""
        try:
            print(f"Connecting to MQTT Broker: {self.broker}...")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start() # Start background thread for network traffic
            self._connected = True
            print("Successfully connected to MQTT broker")
            
            # Send a power-on signal to confirm link (Retained)
            self.client.publish("camsense/status", "CAM_SENSE_SYSTEM_ONLINE", qos=1, retain=True)
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            self._connected = False
            return False
            
    def publish_control(self, room_id: str, action: str):
        """
        Publish a control message (TURN_ON / TURN_OFF).
        Only publishes if the state has changed.
        Uses RETAIN=True so the state persists even after a browser refresh.
        """
        if not self._connected:
            return
            
        # Topic matches room ID for multi-room support
        topic = f"camsense/{room_id}/control"
        # Alias topic for easy general demo
        alias_topic = "camsense/control"
        
        # Avoid redundant commands
        if self._last_state.get(room_id) == action:
            return
            
        print(f"[MQTT] Publishing action '{action}' (RETAINED) to topics: {topic}, {alias_topic}")
        
        # Publish to specific room (RETAIN=True)
        self.client.publish(topic, action, qos=1, retain=True)
        # Publish to general control topic (RETAIN=True)
        self.client.publish(alias_topic, action, qos=1, retain=True)
        
        # Log it centrally (RETAIN=True)
        self.client.publish("camsense/status", f"AUTO_CMD: {room_id} status changed to {action}", qos=1, retain=True)
        
        self._last_state[room_id] = action

    def disconnect(self):
        """Disconnect from broker."""
        self.client.loop_stop()
        self.client.disconnect()
        self._connected = False
