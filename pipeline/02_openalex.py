"""For each laureate, pull their most-cited works published before the prize (OpenAlex)."""
import json, urllib.request, urllib.parse, time, re, unicodedata
from concurrent.futures import ThreadPoolExecutor
L = json.load(open("data/laureates.json"))
UA = {'User-Agent': 'Mozilla/5.0 (research-similarity-prototype)'}

def get(url, tries=4):
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except Exception as e:
            time.sleep(2 * (i + 1)); err = e
    print("FAIL", url, err); return None

def abstract(inv):
    if not inv: return ""
    pos = {}
    for w, ix in inv.items():
        for i in ix: pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))

def strip(s): return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def names(l):
    given = [t for t in re.split(r"[\s]+", l["given"]) if t and not re.fullmatch(r"[A-Z]\.?(-[A-Z]\.?)?", t)]
    fam = l["family"] or l["name"].split()[-1]
    out = []
    if given: out.append(f"{given[0]} {fam}")
    out.append(l["name"])
    return list(dict.fromkeys(out)), fam

def fetch(l):
    cand, fam = names(l)
    lo, hi = max(1800, l["year"] - 45), l["year"]
    works = {}
    for n in cand:
        q = urllib.parse.quote(n.replace(",", " "))
        url = (f"https://api.openalex.org/works?filter=raw_author_name.search:{q},publication_year:{lo}-{hi}"
               f"&sort=cited_by_count:desc&per_page=40&select=id,doi,title,publication_year,cited_by_count,abstract_inverted_index,authorships,primary_location")
        d = get(url)
        if not d: continue
        for w in d.get("results", []):
            if not w.get("title"): continue
            raws = [strip(a.get("raw_author_name") or "") for a in w["authorships"]]
            if not any(strip(fam).split()[-1] in r for r in raws): continue
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
            works[w["id"]] = {"id": w["id"].split("/")[-1], "doi": w.get("doi"), "title": w["title"], "year": w["publication_year"],
                              "cites": w["cited_by_count"], "venue": src, "nAuthors": len(w["authorships"]),
                              "abstract": abstract(w.get("abstract_inverted_index"))[:2500]}
        if len(works) >= 15: break
    return {"lid": l["id"], "year": l["year"], "works": sorted(works.values(), key=lambda w: -w["cites"])[:40]}

with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(fetch, L))
json.dump(res, open("data/openalex_works.json", "w"))
n = [len(r["works"]) for r in res]
print("laureates", len(n), "with>=1 work", sum(x > 0 for x in n), "with abstract", sum(any(w["abstract"] for w in r["works"]) for r in res))
