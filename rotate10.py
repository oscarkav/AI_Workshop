import requests
from requests.auth import HTTPDigestAuth
import time
import re

CAMERA_IP = "172.27.34.173"
USERNAME = "root"
PASSWORD = "pass"
BASE_URL = f"http://{CAMERA_IP}/axis-cgi/com/ptz.cgi"
auth = HTTPDigestAuth(USERNAME, PASSWORD)


def get_pan():
    resp = requests.get(f"{BASE_URL}?query=position", auth=auth, timeout=5)
    resp.raise_for_status()
    m = re.search(r"pan=(-?[\d.]+)", resp.text)
    return float(m.group(1)) if m else None


def move_to(pan, speed=80):
    requests.get(f"{BASE_URL}?pan={pan}&speed={speed}", auth=auth, timeout=5)


def normalize(angle):
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return round(angle, 1)


def main():
    laps = 10
    steps_per_lap = 12  # 30 degrees per step
    total_steps = laps * steps_per_lap  # 120 steps

    start = get_pan()
    print(f"Start position: {start}")
    print(f"Rotating {laps} laps ({total_steps} steps)...\n")

    for i in range(1, total_steps + 1):
        target = normalize(start + (360.0 * i / steps_per_lap))
        move_to(target)
        time.sleep(1)

        lap = (i - 1) // steps_per_lap + 1
        step_in_lap = (i - 1) % steps_per_lap + 1
        if step_in_lap == steps_per_lap:
            print(f"  Lap {lap}/{laps} complete")

    move_to(start)
    time.sleep(2)
    print(f"\nDone! Back at: {get_pan()}")


if __name__ == "__main__":
    main()
