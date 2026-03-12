import requests, json
from requests.auth import HTTPDigestAuth
auth = HTTPDigestAuth('root', 'pass')
ip = '172.27.34.173'
ov = f'http://{ip}/axis-cgi/dynamicoverlay/dynamicoverlay.cgi'
pm = f'http://{ip}/axis-cgi/privacymask.cgi'

# Privacy mask - try different actions to list
print("--- PM actions ---")
for act in ['listall', 'getmasks', 'view', 'remove']:
    r = requests.get(f'{pm}?action={act}', auth=auth, timeout=5)
    print(f"  action={act}: {r.text.strip()[:150]}")

# PM - remove the one we added
print("\n--- PM remove by name ---")
r = requests.get(f'{pm}?action=remove&name=T1', auth=auth, timeout=5)
print(r.text.strip()[:200])

# PM - add multiple, test width limits
print("\n--- PM add width tests ---")
for w in [10, 20, 50, 99]:
    r = requests.get(f'{pm}?action=add&name=W{w}&xpos=0&ypos=0&width={w}&height={w}', auth=auth, timeout=5)
    body = r.text.strip()
    status = "OK" if not body or "Error" not in body else body[:100]
    print(f"  width={w}: {status}")
    if "Error" not in body:
        requests.get(f'{pm}?action=remove&name=W{w}', auth=auth, timeout=5)

# addImage - try every known param
print("\n--- addImage all known params ---")
combos = [
    {'camera':1,'overlayPath':'/etc/overlays/axis(128x44).ovl'},
    {'camera':1,'image':'/etc/overlays/axis(128x44).ovl'},
    {'camera':1,'file':'/etc/overlays/axis(128x44).ovl'},
]
for p in combos:
    r = requests.post(ov, auth=auth, json={'apiVersion':'1.0','method':'addImage','params':p}, timeout=5)
    d = r.json()
    err = d.get('error',{}).get('message','OK')
    print(f"  {json.dumps(p)}: {err}")

# set text on existing overlay (setText)
print("\n--- setText ---")
r = requests.post(ov, auth=auth, json={'apiVersion':'1.0','method':'addText','params':{'camera':1,'text':'Test'}}, timeout=5)
ident = r.json().get('data',{}).get('identity')
print(f"Added text, identity={ident}")

r = requests.post(ov, auth=auth, json={'apiVersion':'1.0','method':'setText','params':{'identity':ident,'text':'Updated #D %T','fontSize':32,'textColor':'yellow'}}, timeout=5)
print(f"setText: {r.text.strip()[:200]}")

# List full details 
print("\n--- Full list ---")
r = requests.post(ov, auth=auth, json={'apiVersion':'1.0','method':'list','params':{}}, timeout=5)
print(json.dumps(r.json(), indent=2)[:1500])
