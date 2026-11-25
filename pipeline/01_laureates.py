import json, urllib.request, time
cats = {"phy":"Physics","che":"Chemistry","med":"Physiology or Medicine","eco":"Economic Sciences"}
out = []
for c in cats:
    off = 0
    while True:
        url = f"https://api.nobelprize.org/2.1/laureates?limit=100&offset={off}&nobelPrizeCategory={c}"
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (research-similarity-prototype)'})))
        for L in d["laureates"]:
            if "knownName" not in L: continue  # organisations
            for p in L["nobelPrizes"]:
                code = {"Physics":"phy","Chemistry":"che","Physiology or Medicine":"med","Economic Sciences":"eco"}.get(p["category"]["en"])
                if code != c: continue
                out.append({
                    "id": L["id"], "name": L["knownName"]["en"],
                    "given": L.get("givenName",{}).get("en",""), "family": L.get("familyName",{}).get("en",""),
                    "birthYear": L.get("birth",{}).get("year"), "birthPlace": L.get("birth",{}).get("place",{}).get("locationString",{}).get("en"), "gender": L.get("gender"), "deathYear": (L.get("death",{}).get("date") or "")[:4] or None,
                    "year": int(p["awardYear"]), "category": cats[c], "cat": c,
                    "motivation": p.get("motivation",{}).get("en","").strip('" '),
                    "share": p.get("portion"), "affiliations": [", ".join(x for x in [a.get("name",{}).get("en"), a.get("city",{}).get("en"), a.get("country",{}).get("en")] if x) for a in p.get("affiliations",[])], "prizeAmount": p.get("prizeAmount"),
                    "wikidata": L.get("wikidata",{}).get("id"),
                    "wikipedia": L.get("wikipedia",{}).get("english"),
                    "nobelUrl": f"https://www.nobelprize.org/prizes/{p['category']['en'].split()[0].lower()}/{p['awardYear']}/summary/",
                })
        off += 100
        if off >= d["meta"]["count"]: break
        time.sleep(0.3)
json.dump(out, open("raw/laureates.json","w"), indent=1)
print(len(out)); import collections; print(collections.Counter(x["cat"] for x in out)); print(out[-1])
