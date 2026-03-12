import requests
import re
import time
import random
from requests.auth import HTTPDigestAuth

CAMERA_IP = "172.27.34.173"
auth = HTTPDigestAuth("root", "pass")
PM_URL = f"http://{CAMERA_IP}/axis-cgi/privacymask.cgi"
PTZ_URL = f"http://{CAMERA_IP}/axis-cgi/com/ptz.cgi"

random.seed(42)  # reproducible randomness


def remove_mask(name):
    requests.get(f"{PM_URL}?action=remove&name={name}", auth=auth, timeout=5)

def add_mask(name, x, y, w, h, pan, tilt):
    r = requests.get(
        f"{PM_URL}?action=add&name={name}"
        f"&xpos={x}&ypos={y}&width={w}&height={h}"
        f"&pan={pan}&tilt={tilt}",
        auth=auth, timeout=5)
    return "Error" not in r.text


def setup_masks():
    print("=" * 60)
    print("  ADDING 16 RANDOM PRIVACY MASKS ACROSS 360° VIEW")
    print("=" * 60)

    W, H = 22, 22  # ~5% of view each

    # Remove old masks
    print("\n  Cleaning old masks...")
    for i in range(1, 20):
        remove_mask(f"PM_{i:02d}_R{(i-1)//4}C{(i-1)%4}")
        remove_mask(f"Mask_{i:02d}")
        remove_mask(f"RndMask_{i:02d}")
    for old in ["Mask_01_TopLeft","Mask_02_TopCenter","Mask_03_TopRight",
                "Mask_04_MidLeft","Mask_05_MidCenterL","Mask_06_MidCenterR",
                "Mask_07_MidRight","Mask_08_BotLeft","Mask_09_BotCenter",
                "Mask_10_BotRight"]:
        remove_mask(old)

    # Generate 16 masks at random pan/tilt positions across 360°
    masks = []
    for i in range(1, 17):
        pan = random.randint(-180, 179)
        tilt = random.randint(-20, 60)
        xpos = random.randint(5, 70)
        ypos = random.randint(5, 70)
        masks.append((f"RndMask_{i:02d}", xpos, ypos, pan, tilt))

    print(f"  Adding {len(masks)} masks randomly across 360° panorama...\n")
    ok = 0
    for name, x, y, pan, tilt in masks:
        success = add_mask(name, x, y, W, H, pan, tilt)
        ok += success
        print(f"    {name}  pos=({x:2d},{y:2d}) size={W}x{H}  pan={pan:4d} tilt={tilt:3d}  {'OK' if success else 'FAIL'}")

    print(f"\n  -> {ok}/{len(masks)} masks added.\n")


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
    setup_masks()
    rotate(10)
    print("=" * 60)
    print("  ALL DONE")
    print("=" * 60)
