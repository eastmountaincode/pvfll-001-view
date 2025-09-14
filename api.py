#!/usr/bin/env python3
"""
Simple API client to fetch box status from pvfll_001 Next.js app
"""

import requests
import json
import os
import mimetypes
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import time

# Load environment variables from .env.local
load_dotenv('.env.local')

# Configuration
API_BASE = os.getenv("API_BASE")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT"))

def get_file_type(filename: str) -> str:
    """Get file type from filename extension"""
    if not filename:
        return "Unknown"
    
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        # Convert MIME type to friendly name
        if mime_type.startswith('image/'):
            return f"Image ({mime_type.split('/')[-1].upper()})"
        elif mime_type.startswith('text/'):
            return f"Text ({mime_type.split('/')[-1].upper()})"
        elif mime_type.startswith('audio/'):
            return f"Audio ({mime_type.split('/')[-1].upper()})"
        elif mime_type.startswith('video/'):
            return f"Video ({mime_type.split('/')[-1].upper()})"
        elif 'pdf' in mime_type:
            return "PDF"
        elif 'zip' in mime_type or 'compressed' in mime_type:
            return "Archive"
        else:
            return mime_type
    else:
        # Fallback to extension
        ext = filename.split('.')[-1].upper() if '.' in filename else "Unknown"
        return f".{ext}" if ext != "Unknown" else "Unknown"

def fetch_box_status(box_number: int, retries: int = 5, delay: int = 3) -> Dict[str, Any]:
    """
    Fetch the status of a single box with retries
    """
    url = f"{API_BASE}/boxes/{box_number}/files"

    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            # Ensure we always have an 'empty' field
            data.setdefault("empty", True)

            # Add file type if we have a filename
            if not data.get("empty") and data.get("name"):
                data["type"] = get_file_type(data["name"])

            return data

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{retries} failed for box {box_number}: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"All attempts failed for box {box_number}. Marking as empty.")
                return {"empty": True, "error": str(e)}


def fetch_all_boxes() -> Dict[int, Dict[str, Any]]:
    """
    Fetch status of all 4 boxes
    Returns: {1: {...}, 2: {...}, 3: {...}, 4: {...}}
    """
    boxes = [1, 2, 3, 4]
    results = {}
    
    for box_num in boxes:
        print(f"Fetching box {box_num}...")
        results[box_num] = fetch_box_status(box_num)
    
    return results

def format_size(bytes_value: Optional[int]) -> str:
    """Helper to format file size in human readable format"""
    if bytes_value is None or bytes_value == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB"]
    size = float(bytes_value)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"

def print_box_status(box_data: Dict[int, Dict[str, Any]]):
    """Pretty print the box status for testing"""
    print("\n" + "="*50)
    print("PVFLL_001 BOX STATUS")
    print("="*50)
    
    for box_num in sorted(box_data.keys()):
        data = box_data[box_num]
        print(f"\nBox {box_num}:")
        
        if data.get("error"):
            print(f"  ERROR: {data['error']}")
        elif data.get("empty", True):
            print("  Status: Empty")
        else:
            print("  Status: Has file")
            print(f"  Name: {data.get('name', 'Unknown')}")
            print(f"  Type: {data.get('type', 'Unknown')}")
            print(f"  Size: {format_size(data.get('size'))}")

# Test function - run this file directly to test the API
if __name__ == "__main__":
    print("Testing PVFLL_001 API connection...")
    print(f"API Base: {API_BASE}")
    
    # Fetch all boxes
    all_boxes = fetch_all_boxes()
    
    # Print results
    print_box_status(all_boxes)
    
    # Also print raw JSON for debugging
    print("\nRaw JSON data:")
    print(json.dumps(all_boxes, indent=2))
