import requests
from requests.auth import HTTPDigestAuth
import time
import re
import struct
import io
import urllib.parse

CAMERA_IP = "172.27.34.173"
USERNAME = "root"
PASSWORD = "pass"
auth = HTTPDigestAuth(USERNAME, PASSWORD)

BASE_PTZ = f"http://{CAMERA_IP}/axis-cgi/com/ptz.cgi"
BASE_PARAM = f"http://{CAMERA_IP}/axis-cgi/param.cgi"
BASE_OVERLAY = f"http://{CAMERA_IP}/axis-cgi/dynamicoverlay/dynamicoverlay.cgi"
BASE_UPLOAD = f"http://{CAMERA_IP}/axis-cgi/uploadoverlayimage.cgi"


# ======================== HELPERS ========================

def vapix_get(url, **kwargs):
    resp = requests.get(url, auth=auth, timeout=10, **kwargs)
    return resp

def vapix_post(url, **kwargs):
    resp = requests.post(url, auth=auth, timeout=10, **kwargs)
    return resp

def set_params(params_str):
    """Update camera parameters via param.cgi."""
    url = f"{BASE_PARAM}?action=update&{params_str}"
    resp = vapix_get(url)
    return resp.text.strip()

def get_params(group):
    """List camera parameters for a group."""
    resp = vapix_get(f"{BASE_PARAM}?action=list&group={group}")
    return resp.text.strip()


# ======================== PTZ ========================

def get_position():
    resp = vapix_get(f"{BASE_PTZ}?query=position")
    resp.raise_for_status()
    m = re.search(r"pan=(-?[\d.]+)", resp.text)
    return float(m.group(1)) if m else None

def move_to(pan, speed=30):
    resp = vapix_get(f"{BASE_PTZ}?pan={pan}&speed={speed}")
    resp.raise_for_status()

def normalize_pan(angle):
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return round(angle, 1)


# ======================== PRIVACY MASKS ========================

def add_privacy_masks():
    """Add 10 privacy masks at different positions on the image."""
    print("\n" + "=" * 55)
    print("  ADDING 10 PRIVACY MASKS")
    print("=" * 55)

    # Window coordinates: left, top, right, bottom (0-10000 = 0-100%)
    masks = [
        ("Shield_TopLeft_1",     "0,0,1200,1200",          "black"),
        ("Shield_TopLeft_2",     "1400,0,2600,1200",       "white"),
        ("Shield_TopRight_1",    "7400,0,8600,1200",       "mosaic"),
        ("Shield_TopRight_2",    "8800,0,10000,1200",      "black"),
        ("Shield_BottomLeft_1",  "0,8800,1200,10000",      "white"),
        ("Shield_BottomLeft_2",  "1400,8800,2600,10000",   "mosaic"),
        ("Shield_BottomRight_1", "7400,8800,8600,10000",   "black"),
        ("Shield_BottomRight_2", "8800,8800,10000,10000",  "white"),
        ("Shield_CenterLeft",    "0,4400,1200,5600",       "mosaic"),
        ("Shield_CenterRight",   "8800,4400,10000,5600",   "black"),
    ]

    for i, (name, window, color) in enumerate(masks):
        params = (
            f"PrivacyMask.M{i}.Name={name}"
            f"&PrivacyMask.M{i}.Window={window}"
            f"&PrivacyMask.M{i}.Color={color}"
            f"&PrivacyMask.M{i}.Enabled=yes"
        )
        result = set_params(params)
        ok = "OK" in result
        print(f"  [{i}] {name:25s} color={color:6s}  {'OK' if ok else result}")

    print(f"\n  -> 10 privacy masks configured.")


# ======================== OVERLAYS ========================

def create_small_bmp(width=80, height=30, r=255, g=0, b=0):
    """Create a minimal 24-bit BMP image in memory."""
    row_size = (width * 3 + 3) & ~3
    pixel_data_size = row_size * height
    file_size = 54 + pixel_data_size

    buf = io.BytesIO()
    # BMP header
    buf.write(b'BM')
    buf.write(struct.pack('<I', file_size))
    buf.write(struct.pack('<HH', 0, 0))
    buf.write(struct.pack('<I', 54))
    # DIB header
    buf.write(struct.pack('<I', 40))
    buf.write(struct.pack('<i', width))
    buf.write(struct.pack('<i', height))
    buf.write(struct.pack('<HH', 1, 24))
    buf.write(struct.pack('<I', 0))
    buf.write(struct.pack('<I', pixel_data_size))
    buf.write(struct.pack('<i', 2835))
    buf.write(struct.pack('<i', 2835))
    buf.write(struct.pack('<I', 0))
    buf.write(struct.pack('<I', 0))
    # Pixel data (BMP stores as BGR, bottom-up)
    padding = row_size - width * 3
    for _ in range(height):
        for _ in range(width):
            buf.write(struct.pack('BBB', b, g, r))
        buf.write(b'\x00' * padding)

    buf.seek(0)
    return buf


def add_overlays():
    """Add 5 different types of overlays."""
    print("\n" + "=" * 55)
    print("  ADDING 5 OVERLAYS")
    print("=" * 55)

    # --- 1. TEXT OVERLAY ---
    print("\n  [1] Text Overlay")
    text_str = urllib.parse.quote("AXIS Surveillance - Monitored Zone")
    result = set_params(
        f"Image.I0.Text.TextEnabled=yes"
        f"&Image.I0.Text.String={text_str}"
        f"&Image.I0.Text.Position=top"
        f"&Image.I0.Text.BGColor=%23000000"
        f"&Image.I0.Text.Color=%23FFFFFF"
        f"&Image.I0.Text.TextSize=48"
    )
    ok = "OK" in result
    print(f"      Text: 'AXIS Surveillance - Monitored Zone'  {'OK' if ok else result}")

    # --- 2. DATE / TIME OVERLAY ---
    print("\n  [2] Date & Time Overlay")
    result = set_params(
        "Image.I0.Text.DateEnabled=yes"
        "&Image.I0.Text.ClockEnabled=yes"
    )
    ok = "OK" in result
    print(f"      Date + Clock enabled  {'OK' if ok else result}")

    # --- 3. IMAGE / PICTURE OVERLAY ---
    print("\n  [3] Image Overlay (uploaded BMP)")
    try:
        bmp = create_small_bmp(80, 30, r=255, g=50, b=50)
        resp = vapix_post(
            BASE_UPLOAD,
            data={"apiVersion": "1.0", "method": "uploadOverlayImage"},
            files={"file": ("overlay_logo.bmp", bmp, "image/bmp")},
        )
        # Try the param-based approach as fallback
        if resp.status_code != 200 or "error" in resp.text.lower():
            # Alternative: use dynamic overlay API
            resp2 = vapix_get(
                f"{BASE_OVERLAY}?action=add&camera=1&identity=overlay_img"
                f"&overlaytype=image&position=100,100"
            )
            print(f"      Image overlay (dynamic): {resp2.text.strip()[:80]}")
        else:
            print(f"      Image uploaded: {resp.text.strip()[:80]}")
        # Enable the overlay
        set_params("Image.I0.Overlay.Enabled=yes")
    except Exception as e:
        print(f"      Image overlay: {e}")

    # --- 4. STREAMING INDICATOR ---
    print("\n  [4] Streaming Indicator Overlay")
    try:
        resp = vapix_get(
            f"{BASE_OVERLAY}?action=add&camera=1&identity=stream_indicator"
            f"&overlaytype=text&position=10,90"
            f"&text={urllib.parse.quote('● LIVE STREAMING')}"
            f"&fontsize=24&colorname=red"
        )
        text = resp.text.strip()
        print(f"      Streaming indicator: {text[:80]}")
    except Exception as e:
        print(f"      Streaming indicator: {e}")

    # --- 5. WIDGET OVERLAY (camera info / status) ---
    print("\n  [5] Widget Overlay (Camera Info)")
    try:
        widget_text = urllib.parse.quote(f"CAM: {CAMERA_IP} | CH1 | HD 1080p")
        resp = vapix_get(
            f"{BASE_OVERLAY}?action=add&camera=1&identity=widget_info"
            f"&overlaytype=text&position=10,5"
            f"&text={widget_text}"
            f"&fontsize=18&colorname=white&bgcolor=black"
        )
        text = resp.text.strip()
        print(f"      Widget overlay: {text[:80]}")
    except Exception as e:
        print(f"      Widget overlay: {e}")

    print(f"\n  -> 5 overlays configured.")


# ======================== ROTATION ========================

def rotate_360():
    """Rotate the camera 360 degrees."""
    print("\n" + "=" * 55)
    print("  360-DEGREE PTZ ROTATION")
    print("=" * 55)

    start_pan = get_position()
    print(f"\n  Starting pan position: {start_pan}")

    steps = 12
    print("  Rotating 360 degrees in 12 steps...\n")

    for i in range(1, steps + 1):
        target = normalize_pan(start_pan + (360.0 * i / steps))
        move_to(target)
        time.sleep(2)
        current = get_position()
        print(f"    Step {i:2d}/{steps} - Target: {target:7.1f} - Current: {current}")

    move_to(start_pan)
    time.sleep(2)
    print(f"\n  Rotation complete! Back at: {get_position()}")


# ======================== MAIN ========================

def main():
    print("=" * 55)
    print(f"  VAPIX Camera Control - {CAMERA_IP}")
    print("=" * 55)

    add_privacy_masks()
    add_overlays()
    rotate_360()

    print("\n" + "=" * 55)
    print("  ALL DONE")
    print("=" * 55)


if __name__ == "__main__":
    main()
