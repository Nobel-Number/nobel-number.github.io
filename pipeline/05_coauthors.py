"""Build the distance-1 table: every co-author of every laureate (papers with <= MAXA authors)."""
# Peer-reviewed only: journal/conference articles, reviews and letters; no preprints, abstracts, errata, books, datasets or retracted papers.
import json, urllib.request, time, sys
from concurrent.futures import ThreadPoolExecutor
MAXA = 30
UA = {'User-Agent': 'Mozilla/5.0 (research-similarity-prototype)'}
def get(url):
    for i in range(6):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90))
        except Exception as e: err = e; time.sleep(2 * (i + 1))
    print("FAIL", url, err, flush=True); return None
A = [r for r in json.load(open("data/author_ids.json")) if r["ids"]]
def crawl(r):
    ids = set(r["ids"]); co = {}; page = 1
    while page <= 40:  # at most 8000 works per laureate
        d = get(f"https://api.openalex.org/works?filter=author.id:{'|'.join(ids)},type:article|review|letter,primary_location.source.type:journal|conference,is_retracted:false&select=id,publication_year,authorships&per_page=200&page={page}")
        if not d: break
        for w in d["results"]:
            au = w["authorships"]
            if len(au) > MAXA: continue
            for a in au:
                aid = ((a.get("author") or {}).get("id") or "").split("/")[-1]
                if not aid or aid in ids: continue
                prev = co.get(aid)
                if not prev or (w["publication_year"] or 9999) < prev[1]:
                    co[aid] = (w["id"].split("/")[-1], w["publication_year"] or 0, (a["author"].get("display_name") or ""))
        if page * 200 >= d["meta"]["count"]: break
        page += 1
    return {"lid": r["lid"], "ids": r["ids"], "co": co}
out = []
with ThreadPoolExecutor(6) as ex:
    for i, res in enumerate(ex.map(crawl, A)):
        out.append(res)
        if i % 50 == 0: print(i, len(res["co"]), flush=True)
json.dump(out, open("data/coauthors_raw.json", "w"))
print("done", sum(len(o["co"]) for o in out))
