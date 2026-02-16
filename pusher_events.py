#!/usr/bin/env python3
"""Pusher WebSocket client — listens for real-time box update events."""

import os
import json
import time
from dotenv import load_dotenv

try:
    import pysher
    PUSHER_AVAILABLE = True
except ImportError:
    print("pysher not found — install with: pip install pysher")
    PUSHER_AVAILABLE = False
    pysher = None

load_dotenv(".env.local")

PUSHER_APP_KEY = os.getenv("PUSHER_APP_KEY")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER", "us2")
PUSHER_CHANNEL = os.getenv("PUSHER_CHANNEL", "garden")


class PusherListener:
    def __init__(self, on_box_update_callback=None):
        self.on_box_update = on_box_update_callback
        self.pusher = None
        self.channel = None
        self.connected = False
        self._last_event_time = time.monotonic()

    def connect(self):
        if not PUSHER_AVAILABLE or not PUSHER_APP_KEY:
            print("Pusher not available or PUSHER_APP_KEY not set")
            return False
        try:
            # Clean up old connection first
            self.disconnect()

            self.pusher = pysher.Pusher(
                PUSHER_APP_KEY, cluster=PUSHER_CLUSTER, secure=True,
                reconnect_interval=5
            )
            self.pusher.connection.bind("pusher:connection_established", self._on_connect)
            self.pusher.connection.bind("pusher:connection_failed", self._on_connection_failed)
            self.pusher.connection.bind("pusher:error", self._on_error)
            self.pusher.connect()
            # Don't subscribe here — _on_connect will handle it once connected
            print(f"Connecting to Pusher (key: {PUSHER_APP_KEY[:8]}..., cluster: {PUSHER_CLUSTER})")
            # Wait for connection callback
            for _ in range(20):
                if self.connected:
                    break
                time.sleep(0.25)
            return self.connected
        except Exception as e:
            print(f"Error connecting to Pusher: {e}")
            return False

    def _subscribe(self):
        """Subscribe to channel and bind event handlers."""
        if self.pusher:
            self.channel = self.pusher.subscribe(PUSHER_CHANNEL)
            self.channel.bind("file-uploaded", self._on_file_event)
            self.channel.bind("file-deleted", self._on_file_event)

    def _on_connect(self, data):
        self.connected = True
        self._last_event_time = time.monotonic()
        print("Pusher connected")
        self._subscribe()

    def _on_connection_failed(self, data):
        self.connected = False
        print(f"Pusher connection failed: {data}")

    def _on_error(self, data):
        msg = str(data.get("message", "")) if isinstance(data, dict) else str(data)
        # Don't mark as disconnected for non-fatal errors (e.g. duplicate subscriptions)
        if "Existing subscription" not in msg:
            self.connected = False
        print(f"Pusher error: {data}")

    def _on_file_event(self, data):
        self._last_event_time = time.monotonic()
        try:
            if isinstance(data, str):
                data = json.loads(data)
            box_number = data.get("boxNumber")
            if box_number and self.on_box_update:
                print(f"Pusher event: updating box {box_number}")
                self.on_box_update(int(str(box_number).strip()))
        except Exception as e:
            print(f"Error processing Pusher event: {e}")

    def is_healthy(self):
        """Check if the connection appears healthy."""
        if not self.connected:
            return False
        # Also check the underlying websocket state if available
        try:
            ws = self.pusher.connection
            if hasattr(ws, 'state') and ws.state != "connected":
                self.connected = False
                return False
        except Exception:
            pass
        return True

    def disconnect(self):
        if self.pusher:
            try:
                self.pusher.disconnect()
            except Exception:
                pass
            self.pusher = None
        self.channel = None
        self.connected = False
