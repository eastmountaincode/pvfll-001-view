#!/usr/bin/env python3
"""
E-ink display module for PVFLL_001
Renders box status to a 7.5" Waveshare e-ink display (800x480)
"""

import sys
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps
from typing import Dict, Any, Tuple

# Waveshare library path
libdir = "/home/virtual/pvfll/e-Paper/RaspberryPi_JetsonNano/python/lib"
if os.path.exists(libdir):
    sys.path.append(libdir)

try:
    from waveshare_epd import epd7in5_V2
except ImportError:
    epd7in5_V2 = None

# Display dimensions (7.5" is 800x480)
WIDTH = 800
HEIGHT = 480

# Global state
epd = None
file_icon = None

# Font config — DejaVuSans on Pi, Arial fallback on macOS
FONT_PATH_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_PATH_REGULAR_FALLBACK = "/Library/Fonts/Arial.ttf"
FONT_PATH_BOLD_FALLBACK = "/Library/Fonts/Arial Bold.ttf"
# Matisse EB (Evangelion font) for header — bundled in fonts/
FONT_PATH_MATISSE = os.path.join(os.path.dirname(__file__), "fonts", "EVA-Matisse_Classic.ttf")
# Los Angeles (classic Mac font) for subtitle
FONT_PATH_LOS_ANGELES = os.path.join(os.path.dirname(__file__), "fonts", "LosAngeles.ttf")
_font_cache: Dict[Tuple[bool, int], ImageFont.ImageFont] = {}


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (bold, size)
    if key in _font_cache:
        return _font_cache[key]
    primary = FONT_PATH_BOLD if bold else FONT_PATH_REGULAR
    fallback = FONT_PATH_BOLD_FALLBACK if bold else FONT_PATH_REGULAR_FALLBACK
    for path in [primary, fallback]:
        try:
            font = ImageFont.truetype(path, size)
            _font_cache[key] = font
            return font
        except Exception:
            continue
    font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def init_display():
    global epd
    if epd7in5_V2 is None:
        print("Waveshare library not available, running in image-only mode")
        return
    try:
        epd = epd7in5_V2.EPD()
        epd.init()
        epd.Clear()
        print("E-ink display initialized (7.5\" 800x480)")
    except Exception as e:
        print(f"Error initializing display: {e}")


def clear_display():
    if epd is None:
        return
    try:
        white = Image.new('1', (WIDTH, HEIGHT), 255)
        epd.init()
        epd.display(epd.getbuffer(white))
        print("Display cleared")
    except Exception as e:
        print(f"Error clearing display: {e}")


def sleep_display():
    if epd is None:
        return
    try:
        epd.sleep()
        print("Display sleeping")
    except Exception as e:
        print(f"Error sleeping display: {e}")


def format_size(bytes_value):
    if bytes_value is None or bytes_value == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    size = float(bytes_value)
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{int(size)} {units[i]}" if i == 0 else f"{size:.1f} {units[i]}"


def load_file_icon(icon_size: int = 48):
    """Load the SVG file icon using cairosvg."""
    global file_icon
    try:
        import cairosvg
        from io import BytesIO

        # Render at 4x then downscale for clean edges
        render_size = icon_size * 4
        svg_path = os.path.join(os.path.dirname(__file__), "images", "file-regular-full.svg")
        png_data = cairosvg.svg2png(
            url=svg_path,
            output_width=render_size,
            output_height=render_size,
            background_color="rgba(0,0,0,0)",
        )
        icon = Image.open(BytesIO(png_data))

        # Composite onto white background at high res
        white_bg = Image.new('RGB', (render_size, render_size), (255, 255, 255))
        if icon.mode == 'RGBA':
            mask = icon.split()[-1]
            white_bg.paste(icon.convert('RGB'), (0, 0), mask)
        else:
            white_bg.paste(icon, (0, 0))

        # Downscale with LANCZOS, then threshold to clean 1-bit (no dithering)
        scaled = white_bg.resize((icon_size, icon_size), Image.LANCZOS)
        gray = scaled.convert('L')
        bw = gray.point(lambda p: 255 if p > 128 else 0, mode='1')
        # Invert for draw.bitmap (0=draw, 255=skip)
        file_icon = ImageOps.invert(bw)
        print(f"File icon loaded: {file_icon.size}")
        return True

    except ImportError:
        print("cairosvg not available — install with: pip install cairosvg")
        return False
    except Exception as e:
        print(f"Error loading SVG icon: {e}")
        return False


def draw_box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int,
             box_num: int, box_data: Dict[str, Any],
             pad_x: int = 12, pad_y: int = 8,
             icon_pad_x: int = 5, icon_pad_y: int = 8,
             text_pad_x: int = 14):
    """Draw a single box cell."""
    font_num = get_font(48, bold=True)
    font_info = get_font(18)
    font_label = get_font(18, bold=True)
    font_source = get_font(14)  # Smaller font for source info

    # Border
    draw.rectangle((x, y, x + w, y + h), outline=0, width=2)

    has_file = not box_data.get("empty", True) and not box_data.get("error")

    # Box number
    draw.text((x + pad_x, y + pad_y), str(box_num), font=font_num, fill=0)

    # File icon in upper right if there's a file
    if has_file and file_icon:
        icon_x = x + w - file_icon.width - icon_pad_x
        icon_y = y + icon_pad_y
        draw.bitmap((icon_x, icon_y), file_icon, fill=0)

    # Source library info — two lines, left-aligned next to number
    source = box_data.get("source")
    if has_file and source:
        source_name = source.get("name", "")
        source_city = source.get("city", "")
        
        if source_name:
            num_bbox_src = draw.textbbox((0, 0), str(box_num), font=font_num)
            num_width = num_bbox_src[2] - num_bbox_src[0]
            
            # Left-aligned, right of number, nudged down slightly
            source_x = x + pad_x + num_width + 10
            source_y = y + pad_y + 8
            line_spacing = 16
            
            # Measure "from " width for indent
            from_width = draw.textbbox((0, 0), "from ", font=font_source)[2]
            
            # Line 1: "from" + library name
            draw.text((source_x, source_y), "from", font=font_source, fill=0)
            draw.text((source_x + from_width, source_y), source_name, font=font_source, fill=0)
            
            # Line 2: city (indented to align with name)
            if source_city:
                draw.text((source_x + from_width, source_y + line_spacing), source_city, font=font_source, fill=0)

    # Status text below the number
    num_bbox = draw.textbbox((0, 0), "1", font=font_num)
    text_y = y + pad_y + num_bbox[3] + 12
    line_h = 22

    if box_data.get("error"):
        draw.text((x + text_pad_x, text_y), "ERROR", font=font_info, fill=0)
        msg = str(box_data["error"])[:30]
        draw.text((x + text_pad_x, text_y + line_h), msg, font=font_info, fill=0)

    elif box_data.get("empty", True):
        draw.text((x + text_pad_x, text_y), "Empty", font=font_info, fill=0)

    else:
        name = box_data.get("name", "?")
        if len(name) > 30:
            name = name[:27] + "..."
        file_type = box_data.get("type", "")
        size = format_size(box_data.get("size", 0))
        for i, (label, value) in enumerate([("File: ", name), ("Type: ", file_type), ("Size: ", size)]):
            lx = x + text_pad_x
            ly = text_y + line_h * i
            draw.text((lx, ly), label, font=font_label, fill=0)
            label_w = draw.textbbox((0, 0), label, font=font_label)[2]
            draw.text((lx + label_w, ly), value, font=font_info, fill=0)


def make_qr_image(url: str, size: int) -> Image.Image:
    """Generate a 1-bit QR code image at the given pixel size."""
    qr = qrcode.QRCode(box_size=1, border=0, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('1')
    return img.resize((size, size), Image.NEAREST)


def create_layout_image(box_data: Dict[int, Dict[str, Any]],
                        qr_url: str = "https://htmlpg.andrew-boylan.com") -> Image.Image:
    """Create the full layout image for the 7.5\" display."""
    image = Image.new('1', (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(image)

    margin = 12

    # --- Header spacing controls (scaled up from 002's 4.2" layout) ---
    qr_size = 120
    qr_text_gap = 14       # horizontal gap between QR code and title/subtitle
    title_top_offset = 2   # title vertical nudge from top margin
    title_sub_gap = 6      # vertical gap between title and subtitle

    # --- Header row: QR code on left, title text on right ---
    qr_img = make_qr_image(qr_url, qr_size)
    image.paste(qr_img, (margin, margin))

    # Title text — Matisse EB with vertical stretch
    try:
        font_header = ImageFont.truetype(FONT_PATH_MATISSE, 38)
    except Exception:
        font_header = get_font(34, bold=True)
    header_text = "HTML Pollinator Garden"
    text_x = margin + qr_size + qr_text_gap
    hbb = draw.textbbox((0, 0), header_text, font=font_header)
    text_w = hbb[2] - hbb[0]
    text_h = hbb[3] - hbb[1]

    # Render to temp image, stretch to half QR height
    stretch_height = qr_size // 2
    text_img = Image.new('1', (text_w, text_h), 255)
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((-hbb[0], -hbb[1]), header_text, font=font_header, fill=0)
    stretched = text_img.resize((text_w, stretch_height), Image.NEAREST)
    image.paste(stretched, (text_x, margin + title_top_offset))

    # Subtitle in Los Angeles below the title
    try:
        font_sub = ImageFont.truetype(FONT_PATH_LOS_ANGELES, 38)
    except Exception:
        font_sub = get_font(26)
    subtitle_text = "Take a file. Leave a file. "
    sub_y = margin + stretch_height + title_sub_gap
    draw.text((text_x, sub_y), subtitle_text, font=font_sub, fill=0)

    # --- 2x2 grid below header ---
    top_offset = margin + qr_size + margin
    box_w = (WIDTH - 3 * margin) // 2
    box_h = (HEIGHT - top_offset - 2 * margin) // 2

    positions = [
        (margin, top_offset),
        (margin + box_w + margin, top_offset),
        (margin, top_offset + box_h + margin),
        (margin + box_w + margin, top_offset + box_h + margin),
    ]

    for i, num in enumerate([1, 2, 3, 4]):
        x, y = positions[i]
        draw_box(draw, x, y, box_w, box_h, num, box_data.get(num, {"empty": True}))

    # Invert for dark mode (white on black)
    image = ImageOps.invert(image)

    return image


def display_boxes(box_data: Dict[int, Dict[str, Any]], force_full=False, qr_url: str = None):
    """Render box data to the e-ink display."""
    kwargs = {}
    if qr_url:
        kwargs["qr_url"] = qr_url
    image = create_layout_image(box_data, **kwargs)

    if epd is None:
        # No hardware — save to file for preview
        image.save("preview.png")
        print("Preview saved to preview.png")
        return

    try:
        if force_full:
            epd.init()
            epd.display(epd.getbuffer(image))
            print("Display updated (full refresh)")
        else:
            try:
                epd.init_part()
                epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)
                print("Display updated (partial refresh)")
            except AttributeError:
                epd.init()
                epd.display(epd.getbuffer(image))
                print("Display updated (full refresh fallback)")
    except Exception as e:
        print(f"Error updating display: {e}")


def display_centered_message(message: str, font_size: int = 28, bold: bool = True,
                             full_refresh: bool = False):
    """Show a single centered message (for boot status, errors, etc.)."""
    image = Image.new('1', (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(image)
    font = get_font(font_size, bold=bold)

    bbox = draw.textbbox((0, 0), message, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((WIDTH - tw) // 2, (HEIGHT - th) // 2), message, font=font, fill=0)

    if epd is None:
        image.save("preview.png")
        print(f"Preview saved: {message}")
        return

    try:
        if full_refresh:
            epd.init()
            epd.display(epd.getbuffer(image))
        else:
            try:
                epd.init_part()
                epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)
            except AttributeError:
                epd.init()
                epd.display(epd.getbuffer(image))
    except Exception as e:
        print(f"Error displaying message: {e}")


def display_portal_message():
    """Show captive portal instructions when WiFi is not connected."""
    image = Image.new('1', (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(image)

    lines = [
        (get_font(32, bold=True), "No WiFi"),
        (get_font(20), ""),
        (get_font(20), "To configure, connect to"),
        (get_font(20), "this device's WiFi:"),
        (get_font(20), ""),
        (get_font(24, bold=True), 'Network: "pvfll_001"'),
        (get_font(24, bold=True), "Password: htmlpg2025"),
        (get_font(20), ""),
        (get_font(18), "A setup page will appear,"),
        (get_font(18), "or go to 192.168.4.1"),
    ]

    # Calculate total height
    total_h = 0
    line_metrics = []
    for font, text in lines:
        if text == "":
            h = 12  # blank line spacing
        else:
            bbox = draw.textbbox((0, 0), text, font=font)
            h = bbox[3] - bbox[1] + 6
        line_metrics.append(h)
        total_h += h

    y = (HEIGHT - total_h) // 2
    for i, (font, text) in enumerate(lines):
        if text == "":
            y += line_metrics[i]
            continue
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((WIDTH - tw) // 2, y), text, font=font, fill=0)
        y += line_metrics[i]

    # Dark mode
    image = ImageOps.invert(image)

    if epd is None:
        image.save("preview.png")
        print("Preview saved: portal message")
        return

    try:
        try:
            epd.init_part()
            epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)
        except AttributeError:
            epd.init()
            epd.display(epd.getbuffer(image))
    except Exception as e:
        print(f"Error displaying portal message: {e}")


# Test function
if __name__ == "__main__":
    test_data = {
        1: {"empty": True},
        2: {
            "empty": False,
            "name": "test_image.jpg",
            "type": "Image (JPEG)",
            "size": 1234567,
            "source": {"name": "Headrest Coffee", "city": "NYC"}
        },
        3: {
            "empty": False,
            "name": "very_long_filename_that_will_be_truncated.pdf",
            "type": "PDF",
            "size": 987654,
            "source": {"name": "BK Heights LFL", "city": "Brooklyn"}
        },
        4: {"empty": True, "error": "Connection timeout"}
    }

    init_display()
    load_file_icon()
    display_boxes(test_data)
    sleep_display()
