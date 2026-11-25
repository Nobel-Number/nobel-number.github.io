import json, re, unicodedata
strip = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
L = {l["id"]: l for l in json.load(open("raw/laureates.json"))}
R = json.load(open("raw/author_ids.json"))
def initials(name, fam):
    toks = [t for t in re.split(r"[\s.\-]+", strip(name)) if t and t not in strip(fam).split() and t not in ("sir", "jr", "lord")]
    return [t[0] for t in toks]
dropped = 0
for r in R:
    if len(r.get("ids") or []) < 2: continue
    l = L[r["lid"]]; li = initials(l["fullName"] if "fullName" in l else l["name"], l["family"])
    keep = [0]
    for j in range(1, len(r["ids"])):
        ci = initials(r["names"][j], l["family"])
        ok = r["scores"][j] >= 0.4 * r["scores"][0] and ci[:1] == li[:1] and (len(ci) < 2 or len(li) < 2 or ci[1] in li[1:])
        if ok: keep.append(j)
        else: dropped += 1
    for k in ("ids", "names", "scores"): r[k] = [r[k][j] for j in keep]
json.dump(R, open("raw/author_ids.json", "w"), indent=0)
print("dropped", dropped)
