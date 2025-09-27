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

def is_wifi_connected():
    """Check if the device is connected to Wi-Fi (via NetworkManager)"""
    try:
        # Uses nmcli to check if we have a connection
        result = subprocess.run(
            ["nmcli", "-t", "-f", "STATE", "g"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return "connected" in result.stdout.strip()
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