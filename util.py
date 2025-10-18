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
    """Check if Wi-Fi is connected and has an IP address (no sudo required)."""
    import datetime
    log_file = "/tmp/wifi_check.log"
    
    try:
        with open(log_file, "a") as log:
            log.write(f"\n--- WiFi Check at {datetime.datetime.now()} ---\n")
            
            interface = "wlan0"  # default wireless interface
            
            # Check if connected to an access point using iwgetid (works without sudo)
            iwgetid_result = subprocess.run(
                ["iwgetid", interface, "-r"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            log.write(f"iwgetid command: iwgetid {interface} -r\n")
            log.write(f"iwgetid stdout: '{iwgetid_result.stdout}'\n")
            log.write(f"iwgetid stderr: '{iwgetid_result.stderr}'\n")
            log.write(f"iwgetid returncode: {iwgetid_result.returncode}\n")
            
            # If iwgetid returns an SSID, we're connected to an AP
            ssid = iwgetid_result.stdout.strip()
            log.write(f"SSID detected: '{ssid}'\n")
            
            if not ssid:
                log.write("Result: No SSID - returning False\n")
                return False
            
            # Verify we have an IP address on the wireless interface
            ip_result = subprocess.run(
                ["ip", "-4", "addr", "show", interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            log.write(f"ip command: ip -4 addr show {interface}\n")
            log.write(f"ip stdout:\n{ip_result.stdout}\n")
            log.write(f"ip stderr: '{ip_result.stderr}'\n")
            log.write(f"ip returncode: {ip_result.returncode}\n")
            
            # Check if there's an inet (IPv4) address assigned
            found_ip = False
            for line in ip_result.stdout.splitlines():
                if "inet " in line and "127.0.0.1" not in line:
                    log.write(f"Found IP line: {line}\n")
                    found_ip = True
                    break
            
            if found_ip:
                log.write("Result: Connected with IP - returning True\n")
                return True
            else:
                log.write("Result: No IP address found - returning False\n")
                return False
            
    except Exception as e:
        try:
            with open(log_file, "a") as log:
                log.write(f"Exception occurred: {type(e).__name__}: {str(e)}\n")
                log.write("Result: Exception - returning False\n")
        except:
            pass
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