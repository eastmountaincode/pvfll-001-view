import subprocess
import mimetypes


def is_wifi_connected() -> bool:
    """Check if wlan0 has an IPv4 address assigned (works without NetworkManager)."""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        for line in result.stdout.splitlines():
            if "inet " in line and "127.0.0.1" not in line:
                return True
        return False
    except Exception:
        return False


def format_size(bytes_value):
    """Format file size in human-readable form."""
    if bytes_value is None or bytes_value == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    size = float(bytes_value)
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{int(size)} {units[i]}" if i == 0 else f"{size:.1f} {units[i]}"


def get_file_type(filename: str) -> str:
    """Get friendly file type from filename extension."""
    if not filename:
        return "Unknown"
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        if mime_type.startswith("image/"):
            return f"Image ({mime_type.split('/')[-1].upper()})"
        elif mime_type.startswith("text/"):
            return f"Text ({mime_type.split('/')[-1].upper()})"
        elif mime_type.startswith("audio/"):
            return f"Audio ({mime_type.split('/')[-1].upper()})"
        elif mime_type.startswith("video/"):
            return f"Video ({mime_type.split('/')[-1].upper()})"
        elif "pdf" in mime_type:
            return "PDF"
        elif "zip" in mime_type or "compressed" in mime_type:
            return "Archive"
        else:
            return mime_type
    ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "Unknown"
    return f".{ext}" if ext != "Unknown" else "Unknown"
