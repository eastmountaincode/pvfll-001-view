#!/usr/bin/env python3
"""
PVFLL_001 Display Controller
Main entry point for the e-ink display system
"""

import time
import signal
import sys
from api import fetch_all_boxes
from display import init_display, display_boxes, clear_display, sleep_display

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C and other shutdown signals"""
    global running
    print("\nShutting down gracefully...")
    running = False
    print("Clearing display...")
    clear_display()
    sleep_display()
    sys.exit(0)

def main():
    """Main application loop"""
    global running
    
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
        print("Displaying initial status...")
        display_boxes(box_data)
    except Exception as e:
        print(f"Error during initial fetch/display: {e}")
        return
    
    print("System ready! Press Ctrl+C to exit.")
    print("Current status displayed. Real-time updates coming in next step...")
    
    # For now, just keep the program running
    # Later we'll add Pusher here to listen for real-time updates
    try:
        while running:
            time.sleep(1)  # Just keep alive for now
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
