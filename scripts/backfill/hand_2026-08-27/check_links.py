import json, concurrent.futures, requests

data = json.load(open("scripts/backfill/kuratiert_rest129.json"))
UA = "Mozilla/5.0 (compatible; berufungsradar-linkcheck/1.0)"

def check(entry):
    url = entry["quelle_werdegang"]
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15, allow_redirects=True)
        return (entry["name"], url, r.status_code, "")
    except requests.RequestException as e:
        return (entry["name"], url, "ERR", str(e)[:120])

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(check, data))

broken = [r for r in results if r[2] == "ERR" or (isinstance(r[2], int) and r[2] >= 400)]

with open("scripts/backfill/hand_2026-08-27/link_check.log", "w") as f:
    for name, url, status, err in results:
        f.write(f"{status}\t{name}\t{url}\t{err}\n")

print(f"{len(results)} checked, {len(broken)} broken")
for name, url, status, err in broken:
    print(f"  {status} {name} {url} {err}")
