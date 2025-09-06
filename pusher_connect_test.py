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

# pusherclient supports overriding the websocket host via custom_host
# Modern endpoints are ws-<cluster>.pusher.com (wss on port 443)
def cluster_ws_host(cluster: str) -> str:
    cluster = (cluster or "").strip()
    if not cluster:
        return "ws.pusherapp.com"          # legacy default
    return f"ws-{cluster}.pusher.com"       # e.g., ws-us2.pusher.com, ws-mt1.pusher.com

try:
    import pusherclient
except Exception as e:
    raise SystemExit("Install deps first: pip install pusherclient websocket-client python-dotenv") from e

def on_subscription_succeeded(data):
    print(f"✓ Subscribed to '{PUSHER_CHANNEL}'")

def on_file_event(payload):
    # pusherclient passes JSON string; parse if needed
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            pass
    print(f"📡 Event payload: {payload}")

def on_connected(_data):
    print("✓ Connected to Pusher, subscribing…")
    chan = pusher.subscribe(PUSHER_CHANNEL)
    chan.bind('pusher:subscription_succeeded', on_subscription_succeeded)
    chan.bind('file-uploaded', on_file_event)
    chan.bind('file-deleted', on_file_event)

def on_connection_failed(info):
    print(f"✗ Connection failed: {info}")
    print(f"    key={PUSHER_APP_KEY[:8]}…  cluster={PUSHER_CLUSTER}  host={HOST}")

HOST = cluster_ws_host(PUSHER_CLUSTER)
print(f"Connecting with key={PUSHER_APP_KEY[:8]}…  cluster={PUSHER_CLUSTER}  host={HOST}")

# Create client; note the custom_host for cluster routing
pusher = pusherclient.Pusher(
    PUSHER_APP_KEY,
    secure=True,
    custom_host=HOST
)

# Wire connection events
pusher.connection.bind('pusher:connection_established', on_connected)
pusher.connection.bind('pusher:connection_failed', on_connection_failed)
pusher.connection.bind('pusher:error', lambda e: print(f"✗ Pusher error: {e}"))

# Connect and keep process alive
pusher.connect()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Bye")
