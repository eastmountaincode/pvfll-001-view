#!/usr/bin/env python3
"""
Pusher WebSocket client for PVFLL_001
Listens for real-time box update events
"""

import os
import json
import threading
import time
from dotenv import load_dotenv

# Try different pusher client packages
try:
    import pusherclient
    print("Using pusherclient package")
    PUSHER_AVAILABLE = True
except ImportError:
    try:
        from pusher_client_python import Pusher
        print("Using pusher_client_python package")
        PUSHER_AVAILABLE = True
        pusherclient = None
    except ImportError:
        print("Error: No Pusher client package found. Install with: pip3 install pusherclient")
        PUSHER_AVAILABLE = False
        pusherclient = None

# Load environment variables
load_dotenv('.env.local')

# Pusher configuration
PUSHER_APP_KEY = os.getenv("PUSHER_APP_KEY")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER", "us2")
PUSHER_CHANNEL = os.getenv("PUSHER_CHANNEL", "garden")

class PusherListener:
    def __init__(self, on_box_update_callback):
        """
        Initialize Pusher listener
        on_box_update_callback: function that takes (box_number) when an event occurs
        """
        self.on_box_update = on_box_update_callback
        self.pusher = None
        self.channel = None
        self.connected = False
        
    def connect(self):
        """Connect to Pusher and subscribe to the garden channel"""
        if not PUSHER_AVAILABLE:
            print("Warning: Pusher client not available. Real-time updates disabled.")
            return False
            
        if not PUSHER_APP_KEY:
            print("Warning: PUSHER_APP_KEY not set. Real-time updates disabled.")
            return False
            
        try:
            # Create Pusher client using pusherclient package
            if pusherclient:
                # pusherclient package API
                self.pusher = pusherclient.Pusher(PUSHER_APP_KEY)
                
                # Connection event handlers
                self.pusher.connection.bind('pusher:connection_established', self._on_connect)
                self.pusher.connection.bind('pusher:connection_failed', self._on_connection_failed)
                
                # Connect first
                self.pusher.connect()
                
                # Subscribe to the garden channel
                self.channel = self.pusher.subscribe(PUSHER_CHANNEL)
                
                # Bind to file events
                self.channel.bind('file-uploaded', self._on_file_event)
                self.channel.bind('file-deleted', self._on_file_event)
            else:
                # Alternative pusher package API
                self.pusher = Pusher(
                    key=PUSHER_APP_KEY,
                    cluster=PUSHER_CLUSTER,
                    secure=True
                )
                
                self.pusher.connection.bind('pusher:connection_established', self._on_connect)
                self.pusher.connection.bind('pusher:connection_failed', self._on_connection_failed)
                
                self.channel = self.pusher.subscribe(PUSHER_CHANNEL)
                self.channel.bind('file-uploaded', self._on_file_event)
                self.channel.bind('file-deleted', self._on_file_event)
                
                self.pusher.connect()
            
            print(f"Connecting to Pusher (key: {PUSHER_APP_KEY[:8]}..., cluster: {PUSHER_CLUSTER})")
            return True
            
        except Exception as e:
            print(f"Error connecting to Pusher: {e}")
            return False
    
    def _on_connect(self, data):
        """Called when Pusher connection is established"""
        self.connected = True
        print("✓ Pusher connected - listening for real-time updates")
        
    def _on_connection_failed(self, data):
        """Called when Pusher connection fails"""
        print(f"✗ Pusher connection failed: {data}")
        self.connected = False
    
    def _on_file_event(self, data):
        """Called when a file event (upload/delete) occurs"""
        try:
            print(f"📡 Pusher event received: {data}")
            
            # Extract box number from the event data
            box_number = data.get('boxNumber')
            if box_number:
                box_num = int(str(box_number).strip())
                print(f"🔄 Updating box {box_num}...")
                
                # Call the callback to update this box
                if self.on_box_update:
                    self.on_box_update(box_num)
            else:
                print("Warning: No boxNumber in event data")
                
        except Exception as e:
            print(f"Error processing Pusher event: {e}")
    
    def disconnect(self):
        """Disconnect from Pusher"""
        if self.pusher:
            try:
                self.pusher.disconnect()
                print("Pusher disconnected")
            except Exception as e:
                print(f"Error disconnecting from Pusher: {e}")
        self.connected = False

# Test function
if __name__ == "__main__":
    def test_callback(box_number):
        print(f"TEST: Box {box_number} needs updating!")
    
    listener = PusherListener(test_callback)
    
    if listener.connect():
        print("Pusher test running... upload/delete files to see events")
        print("Press Ctrl+C to exit")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            listener.disconnect()
    else:
        print("Failed to connect to Pusher")
