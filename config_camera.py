import requests
import json
from requests.auth import HTTPDigestAuth

CAMERA_IP = "172.27.34.173"
USERNAME = "root"
PASSWORD = "pass"
auth = HTTPDigestAuth(USERNAME, PASSWORD)

OVERLAY_URL = f"http://{CAMERA_IP}/axis-cgi/dynamicoverlay/dynamicoverlay.cgi"
PMASK_URL = f"http://{CAMERA_IP}/axis-cgi/privacymask.cgi"


def overlay_call(method, params):
    r = requests.post(OVERLAY_URL, auth=auth, timeout=10,
                      json={"apiVersion": "1.0", "method": method, "params": params})
    return r.json()


def add_privacy_mask(name, xpos, ypos, width, height):
    r = requests.get(
        f"{PMASK_URL}?action=add&name={name}&xpos={xpos}&ypos={ypos}&width={width}&height={height}",
        auth=auth, timeout=10)
    return r.text.strip()


def remove_privacy_mask(name):
    requests.get(f"{PMASK_URL}?action=remove&name={name}", auth=auth, timeout=5)


# ======================== PRIVACY MASKS ========================

def setup_privacy_masks():
    print("=" * 55)
    print("  ADDING 10 PRIVACY MASKS (each ~5% of view)")
    print("=" * 55)

    # Each mask: ~22% x 22% = ~5% of total area
    # sqrt(0.05) ≈ 0.22 → 22x22 in percentage units
    W, H = 22, 22

    masks = [
        ("Mask_01_TopLeft",       0,   0),
        ("Mask_02_TopCenter",    39,   0),
        ("Mask_03_TopRight",     78,   0),
        ("Mask_04_MidLeft",       0,  26),
        ("Mask_05_MidCenterL",   26,  26),
        ("Mask_06_MidCenterR",   52,  26),
        ("Mask_07_MidRight",     78,  26),
        ("Mask_08_BotLeft",       0,  52),
        ("Mask_09_BotCenter",    39,  52),
        ("Mask_10_BotRight",     78,  52),
    ]

    for i, (name, x, y) in enumerate(masks, 1):
        # Remove if already exists
        remove_privacy_mask(name)
        result = add_privacy_mask(name, x, y, W, H)
        ok = "Error" not in result
        status = "OK" if ok else result[:80]
        print(f"  [{i:2d}] {name:25s} pos=({x:2d},{y:2d}) size={W}x{H}  {status}")

    print(f"\n  -> 10 privacy masks added.\n")


# ======================== OVERLAYS ========================

def cleanup_overlays():
    """Remove all existing dynamic overlays."""
    data = overlay_call("list", {}).get("data", {})
    for t in data.get("textOverlays", []):
        overlay_call("remove", {"identity": t["identity"]})
    for img in data.get("imageOverlays", []):
        overlay_call("remove", {"identity": img["identity"]})


def setup_overlays():
    print("=" * 55)
    print("  ADDING 5 OVERLAYS")
    print("=" * 55)

    cleanup_overlays()

    # --- 1. TEXT OVERLAY (topLeft) ---
    print("\n  [1] Text Overlay - Custom text")
    r = overlay_call("addText", {"camera": 1, "text": "AXIS Surveillance Zone"})
    ident1 = r.get("data", {}).get("identity")
    if ident1:
        overlay_call("setText", {
            "identity": ident1,
            "text": "AXIS Surveillance Zone",
            "fontSize": 32,
            "textColor": "white",
            "textBGColor": "semiblack",
            "position": "topLeft",
        })
        print(f"      'AXIS Surveillance Zone' at topLeft (id={ident1})  OK")
    else:
        print(f"      Error: {r}")

    # --- 2. DATE & TIME OVERLAY (top) ---
    print("\n  [2] Date & Time Overlay")
    r = overlay_call("addText", {"camera": 1, "text": "%F %X"})
    ident2 = r.get("data", {}).get("identity")
    if ident2:
        overlay_call("setText", {
            "identity": ident2,
            "text": "%F %X",
            "fontSize": 24,
            "textColor": "white",
            "textBGColor": "black",
            "position": "top",
        })
        print(f"      Date/Time '%F %X' at top (id={ident2})  OK")
    else:
        print(f"      Error: {r}")

    # --- 3. IMAGE / PICTURE OVERLAY (topRight via coordinates) ---
    print("\n  [3] Image Overlay - Axis logo")
    r = overlay_call("addImage", {
        "camera": 1,
        "overlayPath": "/etc/overlays/axis(128x44).ovl",
        "position": "topRight",
    })
    ident3 = r.get("data", {}).get("identity")
    if ident3:
        print(f"      Axis logo image at topRight (id={ident3})  OK")
    else:
        print(f"      Error: {r}")

    # --- 4. STREAMING INDICATOR OVERLAY ---
    print("\n  [4] Streaming Indicator")
    r = overlay_call("addText", {"camera": 1, "text": "LIVE"})
    ident4 = r.get("data", {}).get("identity")
    if ident4:
        overlay_call("setText", {
            "identity": ident4,
            "text": "#O LIVE STREAMING",
            "fontSize": 28,
            "textColor": "red",
            "textBGColor": "transparent",
            "textOLColor": "black",
            "position": "bottomLeft",
            "indicator": "recording",
            "indicatorColor": "red",
        })
        print(f"      '#O LIVE STREAMING' at bottomLeft (id={ident4})  OK")
    else:
        print(f"      Error: {r}")

    # --- 5. WIDGET OVERLAY - Camera info ---
    print("\n  [5] Widget Overlay - Camera info")
    r = overlay_call("addText", {"camera": 1, "text": "INFO"})
    ident5 = r.get("data", {}).get("identity")
    if ident5:
        overlay_call("setText", {
            "identity": ident5,
            "text": f"CAM: {CAMERA_IP} | CH1 | 4K UHD",
            "fontSize": 20,
            "textColor": "white",
            "textBGColor": "semiblack",
            "position": "bottom",
        })
        print(f"      Camera info widget at bottom (id={ident5})  OK")
    else:
        print(f"      Error: {r}")

    print(f"\n  -> 5 overlays added.\n")


# ======================== VERIFY ========================

def verify():
    print("=" * 55)
    print("  VERIFICATION")
    print("=" * 55)
    data = overlay_call("list", {}).get("data", {})
    texts = data.get("textOverlays", [])
    images = data.get("imageOverlays", [])
    print(f"\n  Text overlays:  {len(texts)}")
    for t in texts:
        print(f"    id={t['identity']}  text='{t['text'][:40]}'  pos={t['position']}")
    print(f"  Image overlays: {len(images)}")
    for img in images:
        print(f"    id={img['identity']}  file='{img['overlayPath']}'")
    print()


# ======================== MAIN ========================

def main():
    print()
    print("=" * 55)
    print(f"  CAMERA CONFIG - {CAMERA_IP}")
    print("=" * 55)
    print()

    setup_privacy_masks()
    setup_overlays()
    verify()

    print("=" * 55)
    print("  ALL DONE")
    print("=" * 55)


if __name__ == "__main__":
    main()
