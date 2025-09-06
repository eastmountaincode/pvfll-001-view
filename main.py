#!/usr/bin/env python3
"""
PVFLL_001 Display Controller
Main entry point for the e-ink display system
"""

import time
import signal
import sys
import threading
from api import fetch_all_boxes, fetch_box_status
from display import init_display, display_boxes, clear_display, sleep_display
from pusher_client import PusherListener

# Global state
running = True
current_box_data = {}
data_lock = threading.Lock()
pusher_listener = None

def signal_handler(sig, frame):
    """Handle Ctrl+C and other shutdown signals"""
    global running, pusher_listener
    print("\nShutting down gracefully...")
    running = False
    
    # Disconnect Pusher
    if pusher_listener:
        pusher_listener.disconnect()
    
    print("Clearing display...")
    clear_display()
    sleep_display()
    sys.exit(0)

def update_single_box(box_number):
    """Update a single box and refresh the display"""
    global current_box_data
    
    try:
        # Fetch updated data for this box
        new_data = fetch_box_status(box_number)
        
        # Update our state
        with data_lock:
            current_box_data[box_number] = new_data
            # Make a copy for display (to avoid holding the lock)
            display_data = dict(current_box_data)
        
        # Update the display
        print(f"📺 Refreshing display for box {box_number}")
        display_boxes(display_data)
        
    except Exception as e:
        print(f"Error updating box {box_number}: {e}")

def main():
    """Main application loop"""
    global running, current_box_data, pusher_listener
    
    print("=== PVFLL_001 Display System ===")
    print("Starting up...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    # Initialize display
    print("Initializing display...")
    init_display()
    
    # Initial fetch and display
    print("Fetching initial box status...")
    try:
        box_data = fetch_all_boxes()
        
        # Store initial data
        with data_lock:
            current_box_data = box_data
        
        print("Displaying initial status...")
        display_boxes(box_data)
    except Exception as e:
        print(f"Error during initial fetch/display: {e}")
        return
    
    # Set up Pusher for real-time updates
    print("Setting up real-time updates...")
    pusher_listener = PusherListener(on_box_update_callback=update_single_box)
    
    if pusher_listener.connect():
        print("✓ Real-time updates enabled")
    else:
        print("⚠ Real-time updates disabled (continuing without Pusher)")
    
    print("System ready! Press Ctrl+C to exit.")
    print("Display will update automatically when files are uploaded/downloaded.")
    
    # Main loop - just keep alive
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
