import requests
from requests.auth import HTTPDigestAuth

auth = HTTPDigestAuth("root", "pass")
ip = "172.27.34.173"
PM = f"http://{ip}/axis-cgi/privacymask.cgi"

# Clean all old masks
print("Cleaning...")
for i in range(1, 50):
    for p in ["PM_","RndMask_","Mask_","Oct_","Test"]:
        requests.get(f"{PM}?action=remove&name={p}{i:02d}", auth=auth, timeout=3)
        requests.get(f"{PM}?action=remove&name={p}{i}", auth=auth, timeout=3)
for old in ["Mask_01_TopLeft","Mask_02_TopCenter","Mask_03_TopRight",
            "Mask_04_MidLeft","Mask_05_MidCenterL","Mask_06_MidCenterR",
            "Mask_07_MidRight","Mask_08_BotLeft","Mask_09_BotCenter","Mask_10_BotRight"]:
    requests.get(f"{PM}?action=remove&name={old}", auth=auth, timeout=3)

# Test max masks
print("Testing max masks...")
count = 0
for i in range(1, 101):
    r = requests.get(f"{PM}?action=add&name=T{i}&xpos={i%80}&ypos={i%80}&width=5&height=5&pan={i*37%360-180}&tilt=10", auth=auth, timeout=5)
    if "Error" in r.text:
        print(f"  Failed at #{i}: {r.text.strip()[:80]}")
        break
    count += 1
    if count % 10 == 0:
        print(f"  {count} masks added...")

print(f"\nMax masks: {count}")

# Clean up
print("Cleaning up test masks...")
for i in range(1, count + 1):
    requests.get(f"{PM}?action=remove&name=T{i}", auth=auth, timeout=3)
print("Done")
