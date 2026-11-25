import json
L = json.load(open("raw/laureates.json"))
raw = json.load(open("raw/coauthors_raw.json"))
lid_to_idx = {}
site_l = []
try: old = json.load(open("data/laureates.json"))  # keep fields added by later steps (bios, top paper)
except Exception: old = []
for i, l in enumerate(L):
    rec = dict(old[i]) if i < len(old) and old[i].get("name") == l["name"] else {}
    rec.update({k: l[k] for k in ("name", "year", "category", "cat", "motivation", "nobelUrl")}); site_l.append(rec)
    lid_to_idx.setdefault(l["id"], []).append(i)
lids, co = {}, {}; dropped = 0
for r in raw:
    idxs = lid_to_idx[r["lid"]]
    li = max(idxs, key=lambda i: L[i]["year"])  # person with two prizes: point to the latest (path display)
    for a in r["ids"]: lids[a] = idxs if len(idxs) > 1 else idxs[0]
    lo = int(L[li]["birthYear"] or 0) + 16; hi = int(L[li].get("deathYear") or 9999) + 3
    for a, (wid, yr, _) in r["co"].items():
        if yr and not (lo <= yr <= hi): dropped += 1; continue
        lst = co.setdefault(a, [])
        if len(lst) < 6 and all(x[0] != li for x in lst): lst.append([li, wid])
json.dump(site_l, open("data/laureates.json", "w"), separators=(",", ":"))
json.dump(lids, open("data/laureate_ids.json", "w"), separators=(",", ":"))
json.dump(co, open("data/coauthors.json", "w"), separators=(",", ":"))
print("dropped out-of-lifetime links", dropped); print("laureate ids", len(lids), "coauthors", len(co))
