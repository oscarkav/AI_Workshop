import requests
import re
import time
import random
from requests.auth import HTTPDigestAuth

CAMERA_IP = "172.27.34.173"
auth = HTTPDigestAuth("root", "pass")
PM_URL = f"http://{CAMERA_IP}/axis-cgi/privacymask.cgi"
PTZ_URL = f"http://{CAMERA_IP}/axis-cgi/com/ptz.cgi"

random.seed(99)


def pm_remove(name):
    requests.get(f"{PM_URL}?action=remove&name={name}", auth=auth, timeout=10)

def pm_add(name, x, y, w, h, pan, tilt):
    r = requests.get(
        f"{PM_URL}?action=add&name={name}"
        f"&xpos={x}&ypos={y}&width={w}&height={h}"
        f"&pan={pan}&tilt={tilt}",
        auth=auth, timeout=10)
    time.sleep(0.3)  # avoid overloading camera
    return "Error" not in r.text


def make_octagon(prefix, cx, cy, size, pan, tilt):
    """
    Approximate an octagon using 3 stacked rectangles:

        ┌──────────┐         <- top strip (narrower)
        │          │
    ┌───┴──────────┴───┐     <- middle strip (full width)
    │                  │
    └───┬──────────┬───┘
        │          │
        └──────────┘         <- bottom strip (narrower)

    Each strip = 1 mask. 3 masks total.
    """
    # Octagon cuts ~30% off each corner
    cut = int(size * 0.29)       # corner cut
    strip_h = int(size * 0.29)   # height of top/bottom strips
    mid_h = size - 2 * strip_h   # height of middle strip

    masks = [
        # Top strip: narrower, offset inward
        (f"{prefix}_top", cx + cut, cy, size - 2 * cut, strip_h),
        # Middle strip: full width
        (f"{prefix}_mid", cx, cy + strip_h, size, mid_h),
        # Bottom strip: narrower, offset inward
        (f"{prefix}_bot", cx + cut, cy + strip_h + mid_h, size - 2 * cut, strip_h),
    ]

    results = []
    for name, x, y, w, h in masks:
        pm_remove(name)
        ok = pm_add(name, x, y, w, h, pan, tilt)
        results.append((name, x, y, w, h, ok))
    return results


def cleanup_all():
    """Remove all known masks."""
    print("  Cleaning up old masks...")
    prefixes = ["PM_", "RndMask_", "Mask_", "Oct_", "T", "Test",
                "Mask_01_TopLeft", "Mask_02_TopCenter", "Mask_03_TopRight",
                "Mask_04_MidLeft", "Mask_05_MidCenterL", "Mask_06_MidCenterR",
                "Mask_07_MidRight", "Mask_08_BotLeft", "Mask_09_BotCenter",
                "Mask_10_BotRight"]
    for name in prefixes:
        pm_remove(name)
    for i in range(1, 30):
        for p in ["PM_", "RndMask_", "Oct", "T", "Test"]:
            pm_remove(f"{p}{i:02d}")
            pm_remove(f"{p}{i}")
        for suffix in ["_top", "_mid", "_bot"]:
            pm_remove(f"Oct{i:02d}{suffix}")
    time.sleep(1)


def setup_octagons():
    print("=" * 60)
    print("  ADDING OCTAGONAL PRIVACY MASKS ACROSS 360°")
    print("=" * 60)

    cleanup_all()

    # 5 octagons × 3 masks each = 15 masks total
    # Each octagon ~22% size ≈ 5% of view area
    # Spread across different pan/tilt positions (non-overlapping)
    SIZE = 22

    # 5 octagons at evenly-spaced pan positions with random tilt/offset
    octagons = [
        ("Oct01", random.randint(5, 30), random.randint(5, 30), -144, random.randint(-10, 40)),
        ("Oct02", random.randint(40, 60), random.randint(5, 30),  -72, random.randint(-10, 40)),
        ("Oct03", random.randint(5, 30), random.randint(40, 60),    0, random.randint(-10, 40)),
        ("Oct04", random.randint(40, 60), random.randint(40, 60),  72, random.randint(-10, 40)),
        ("Oct05", random.randint(5, 30), random.randint(5, 30),   144, random.randint(-10, 40)),
    ]

    print(f"\n  Creating 5 octagons (3 masks each = 15 masks total)...\n")
    total_ok = 0
    for prefix, cx, cy, pan, tilt in octagons:
        results = make_octagon(prefix, cx, cy, SIZE, pan, tilt)
        for name, x, y, w, h, ok in results:
            total_ok += ok
            print(f"    {name:16s}  ({x:2d},{y:2d}) {w:2d}x{h:2d}  pan={pan:4d} tilt={tilt:3d}  {'OK' if ok else 'FAIL'}")
        print()

    print(f"  -> {total_ok}/15 masks added.\n")


# ======================== PTZ ========================

def get_pan():
    r = requests.get(f"{PTZ_URL}?query=position", auth=auth, timeout=5)
    m = re.search(r"pan=(-?[\d.]+)", r.text)
    return float(m.group(1)) if m else 0

def move_to(pan, speed=80):
    requests.get(f"{PTZ_URL}?pan={pan}&speed={speed}", auth=auth, timeout=5)

def normalize(a):
    while a > 180: a -= 360
    while a < -180: a += 360
    return round(a, 1)

def rotate(laps=10):
    print("=" * 60)
    print(f"  ROTATING CAMERA {laps} LAPS")
    print("=" * 60)
    steps_per_lap = 12
    total = laps * steps_per_lap
    start = get_pan()
    print(f"\n  Start: {start}  |  {total} steps\n")

    for i in range(1, total + 1):
        target = normalize(start + 360.0 * i / steps_per_lap)
        move_to(target)
        time.sleep(1)
        if i % steps_per_lap == 0:
            print(f"    Lap {i // steps_per_lap}/{laps} complete")

    move_to(start)
    time.sleep(2)
    print(f"\n  Done! Back at: {get_pan()}\n")


if __name__ == "__main__":
    print()
    setup_octagons()
    rotate(10)
    print("=" * 60)
    print("  ALL DONE")
    print("=" * 60)
