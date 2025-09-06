#!/usr/bin/env python3
"""
E-ink display module for PVFLL_001
Handles rendering box status to the 7.5" Waveshare display
"""

import sys
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any

# Add the waveshare library path (adjust if needed)
libdir = "/home/virtual/pvfll/e-Paper/RaspberryPi_JetsonNano/python/lib"
if os.path.exists(libdir):
    sys.path.append(libdir)

try:
    from waveshare_epd import epd7in5_V2
except ImportError:
    print("Warning: waveshare_epd not found. Display functions will be mocked.")
    epd7in5_V2 = None

# Global display object
epd = None
fonts_loaded = False
font_title = None
font_box_number = None
font_text = None
full_refresh_counter = 0
FULL_REFRESH_INTERVAL = 10  # Do full refresh every 10 updates

def init_display():
    """Initialize the e-ink display"""
    global epd, fonts_loaded, font_title, font_box_number, font_text
    
    if epd7in5_V2 is None:
        print("[MOCK] Display initialized (no hardware)")
        return
    
    try:
        epd = epd7in5_V2.EPD()
        epd.init()
        epd.Clear()
        print("E-ink display initialized")
    except Exception as e:
        print(f"Error initializing display: {e}")
        return
    
    # Load fonts
    try:
        # Try to load system fonts (adjust paths as needed)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        # Make box numbers much larger and bolder (font-black equivalent)
        font_box_number = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        fonts_loaded = True
        print("Fonts loaded")
    except Exception as e:
        print(f"Font loading failed, using default: {e}")
        font_title = ImageFont.load_default()
        font_box_number = ImageFont.load_default()
        font_text = ImageFont.load_default()
        fonts_loaded = True

def clear_display():
    """Clear the display completely"""
    if epd:
        try:
            epd.Clear()
            print("Display cleared")
        except Exception as e:
            print(f"Error clearing display: {e}")
    else:
        print("[MOCK] Display cleared")

def sleep_display():
    """Put the display to sleep"""
    if epd:
        try:
            epd.sleep()
            print("Display sleeping")
        except Exception as e:
            print(f"Error putting display to sleep: {e}")
    else:
        print("[MOCK] Display sleeping")

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
    
    # Define the content area below the box number
    content_top = y + padding + 60
    content_height = height - (padding + 60 + padding)  # Available height for content
    content_width = width - (2 * padding)  # Available width for content
    content_center_x = x + width // 2  # Horizontal center of the box
    
    if box_data.get("error"):
        # Center error message
        error_text = "ERROR"
        error_msg = str(box_data["error"])[:30] + "..." if len(str(box_data["error"])) > 30 else str(box_data["error"])
        
        # Calculate vertical center for 2 lines
        line_height = 25
        total_text_height = line_height * 2
        start_y = content_top + (content_height - total_text_height) // 2
        
        # Center horizontally
        error_bbox = draw.textbbox((0, 0), error_text, font=font_text)
        error_width = error_bbox[2] - error_bbox[0]
        draw.text((content_center_x - error_width // 2, start_y), error_text, font=font_text, fill=0)
        
        msg_bbox = draw.textbbox((0, 0), error_msg, font=font_text)
        msg_width = msg_bbox[2] - msg_bbox[0]
        draw.text((content_center_x - msg_width // 2, start_y + line_height), error_msg, font=font_text, fill=0)
        
    elif box_data.get("empty", True):
        # Center "Empty" text
        empty_text = "Empty"
        empty_bbox = draw.textbbox((0, 0), empty_text, font=font_text)
        empty_width = empty_bbox[2] - empty_bbox[0]
        empty_height = empty_bbox[3] - empty_bbox[1]
        
        # Center both horizontally and vertically
        text_x = content_center_x - empty_width // 2
        text_y = content_top + (content_height - empty_height) // 2
        draw.text((text_x, text_y), empty_text, font=font_text, fill=0)
        
    else:
        # File info - center the block of text
        name = box_data.get("name", "Unknown")
        file_type = box_data.get("type", "Unknown")
        size = format_size(box_data.get("size", 0))
        
        # Truncate long filenames
        if len(name) > 20:
            name = name[:17] + "..."
        
        # Prepare the lines
        lines = [
            f"File: {name}",
            f"Type: {file_type}",
            f"Size: {size}"
        ]
        
        # Calculate total height of text block
        line_height = 22
        total_text_height = line_height * len(lines)
        start_y = content_top + (content_height - total_text_height) // 2
        
        # Draw each line centered
        for i, line in enumerate(lines):
            line_bbox = draw.textbbox((0, 0), line, font=font_text)
            line_width = line_bbox[2] - line_bbox[0]
            text_x = content_center_x - line_width // 2
            text_y = start_y + (i * line_height)
            draw.text((text_x, text_y), line, font=font_text, fill=0)

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

def display_boxes(box_data: Dict[int, Dict[str, Any]], force_full_refresh=False):
    """Main function to display box data on e-ink screen"""
    global full_refresh_counter
    
    print("Rendering display...")
    
    # Create the image
    image = create_layout_image(box_data)
    
    if epd:
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
    else:
        # Mock mode - no hardware available
        print("Display rendered (no hardware available)")

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
