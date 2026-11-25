"""Laureate network: laureates are linked when they co-authored, or share 2+ co-authors. Force layout with numpy."""
import json, collections, itertools, numpy as np
site = json.load(open("data/laureates.json"))
lids = json.load(open("data/laureate_ids.json"))
co = json.load(open("data/coauthors.json"))
idx_of = {a: (v if isinstance(v, list) else [v]) for a, v in lids.items()}
nodes = sorted({i for v in idx_of.values() for i in v})
pos = {li: k for k, li in enumerate(nodes)}
direct, shared = collections.Counter(), collections.Counter()
for a, links in co.items():
    ls = sorted({li for li, _ in links})
    if a in idx_of:  # the co-author is a laureate themself
        for x in idx_of[a]:
            for y in ls:
                if x != y: direct[tuple(sorted((x, y)))] += 1
    for x, y in itertools.combinations(ls, 2): shared[(x, y)] += 1
edges = {}
for (x, y), c in shared.items():
    if c >= 2: edges[(x, y)] = min(1.0, c / 10)
for (x, y) in direct: edges[(x, y)] = 1.0
E = [(pos[x], pos[y], w) for (x, y), w in edges.items() if x in pos and y in pos]
n = len(nodes); print("nodes", n, "edges", len(E), "direct", len(direct))
rng = np.random.default_rng(7)
cats = [site[li]["cat"] for li in nodes]
anchor = {"phy": (-1, -0.6, 0.6), "che": (0.9, -0.7, -0.5), "med": (0.8, 0.8, 0.6), "eco": (-0.9, 0.8, -0.6)}
P = np.array([anchor[c] for c in cats]) + rng.normal(0, .5, (n, 3))
ei = np.array([[a, b] for a, b, _ in E]); ew = np.array([w for _, _, w in E])
deg = np.zeros(n); np.add.at(deg, ei[:, 0], 1); np.add.at(deg, ei[:, 1], 1)
for it in range(400):
    t = 0.08 * (1 - it / 400) + 0.005
    D = P[:, None, :] - P[None, :, :]; d2 = (D ** 2).sum(-1) + 1e-3
    rep = (D / d2[..., None]).sum(1) * 0.0025
    F = rep
    v = P[ei[:, 1]] - P[ei[:, 0]]; dist = np.linalg.norm(v, axis=1, keepdims=True) + 1e-6
    f = v * (dist - 0.15) * ew[:, None] * 0.5
    np.add.at(F, ei[:, 0], f); np.add.at(F, ei[:, 1], -f)
    F += (np.array([anchor[c] for c in cats]) * 0.6 - P) * 0.02  # loose pull to field quadrant
    step = np.linalg.norm(F, axis=1, keepdims=True); F = F / np.maximum(step, 1e-9) * np.minimum(step, t)
    P += F
conn = deg > 0
P -= P[conn].mean(0); P /= np.percentile(np.abs(P[conn]), 97, axis=0)
nr = np.linalg.norm(P, axis=1, keepdims=True); P = np.where(nr > 1, P / nr * (1 + np.log(nr) * 0.15), P)
iso = np.where(~conn)[0]; ang = rng.uniform(0, 2*np.pi, len(iso)); rad = rng.uniform(0.95, 1.08, len(iso))
v = rng.normal(0, 1, (len(iso), 3)); v /= np.linalg.norm(v, axis=1, keepdims=True); P[iso] = v * rad[:, None]
out = {"nodes": [[li, round(float(x), 4), round(float(y), 4), int(deg[k]), round(float(z), 4)] for k, (li, (x, y, z)) in enumerate(zip(nodes, P))],
       "edges": [[a, b, round(w, 2), 1 if (nodes[a], nodes[b]) in direct or (nodes[b], nodes[a]) in direct else 0] for a, b, w in E], "people": len(co)}
json.dump(out, open("data/network.json", "w"), separators=(",", ":"))
print("isolated", int((deg == 0).sum()))
