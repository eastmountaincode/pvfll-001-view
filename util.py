import subprocess
import mimetypes


def format_size(bytes_value):
    """Format file size - copied from api.py for consistency"""
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

import subprocess

def is_wifi_connected() -> bool:
    """Check if Wi-Fi is connected and has an IP address."""
    try:
        # Get the device name for wifi (usually wlan0)
        dev_result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in dev_result.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 3:
                device, dev_type, state = parts[0], parts[1], parts[2]
                if dev_type == "wifi" and state == "connected":
                    # Check for a valid IP address on this device
                    ip_result = subprocess.run(
                        ["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", device],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if ip_result.stdout.strip():
                        return True
        return False
    except Exception:
        return False


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