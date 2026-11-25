"""Resolve each laureate to OpenAlex author id(s) using works before the prize whose byline matches their name."""
import json, urllib.request, urllib.parse, time, re, unicodedata, collections, math
from concurrent.futures import ThreadPoolExecutor
L = json.load(open("data/laureates.json"))
UA = {'User-Agent': 'Mozilla/5.0 (research-similarity-prototype)'}
def get(url):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e: err = e; time.sleep(2 * (i + 1))
    print("FAIL", url, err); return None
strip = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
def names(l):
    given = [t for t in l["given"].split() if not re.fullmatch(r"[A-Z]\.?(-[A-Z]\.?)?", t)]
    fam = l["family"] or l["name"].split()[-1]
    out = ([f"{given[0]} {fam}"] if given else []) + [l["name"]]
    return list(dict.fromkeys(out)), fam
def resolve(l):
    cand, fam = names(l); famk = strip(fam).split()[-1]
    first = strip(l["given"] or l["name"])[:1]
    score = collections.Counter(); disp = {}
    for n in cand:
        q = urllib.parse.quote(n.replace(",", " "))
        d = get(f"https://api.openalex.org/works?filter=raw_author_name.search:{q},publication_year:{max(1800,l['year']-45)}-{l['year']+5}&sort=cited_by_count:desc&per_page=50&select=cited_by_count,authorships")
        if not d: continue
        for w in d["results"]:
            for a in w["authorships"]:
                raw = strip(a.get("raw_author_name")); au = a.get("author") or {}
                if au.get("id") and famk in raw and raw[:1] == first:
                    aid = au["id"].split("/")[-1]
                    score[aid] += 1 + math.log10(w["cited_by_count"] + 1); disp[aid] = au.get("display_name")
        if score: break
    if not score: return {"lid": l["id"], "ids": []}
    top = score.most_common(1)[0][1]
    ids = [a for a, s in score.most_common(6) if s >= 0.25 * top]
    return {"lid": l["id"], "ids": ids, "names": [disp[a] for a in ids], "scores": [round(score[a], 1) for a in ids]}
uniq = {l["id"]: l for l in L}
with ThreadPoolExecutor(6) as ex: res = list(ex.map(resolve, uniq.values()))
json.dump(res, open("data/author_ids.json", "w"), indent=0)
print(len(res), "resolved", sum(bool(r["ids"]) for r in res))
