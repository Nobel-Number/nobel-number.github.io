"""For each laureate-laureate link, record who/what connects them: the joint paper (direct) or one shared co-author and their two papers."""
import json, urllib.request, time, collections
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (research-similarity-prototype)'}
def get(u):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception: time.sleep(2 * (i + 1))
net = json.load(open("site/data/network.json")); co = json.load(open("site/data/coauthors.json"))
lids = json.load(open("site/data/laureate_ids.json"))
raw = json.load(open("data/coauthors_raw.json"))
names = {}
for r in raw:
    for a, (w, y, nm) in r["co"].items(): names.setdefault(a, nm)
idsOf = collections.defaultdict(set)
for a, v in lids.items():
    for li in (v if isinstance(v, list) else [v]): idsOf[li].add(a)
pos2li = [n[0] for n in net["nodes"]]
# per laureate pair, candidates
by_pair = collections.defaultdict(list)  # (x,y) -> [(coauthorId, workX, workY)]
direct = {}
for a, links in co.items():
    d = {li: w for li, w in links}
    if a in lids:
        for x in (lids[a] if isinstance(lids[a], list) else [lids[a]]):
            for y, w in d.items():
                if x != y: direct[tuple(sorted((x, y)))] = w
    ls = sorted(d)
    for i in range(len(ls)):
        for j in range(i + 1, len(ls)): by_pair[(ls[i], ls[j])].append((a, d[ls[i]], d[ls[j]]))
import re
JUNK = re.compile(r"^(books?\b|books received|index|contents|front matter|back matter|editorial|erratum|errata|correction|masthead|issue information|list of|preface|announcements?|news|letters?|notes?|reviews?|book reviews?|obituar|in memoriam|abstracts?|proceedings|program|meeting|annual report|acknowledg|title page|cover|untitled|\W*$)", re.I)
cand_works = set()
for e in net["edges"]:
    x, y = sorted((pos2li[e[0]], pos2li[e[1]]))
    if (x, y) in direct: cand_works.add(direct[(x, y)])
    for a_, wx, wy in (by_pair.get((x, y)) or [])[:4]: cand_works.update([wx, wy])
works = sorted(cand_works); print("works to title", len(works))
titles = {}
def batch(ws):
    d = get("https://api.openalex.org/works?filter=openalex_id:" + "|".join(ws) + "&per_page=100&select=id,title,publication_year")
    return [(r["id"].split("/")[-1], r["title"], r["publication_year"]) for r in (d or {}).get("results", [])]
with ThreadPoolExecutor(6) as ex:
    for res in ex.map(batch, [works[i:i + 50] for i in range(0, len(works), 50)]):
        for w, t, yv in res: titles[w] = [t, yv]
SIGN = re.compile(r"(open letter|petition|statement|endorse|signator|manifesto|declaration)", re.I)
ok = lambda w: w in titles and titles[w][0] and not JUNK.match(titles[w][0].strip()) and not SIGN.search(titles[w][0])
details, keep = [], []
for e in net["edges"]:
    x, y = sorted((pos2li[e[0]], pos2li[e[1]]))
    if (x, y) in direct and ok(direct[(x, y)]):
        e[3] = 1; details.append({"w": direct[(x, y)]}); keep.append(e); continue
    good = [(a_, wx, wy) for a_, wx, wy in (by_pair.get((x, y)) or [])[:4] if ok(wx) and ok(wy)]
    if good:
        a_, wx, wy = good[0]; e[3] = 0
        details.append({"p": names.get(a_, ""), "pid": a_, "wx": wx, "wy": wy, "x": x, "n": len(by_pair[(x, y)])}); keep.append(e)
print("edges kept", len(keep), "of", len(net["edges"]))
net["edges"] = keep
used = set()
for d in details: used.update([v for k, v in d.items() if k in ("w", "wx", "wy")])
titles = {w: titles[w] for w in used}
for e, d in zip(net["edges"], details): e.append(d)
net["works"] = titles
json.dump(net, open("site/data/network.json", "w"), separators=(",", ":"))
