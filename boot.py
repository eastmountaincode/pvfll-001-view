import time
from display import init_display, display_centered_message
from util import is_wifi_connected
from api import fetch_all_boxes
from pusher_events import PusherListener


def boot_sequence() -> tuple:
    """
    Run the boot sequence with these steps:
      1. Initialize display
      2. Check Wi-Fi connectivity
      3. Connect to WebSocket (Pusher)
      4. Fetch initial data
    Displays status messages on the e-ink screen.

    Returns:
        (dict, PusherListener): initial box data and Pusher listener object.
    """

    # Step 1: Initialize display
    try:
        init_display()
        display_centered_message("Booting system...", font_size=32)
        time.sleep(1)
    except Exception as e:
        print(f"Error initializing display: {e}")
        return {}, None

    # Step 2: Check Wi-Fi
    display_centered_message("Checking Wi-Fi...", font_size=28)
    if not is_wifi_connected():
        display_centered_message("No Wi-Fi: Please restart", font_size=28)
        print("⚠ No Wi-Fi connection detected. Please restart system.")
        return None, None  # Signal boot failure

    # Step 3: Connect to WebSocket
    display_centered_message("Connecting to WebSocket...", font_size=28)
    pusher_listener = PusherListener(on_box_update_callback=None)  # Main will set the callback later
    if pusher_listener.connect():
        display_centered_message("WebSocket connected", font_size=28)
        print("WebSocket connection established.")
    else:
        display_centered_message("WebSocket failed: Please restart", font_size=24)
        print("⚠ Failed to connect to WebSocket. Please restart system.")
        return None, None  # Signal boot failure

    # Step 4: Fetch initial data
    display_centered_message("Fetching data...", font_size=28)
    try:
        box_data = fetch_all_boxes()
        display_centered_message("Boot complete!", font_size=28)
        print("Initial data fetched successfully.")
        time.sleep(1)
        return box_data, pusher_listener
    except Exception as e:
        display_centered_message("Data fetch failed: Please restart", font_size=24)
        print(f"Error during initial fetch: {e}. Please restart system.")
        return None, None  # Signal boot failure
