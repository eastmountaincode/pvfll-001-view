#!/usr/bin/env python3
"""
E-ink display module for PVFLL_001
Handles rendering box status to the 7.5" Waveshare display
"""

import sys
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Tuple
from util import format_size

# Add the waveshare library path (adjust if needed)
libdir = "/home/virtual/pvfll/e-Paper/RaspberryPi_JetsonNano/python/lib"
if os.path.exists(libdir):
    sys.path.append(libdir)

try:
    from waveshare_epd import epd7in5_V2
except ImportError:
    raise ImportError(
        "waveshare_epd not found. Install the Waveshare e-Paper Python library and ensure lib path is correct."
    )

# Global display object
epd = None
fonts_loaded = False
font_title = None
font_box_number = None
font_text = None
full_refresh_counter = 0
FULL_REFRESH_INTERVAL = 10  # Do full refresh every 10 updates
file_icon = None

# Font configuration and cache
FONT_PATH_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_font_cache: Dict[Tuple[bool, int], ImageFont.ImageFont] = {}

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Return a cached PIL ImageFont for the given size and weight."""
    key = (bold, size)
    if key in _font_cache:
        return _font_cache[key]
    try:
        path = FONT_PATH_BOLD if bold else FONT_PATH_REGULAR
        font = ImageFont.truetype(path, size)
    except Exception:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font

def load_file_icon():
    """Load the SVG file icon using cairosvg"""
    global file_icon
    try:
        import cairosvg
        from io import BytesIO
        
        # Convert SVG to PNG with completely transparent background
        png_data = cairosvg.svg2png(
            url="images/file-regular-full.svg", 
            output_width=48, 
            output_height=48,
            background_color="rgba(0,0,0,0)"  # Fully transparent background
        )
        icon = Image.open(BytesIO(png_data))
        
        # Create a pure white background
        white_bg = Image.new('RGB', (64, 64), (255, 255, 255))
        
        # If icon has transparency, handle it properly
        if icon.mode == 'RGBA':
            # Create a mask from the alpha channel
            mask = icon.split()[-1]  # Get alpha channel
            # Paste only the RGB part with the alpha mask
            white_bg.paste(icon.convert('RGB'), (0, 0), mask)
        else:
            white_bg.paste(icon, (0, 0))
        
        # Convert to 1-bit for e-ink
        # For draw.bitmap(), we need 0=draw, 255=transparent
        # So we need to invert: black icon parts should be 0, white background should be 255
        bw_icon = white_bg.convert('1')
        
        # Create inverted version for bitmap drawing
        from PIL import ImageOps
        file_icon = ImageOps.invert(bw_icon)
        print(f"File icon loaded: {file_icon.mode}, size: {file_icon.size}")
        print("File icon loaded from SVG")
        return True
        
    except ImportError:
        print("cairosvg not available - install with: pip install cairosvg")
        return False
    except Exception as e:
        print(f"Error loading SVG icon: {e}")
        return False

def init_display():
    """Initialize the e-ink display"""
    global epd, fonts_loaded, font_title, font_box_number, font_text
    
    if epd7in5_V2 is None:
        raise RuntimeError("Waveshare e-Paper display library not available.")
    
    try:
        epd = epd7in5_V2.EPD()
        epd.init()
        epd.Clear()
        print("E-ink display initialized")
    except Exception as e:
        print(f"Error initializing display: {e}")
        return
    
    # Load fonts (and warm cache)
    font_title = get_font(32, bold=True)
    # Make box numbers much larger and bolder (font-black equivalent)
    font_box_number = get_font(48, bold=True)
    font_text = get_font(18, bold=False)
    fonts_loaded = True
    print("Fonts loaded")
    
    # Load file icon
    load_file_icon()

def clear_display():
    """Clear the display completely to white"""
    if epd is None:
        raise RuntimeError("Display not initialized. Call init_display() first.")
    try:
        # Create a white image and display it to ensure white background
        white_image = Image.new('1', (epd.width, epd.height), 255)  # 255 = white
        epd.display(epd.getbuffer(white_image))
        print("Display cleared to white")
    except Exception as e:
        print(f"Error clearing display: {e}")

def sleep_display():
    """Put the display to sleep"""
    if epd is None:
        raise RuntimeError("Display not initialized. Call init_display() first.")
    try:
        epd.sleep()
        print("Display sleeping")
    except Exception as e:
        print(f"Error putting display to sleep: {e}")

def force_full_refresh():
    """Force the next display update to use full refresh"""
    global full_refresh_counter
    full_refresh_counter = FULL_REFRESH_INTERVAL

def create_layout_image(box_data: Dict[int, Dict[str, Any]]) -> Image.Image:
    """Create the layout image showing all box statuses"""
    
    # Display dimensions (7.5" is 800x480)
    width = 800 if epd else 800
    height = 480 if epd else 480
    
    # Create image (1-bit for e-ink: 0=black, 255=white)
    image = Image.new('1', (width, height), 255)
    draw = ImageDraw.Draw(image)
    
    # Title
    title = "✿ pvfll_001 ✿"
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 20), title, font=font_title, fill=0)
    
    # Box layout - 2x2 grid
    margin = 10
    box_width = (width - 3 * margin) // 2
    box_height = (height - 120 - 3 * margin) // 2
    
    positions = [
        (margin, 80),  # Box 1: top-left
        (margin + box_width + margin, 80),  # Box 2: top-right
        (margin, 80 + box_height + margin),  # Box 3: bottom-left
        (margin + box_width + margin, 80 + box_height + margin)  # Box 4: bottom-right
    ]
    
    for i, box_num in enumerate([1, 2, 3, 4]):
        x, y = positions[i]
        draw_box(draw, x, y, box_width, box_height, box_num, box_data.get(box_num, {"empty": True}))
    
    return image

def draw_box(draw, x, y, width, height, box_num, box_data):
    """Draw a single box with its status"""
    
    # Box border
    draw.rectangle((x, y, x + width, y + height), outline=0, width=2)
    
    # Box number - just the number, large and bold (font-black style)
    padding = 10
    draw.text((x + padding, y + padding), str(box_num), font=font_box_number, fill=0)
    
    # File icon in upper right if there's a file
    if not box_data.get("empty", True) and file_icon:
        icon_x = x + width - file_icon.width + 7 
        icon_y = y + padding
        # Draw the file icon using bitmap (simpler approach)
        draw.bitmap((icon_x, icon_y), file_icon, fill=0)
    
    # Status - adjust position for larger box number
    text_y = y + padding + 60
    
    if box_data.get("error"):
        draw.text((x + padding, text_y), "ERROR", font=font_text, fill=0)
        text_y += 25
        # Truncate long error messages
        error_msg = str(box_data["error"])[:30] + "..." if len(str(box_data["error"])) > 30 else str(box_data["error"])
        draw.text((x + padding, text_y), error_msg, font=font_text, fill=0)
        
    elif box_data.get("empty", True):
        draw.text((x + padding, text_y), "Empty", font=font_text, fill=0)
        
    else:
        # File info
        name = box_data.get("name", "Unknown")
        file_type = box_data.get("type", "Unknown")
        size = format_size(box_data.get("size", 0))
        
        # Truncate long filenames
        if len(name) > 30:
            name = name[:27] + "..."
        
        draw.text((x + padding, text_y), f"File: {name}", font=font_text, fill=0)
        text_y += 22
        draw.text((x + padding, text_y), f"Type: {file_type}", font=font_text, fill=0)
        text_y += 22
        draw.text((x + padding, text_y), f"Size: {size}", font=font_text, fill=0)

def display_boxes(box_data: Dict[int, Dict[str, Any]], force_full_refresh=False):
    """Main function to display box data on e-ink screen"""
    global full_refresh_counter
    
    print("Rendering display...")
    
    # Create the image
    image = create_layout_image(box_data)
    
    if epd is None:
        raise RuntimeError("Display not initialized. Call init_display() first.")
    # Display on actual e-ink
    try:
        # Decide whether to do full or partial refresh
        full_refresh_counter += 1
        use_full_refresh = force_full_refresh or (full_refresh_counter >= FULL_REFRESH_INTERVAL)
        
        if use_full_refresh:
            # Full refresh (with black flash) - clears ghosting
            print("Display: Full refresh")
            epd.init()  # Re-initialize for full refresh
            epd.display(epd.getbuffer(image))
            full_refresh_counter = 0
        else:
            # Partial refresh (no flash) - faster updates
            print("Display: Partial refresh")
            try:
                # Try partial refresh mode
                epd.init_part()
                epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)
            except AttributeError:
                # Fallback if partial refresh not available
                print("Partial refresh not available, using full refresh")
                epd.init()
                epd.display(epd.getbuffer(image))
                
        print("Display updated successfully")
    except Exception as e:
        print(f"Error updating display: {e}")

def display_centered_message(message: str, font_size: int = 32, bold: bool = True, full_refresh: bool = True) -> None:
    """Display a single centered text message on the e-ink screen.

    Args:
        message: The text message to display (single line recommended).
        font_size: Font size in points (default 32).
        bold: Whether to use the bold font variant when available.
        full_refresh: If True, use full refresh (with flash). If False, use partial refresh (faster, no flash).
    """
    if epd is None:
        raise RuntimeError("Display not initialized. Call init_display() first.")

    # Create a white canvas
    width, height = epd.width, epd.height
    image = Image.new('1', (width, height), 255)
    draw = ImageDraw.Draw(image)

    # Choose font from cache
    font = get_font(font_size, bold=bold)

    # Measure text and center
    bbox = draw.textbbox((0, 0), message, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2
    draw.text((x, y), message, font=font, fill=0)

    # Display with chosen refresh mode
    try:
        if full_refresh:
            # Full refresh (with black flash) - clears ghosting
            epd.init()
            epd.display(epd.getbuffer(image))
            print("Centered message displayed (full refresh)")
        else:
            # Partial refresh (no flash) - faster updates
            try:
                epd.init_part()
                epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)
                print("Centered message displayed (partial refresh)")
            except AttributeError:
                # Fallback if partial refresh not available
                print("Partial refresh not available, using full refresh")
                epd.init()
                epd.display(epd.getbuffer(image))
    except Exception as e:
        print(f"Error displaying centered message: {e}")

# Test function
if __name__ == "__main__":
    # Test with mock data
    test_data = {
        1: {"empty": True},
        2: {"empty": False, "name": "test_image.jpg", "type": "Image (JPEG)", "size": 1234567},
        3: {"empty": False, "name": "very_long_filename_that_will_be_truncated.pdf", "type": "PDF", "size": 987654},
        4: {"empty": True, "error": "Connection timeout"}
    }
    
    init_display()
    display_boxes(test_data)
    sleep_display()
