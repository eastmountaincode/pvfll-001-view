#!/usr/bin/env python3
import os, json, time
from dotenv import load_dotenv

# Load your keys from .env.local
load_dotenv('.env.local')

PUSHER_APP_KEY = os.getenv("PUSHER_APP_KEY")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER", "us2")  # e.g., mt1, us2, eu, ap2, etc.
PUSHER_CHANNEL = os.getenv("PUSHER_CHANNEL", "garden")

if not PUSHER_APP_KEY:
    raise SystemExit("PUSHER_APP_KEY missing. Put it in .env.local")

try:
    import pysher
except Exception as e:
    raise SystemExit("Install deps first: pip install pysher python-dotenv") from e

def on_connect(data):
    print("✓ Connected to Pusher")

def on_subscription_succeeded(data):
    print(f"✓ Subscribed to '{PUSHER_CHANNEL}'")

def on_file_event(data):
    print(f"📡 Event received: {data}")

def on_error(error):
    print(f"✗ Pusher error: {error}")

def on_connection_state_change(previous_state, current_state):
    print(f"Connection state: {previous_state} → {current_state}")

print(f"Connecting with key={PUSHER_APP_KEY[:8]}…  cluster={PUSHER_CLUSTER}")

# Create pysher client
pusher = pysher.Pusher(
    PUSHER_APP_KEY,
    cluster=PUSHER_CLUSTER,
    secure=True
)

# Wire connection events
pusher.connection.bind('pusher:connection_established', on_connect)
pusher.connection.bind('pusher:connection_failed', on_error)
pusher.connection.bind('pusher:error', on_error)

# Connect
pusher.connect()

# Subscribe to channel
channel = pusher.subscribe(PUSHER_CHANNEL)
channel.bind('pusher:subscription_succeeded', on_subscription_succeeded)
channel.bind('file-uploaded', on_file_event)
channel.bind('file-deleted', on_file_event)

print(f"Listening for events on channel '{PUSHER_CHANNEL}'...")
print("Upload or delete files to see real-time events!")

# Keep alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nDisconnecting...")
    pusher.disconnect()
    print("Bye")
