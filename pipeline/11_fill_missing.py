"""Second pass for laureates the byline search missed (e.g. "Sir Paul Nurse", initials-only bylines).
Searches OpenAlex author profiles by cleaned name and accepts a profile only when the name is compatible
AND one of its affiliations matches the Nobel affiliation at prize time. Prints everything for review."""
import json, urllib.request, urllib.parse, time, re, unicodedata, sys
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (research-similarity-prototype)'}
def get(u):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception: time.sleep(2 * (i + 1))
strip = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
HON = {"sir", "lord", "jr", "jr.", "iii", "ii", "sr", "dr"}
STOP = set("university of the institute for and de la le des der fur college school laboratory laboratories national research center centre inc company corporation hospital medical medicine dept department faculty royal state polytechnic technology science sciences institut universitat universite academy society foundation".split())
ns = {}; exec(open("pipeline/04c_strict.py").read().split("changed, lost")[0], ns); compatible = ns["compatible"]
L = json.load(open("raw/laureates.json")); R = json.load(open("raw/author_ids.json")); byl = {r["lid"]: r for r in R}
def clean(s): return " ".join(t for t in (s or "").replace(",", " ").split() if strip(t).strip(".") not in HON)
def words(s): return {w for w in re.findall(r"[a-z]{3,}", strip(s)) if w not in STOP}
def mids(l, fam):  # middle names/initials from the full prize name (the "given" field sometimes leaves them out)
    famt = set(strip(fam).replace("-", " ").split())
    t = [x for x in strip(clean(l["name"])).replace(".", " ").replace("-", " ").split() if x not in famt]
    return t[1:]
def resolve(l):
    given, fam = clean(l["given"]), clean(l["family"]) or l["name"].split()[-1]
    l2 = dict(l, given=given, family=fam)
    qs = list(dict.fromkeys([f"{given} {fam}".strip(), f"{given.split()[0] if given else ''} {fam}".strip()]))
    qs.append(fam)  # surname alone finds initials-only profiles like "K. S. Novoselov"
    cands = {}
    for q in qs:
        d = get("https://api.openalex.org/authors?search=" + urllib.parse.quote(q) + "&per_page=15&select=id,display_name,works_count,cited_by_count,affiliations,last_known_institutions")
        for a in (d or {}).get("results", []): cands[a["id"].split("/")[-1]] = a
    affw = set().union(*[words(x.split(",")[0]) for x in l.get("affiliations") or []] or [set()])
    city = set().union(*[words(",".join(x.split(",")[1:-1])) for x in l.get("affiliations") or []] or [set()])
    ok, seen = [], []
    for aid, a in cands.items():
        if not compatible(a["display_name"], l2) or a["works_count"] < 5: continue
        famk = strip(fam).replace("-", " ").split()[-1]
        dn = strip(a["display_name"]).replace("-", " ").replace(".", " ").split()
        if not dn or dn[-1] != famk: continue  # surname must end the name
        gmid = mids(l, fam)
        cmid = [t for t in dn[1:-1] if t not in strip(fam).replace("-", " ").split()]
        if not gmid and any(len(t) == 1 for t in cmid): continue  # "Michael J. Smith" is not "Michael Smith"
        if gmid and cmid and gmid[0][0] != cmid[0][0]: continue
        # an affiliation must match the Nobel one AND be in the prize era, so namesakes at the same university don't pass
        insts = [x["institution"]["display_name"] for x in a.get("affiliations") or []
                 if any(l["year"] - 30 <= y <= l["year"] + 15 for y in x.get("years") or [])]
        hit = [n for n in insts if words(n) & affw]
        seen.append((aid, a["display_name"], a["works_count"], a["cited_by_count"], hit[:2]))
        if hit: ok.append((aid, a["display_name"], a["cited_by_count"]))
    if len(ok) > 1 and not mids(l, fam):  # common name, several plausible profiles: need an exact name
        ok = [o for o in ok if len(strip(o[1]).split()) == 2]
    elif len(ok) > 1 and any(len(strip(o[1]).split()) > 2 for o in ok):  # laureate has a middle name: prefer profiles that show it
        ok = [o for o in ok if len(strip(o[1]).split()) > 2]
    if ok:  # drop small side profiles of other people: keep profiles with at least 10% of the best one's citations
        top = max(o[2] for o in ok); ok = [o for o in ok if o[2] >= 0.1 * top]
    return l, ok, seen, affw
missing = [l for l in L if not byl.get(l["id"], {}).get("ids")]
with ThreadPoolExecutor(6) as ex: res = list(ex.map(resolve, missing))
added = 0
for l, ok, seen, affw in res:
    print(("ADD " if ok else "--- ") + l["name"], l["year"], l.get("affiliations"), "->", [(o[0], o[1], o[2]) for o in ok] if ok else seen[:3])
    if ok and "--dry" not in sys.argv:
        r = byl.setdefault(l["id"], {"lid": l["id"], "ids": [], "names": [], "scores": []})
        if r not in R: R.append(r)
        r["ids"] = [o[0] for o in ok]; r["names"] = [o[1] for o in ok]; r["scores"] = [99] * len(ok); r["via"] = "profile+affiliation"; added += 1
print("added", added, "of", len(missing))
if "--dry" not in sys.argv: json.dump(R, open("raw/author_ids.json", "w"), indent=0)
