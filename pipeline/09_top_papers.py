"""Most-cited paper before the prize, taken from the laureate's own matched OpenAlex profile (not a name search)."""
import json, urllib.request, time
from concurrent.futures import ThreadPoolExecutor
UA = {'User-Agent': 'Mozilla/5.0 (research-similarity-prototype)'}
def get(u):
    for i in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception: time.sleep(2 * (i + 1))
L = json.load(open("data/laureates.json")); A = {r["lid"]: r["ids"] for r in json.load(open("data/author_ids.json"))}
site = json.load(open("site/data/laureates.json"))
def top(i):
    l = L[i]; ids = A.get(l["id"]) or []
    if not ids: return i, None
    d = get(f"https://api.openalex.org/works?filter=author.id:{'|'.join(ids)},publication_year:<{l['year'] + 1},authors_count:<31,type:article|review|letter,primary_location.source.type:journal|conference,is_retracted:false&sort=cited_by_count:desc&per_page=1&select=id,title,publication_year,cited_by_count")
    w = (d or {}).get("results") or []
    return i, ({"title": w[0]["title"], "year": w[0]["publication_year"], "cites": w[0]["cited_by_count"], "id": w[0]["id"].split("/")[-1]} if w and w[0].get("title") else None)
with ThreadPoolExecutor(6) as ex:
    for i, tp in ex.map(top, range(len(L))):
        site[i].pop("topPaper", None)
        if tp: site[i]["topPaper"] = tp
json.dump(site, open("site/data/laureates.json", "w"), separators=(",", ":"))
for s in site:
    if s["name"] in ("Thomas H. Morgan", "Bruce A. Beutler", "Albert Einstein"): print(s["name"], s.get("topPaper"))
print("with top paper", sum("topPaper" in s for s in site))
