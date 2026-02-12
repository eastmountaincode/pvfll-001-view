#!/usr/bin/env python3
"""
PVFLL_001 Display Controller
Main entry point for the e-ink display system
"""

import time
import signal
import sys
import threading
import requests
from datetime import datetime, timezone
from api import fetch_box_status, fetch_all_boxes, API_BASE, HTTP_TIMEOUT
from display import display_boxes, clear_display, sleep_display
from boot import boot_sequence

# Health-check intervals (seconds)
CONNECTION_CHECK_INTERVAL = 60
SYNC_POLL_INTERVAL = 300  # 5 minutes

# Global state
running = True
current_box_data = {}
data_lock = threading.Lock()
pusher_listener = None


def log(msg):
    """Print with timestamp for journalctl debugging."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def signal_handler(sig, frame):
    """Handle Ctrl+C and other shutdown signals"""
    global running, pusher_listener
    log("Shutting down gracefully...")
    running = False

    # Disconnect Pusher
    if pusher_listener:
        pusher_listener.disconnect()

    log("Clearing display...")
    try:
        clear_display()
    except Exception as e:
        log(f"Error during display cleanup: {e}")
    finally:
        sleep_display()
    sys.exit(0)


def sync_poll():
    """Fetch all box statuses via REST API and update display if anything changed."""
    global current_box_data
    try:
        log("Sync poll: fetching all box statuses...")
        fresh_data = fetch_all_boxes()

        with data_lock:
            if fresh_data != current_box_data:
                log("Sync poll: data changed, refreshing display")
                current_box_data = fresh_data
                display_boxes(dict(current_box_data))
            else:
                log("Sync poll: no changes")
    except Exception as e:
        log(f"Sync poll error: {e}")


def report_health(connected: bool):
    """POST device heartbeat to the API. Fire-and-forget."""
    try:
        url = f"{API_BASE}/devices/health"
        payload = {
            "deviceId": "pvfll-001",
            "connected": connected,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        requests.post(url, json=payload, timeout=HTTP_TIMEOUT)
        log("Health reported OK")
    except Exception as e:
        log(f"Health report failed: {e}")


def main():
    """Main application loop"""
    global running, current_box_data, pusher_listener

    log("=== PVFLL_001 Display System ===")

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    # Boot handles display init, Wi-Fi, WebSocket, and initial data fetch
    initial_data, pusher_listener = boot_sequence()

    # Check if boot failed
    if initial_data is None:
        log("Boot sequence failed. System halted.")
        log("Please restart the system to try again.")
        # Stay in loop to keep the error message on display
        try:
            while running:
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(None, None)
        return

    # Store initial data
    with data_lock:
        current_box_data = initial_data

    # Display initial status
    log("Displaying initial status...")
    display_boxes(initial_data)

    # Attach callback AFTER boot finishes
    if pusher_listener:
        def on_box_update(box_number: int):
            """Fetch fresh data for one box via API and refresh the display."""
            try:
                new_data = fetch_box_status(box_number)
                with data_lock:
                    current_box_data[box_number] = new_data
                    display_data = dict(current_box_data)
                log(f"Refreshing display for box {box_number}")
                display_boxes(display_data)
            except Exception as e:
                log(f"Error updating box {box_number}: {e}")

        pusher_listener.on_box_update = on_box_update
        log("Real-time updates enabled")
    else:
        log("Real-time updates disabled")

    # Main loop - health check + sync poll + health report
    log("System ready. Monitoring connection health.")
    last_connection_check = time.monotonic()
    last_sync_poll = time.monotonic()
    last_health_report = time.monotonic()

    try:
        while running:
            time.sleep(1)
            now = time.monotonic()

            # Connection health check every 60s
            if pusher_listener and now - last_connection_check >= CONNECTION_CHECK_INTERVAL:
                last_connection_check = now
                if not pusher_listener.connected:
                    log("Connection lost — attempting reconnect...")
                    try:
                        pusher_listener.connect()
                        log("Reconnect initiated")
                        # Re-sync after reconnect to catch missed events
                        sync_poll()
                        last_sync_poll = now
                    except Exception as e:
                        log(f"Reconnect failed — will retry in 60s: {e}")

            # Sync poll every 5 minutes
            if now - last_sync_poll >= SYNC_POLL_INTERVAL:
                last_sync_poll = now
                sync_poll()

            # Health report every 60s
            if now - last_health_report >= CONNECTION_CHECK_INTERVAL:
                last_health_report = now
                connected = pusher_listener.connected if pusher_listener else False
                report_health(connected)

    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
