import requests
import re
import time
import math
from requests.auth import HTTPDigestAuth

CAMERA_IP = "172.27.34.173"
auth = HTTPDigestAuth("root", "pass")
PM_URL = f"http://{CAMERA_IP}/axis-cgi/privacymask.cgi"
PTZ_URL = f"http://{CAMERA_IP}/axis-cgi/com/ptz.cgi"


# ======================== PRIVACY MASKS ========================

def remove_mask(name):
    requests.get(f"{PM_URL}?action=remove&name={name}", auth=auth, timeout=5)

def add_mask(name, x, y, w, h):
    r = requests.get(
        f"{PM_URL}?action=add&name={name}&xpos={x}&ypos={y}&width={w}&height={h}",
        auth=auth, timeout=5)
    return "Error" not in r.text

def setup_masks():
    print("=" * 55)
    print("  ADDING NON-OVERLAPPING PRIVACY MASKS (~5% each)")
    print("=" * 55)

    # Each mask: 22x22% = ~4.8% of view area
    # Grid: 4 columns x 4 rows = 16 masks
    # Spacing: 25% apart (22% mask + 3% gap) → no overlap
    W, H = 22, 22
    STEP = 25  # 22 + 3 gap

    masks = []
    idx = 0
    for row in range(4):
        for col in range(4):
            idx += 1
            x = col * STEP
            y = row * STEP
            name = f"PM_{idx:02d}_R{row}C{col}"
            masks.append((name, x, y))

    # Remove old masks first
    print("\n  Removing old masks...")
    for name, _, _ in masks:
        remove_mask(name)
    # Also remove masks from previous runs
    for i in range(1, 11):
        for prefix in ["Mask_", "PM_"]:
            old = f"{prefix}{i:02d}"
            remove_mask(old)
    for old in ["Mask_01_TopLeft","Mask_02_TopCenter","Mask_03_TopRight",
                "Mask_04_MidLeft","Mask_05_MidCenterL","Mask_06_MidCenterR",
                "Mask_07_MidRight","Mask_08_BotLeft","Mask_09_BotCenter","Mask_10_BotRight"]:
        remove_mask(old)

    print(f"  Adding {len(masks)} masks in a 4x4 grid (no overlap)...\n")
    ok_count = 0
    for name, x, y in masks:
        ok = add_mask(name, x, y, W, H)
        ok_count += ok
        print(f"    {name:16s}  pos=({x:2d},{y:2d})  size={W}x{H}  {'OK' if ok else 'FAIL'}")

    print(f"\n  -> {ok_count}/{len(masks)} masks added.\n")


# ======================== PTZ ROTATION ========================

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
    print("=" * 55)
    print(f"  ROTATING CAMERA {laps} LAPS")
    print("=" * 55)

    steps_per_lap = 12
    total = laps * steps_per_lap
    start = get_pan()
    print(f"\n  Start: {start}  |  {laps} laps x {steps_per_lap} steps = {total} steps\n")

    for i in range(1, total + 1):
        target = normalize(start + 360.0 * i / steps_per_lap)
        move_to(target)
        time.sleep(1)
        lap = (i - 1) // steps_per_lap + 1
        if i % steps_per_lap == 0:
            print(f"    Lap {lap}/{laps} complete")

    move_to(start)
    time.sleep(2)
    print(f"\n  Done! Back at: {get_pan()}\n")


# ======================== MAIN ========================

if __name__ == "__main__":
    print()
    setup_masks()
    rotate(10)
    print("=" * 55)
    print("  ALL DONE")
    print("=" * 55)
