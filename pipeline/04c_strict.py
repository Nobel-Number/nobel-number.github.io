"""Stricter laureate-profile check: names must agree on first name and middle initials; weak matches are dropped."""
import json, re, unicodedata
strip = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
L = {l["id"]: l for l in json.load(open("raw/laureates.json"))}
R = json.load(open("raw/author_ids.json"))
SUF = {"jr", "jr.", "iii", "ii", "sr", "sr."}
def core(fam): return [t for t in strip(fam).replace("-", " ").replace(",", " ").split() if t not in SUF]
def toks(name, fam):
    fam_t = set(core(fam)) | SUF
    return [t for t in re.split(r"[\s.]+", strip(name).replace("-", " ")) if t and t not in fam_t and t not in ("sir", "jr", "lord", "dr")]
def compatible(cand, l):
    c, g = toks(cand, l["family"]), toks(l["given"] or l["name"], l["family"])
    if not c or not g: return False
    if not core(l["family"]) or core(l["family"])[-1] not in strip(cand).replace("-", " ").replace(".", " ").split() and core(l["family"])[-1] not in strip(cand).replace("-", ""): return False
    if c[0][0] != g[0][0]: return False
    if len(c[0]) > 1 and len(g[0]) > 1 and not (c[0].startswith(g[0]) or g[0].startswith(c[0])): return False
    if len(c) > 1 and len(g) > 1 and c[1][0] != g[1][0]: return False
    return True
changed, lost = [], 0
for r in R:
    l = L[r["lid"]]; old = list(r["ids"])
    keep = [j for j in range(len(r["ids"])) if compatible(r["names"][j], l)]
    if keep:
        c0 = toks(r["names"][keep[0]], l["family"]); full = len(c0[0]) > 1
        if r["scores"][keep[0]] < (5 if full else 10): keep = []
    for k in ("ids", "names", "scores"): r[k] = [r[k][j] for j in keep]
    if r["ids"] != old:
        changed.append(r["lid"])
        if not r["ids"]: lost += 1; print("dropped:", l["name"], "<-", old and [n for n in json.load(open("raw/author_ids_v1.json")) if n["lid"] == r["lid"]][0]["names"])
json.dump(R, open("raw/author_ids.json", "w"), indent=0)
print("changed", len(changed), "now unresolved", lost, "resolved", sum(bool(r["ids"]) for r in R))
json.dump(changed, open("raw/changed_lids.json", "w"))
