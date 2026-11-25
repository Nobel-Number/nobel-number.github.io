import json, importlib.util, sys
spec = importlib.util.spec_from_file_location("c", "pipeline/05_coauthors.py")
src = open("pipeline/05_coauthors.py").read().split("out = []")[0]  # reuse crawl() without running the full job
ns = {}; exec(src, ns)
changed = set(json.load(open("data/changed_lids.json")))
A = {r["lid"]: r for r in json.load(open("data/author_ids.json"))}
raw = json.load(open("data/coauthors_raw.json"))
new = []
for r in raw:
    if r["lid"] not in changed: new.append(r)
for lid in changed:
    if A[lid]["ids"]: new.append(ns["crawl"](A[lid]))
json.dump(new, open("data/coauthors_raw.json", "w"))
print("entries", len(new))
