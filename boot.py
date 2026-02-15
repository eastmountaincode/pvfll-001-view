import time
from display import init_display, display_centered_message, display_portal_message, load_file_icon
from util import is_wifi_connected
from api import fetch_all_boxes
from pusher_events import PusherListener

WIFI_RETRY_INTERVAL = 10  # seconds between WiFi checks


def boot_sequence() -> tuple:
    """
    Boot sequence:
      1. Initialize display + load file icon
      2. Check Wi-Fi connectivity (wait with portal message if not connected)
      3. Connect to Pusher WebSocket
      4. Fetch initial box data
    Returns (box_data, pusher_listener) or (None, None) on failure.
    """

    # Step 1: Initialize display
    try:
        init_display()
        load_file_icon()
        display_centered_message("Booting...", font_size=32)
        time.sleep(1)
    except Exception as e:
        print(f"Error initializing display: {e}")
        return None, None

    # Step 2: Check Wi-Fi — show portal instructions and retry until connected
    display_centered_message("Checking Wi-Fi...", font_size=28)
    if not is_wifi_connected():
        print("No Wi-Fi — showing captive portal instructions")
        display_portal_message()
        while not is_wifi_connected():
            time.sleep(WIFI_RETRY_INTERVAL)
        print("Wi-Fi connected!")
        display_centered_message("Wi-Fi connected!", font_size=28)
        time.sleep(1)

    # Step 3: Connect to Pusher
    display_centered_message("Connecting to WebSocket...", font_size=24)
    pusher_listener = PusherListener()
    if pusher_listener.connect():
        print("WebSocket connected")
    else:
        display_centered_message("WebSocket failed", font_size=28)
        print("Failed to connect to WebSocket")
        return None, None

    # Step 4: Fetch initial data
    display_centered_message("Fetching data...", font_size=28)
    try:
        box_data = fetch_all_boxes()
        display_centered_message("Boot complete!", font_size=28)
        time.sleep(1)
        return box_data, pusher_listener
    except Exception as e:
        display_centered_message("Data fetch failed", font_size=28)
        print(f"Error fetching data: {e}")
        return None, None
