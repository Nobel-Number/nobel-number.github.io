// Nobel number search: co-authorship distance from a researcher to the nearest Nobel laureate.
// Works in the browser and in Node 22 (global fetch). Uses the OpenAlex API live, plus a
// precomputed table of every laureate's co-authors (distance 1), so most answers need few requests.

export const MAX_AUTHORS = 30; // papers with more authors (big collaborations) don't count as links
const OA = 'https://api.openalex.org/';

export function createSearch({ laureates, laureateIds, coauthors, fetchImpl = fetch, onProgress = () => {} }) {
  // laureates: [{name, year, category, ...}]
  // laureateIds: { "A123": laureateIndex | [indices] }
  // coauthors: { "A456": [[laureateIndex, workId], ...] }  (distance-1 table)
  const asList = v => (Array.isArray(v) ? v : [v]);
  let requests = 0;

  async function oa(path) {
    for (let i = 0; i < 4; i++) {
      requests++;
      const r = await fetchImpl(OA + path);
      if (r.ok) return r.json();
      if (r.status === 404) return null;
      await new Promise(res => setTimeout(res, 800 * (i + 1)));
    }
    throw new Error('OpenAlex is not responding right now. Try again in a minute.');
  }

  const short = id => String(id || '').split('/').pop();

  async function findAuthors(query) {
    const q = query.trim();
    const orcid = q.replace(/^https?:\/\/orcid\.org\//, '');
    if (/^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/i.test(orcid)) {
      const a = await oa('authors/orcid:' + orcid);
      return a ? [authorCard(a)] : [];
    }
    if (/^A\d{5,}$/i.test(q)) { const a = await oa('authors/' + q.toUpperCase()); return a ? [authorCard(a)] : []; }
    const d = await oa('authors?search=' + encodeURIComponent(q) + '&per_page=8');
    return (d?.results || []).map(authorCard);
  }
  function authorCard(a) {
    const inst = a.last_known_institutions?.[0]?.display_name || a.affiliations?.[0]?.institution?.display_name || '';
    return { id: short(a.id), name: a.display_name, orcid: a.orcid, works: a.works_count, cites: a.cited_by_count, institution: inst,
      topic: a.topics?.[0]?.display_name || '' };
  }

  // ---------- paper store ----------
  const W = new Map(); // workId -> {id, title, year, field, authors: Map(authorId -> {name, raw, inst:[{id,name}]})}
  function keepWork(w) {
    const id = short(w.id);
    if (W.has(id)) return W.get(id);
    const authors = new Map();
    for (const a of w.authorships || []) {
      const aid = short(a.author?.id); if (!aid) continue;
      authors.set(aid, { name: a.author.display_name, raw: a.raw_author_name, inst: (a.institutions || []).map(i => ({ id: short(i.id), name: i.display_name })) });
    }
    const rec = { id, title: w.title, year: w.publication_year, authors, nAuthors: (w.authorships || []).length };
    W.set(id, rec); return rec;
  }
  const SEL = 'select=id,title,publication_year,authorships';
  // Only peer-reviewed work counts as a link: journal or conference articles, reviews and letters.
  // Excludes preprints, conference abstracts, errata, books, datasets and retracted papers.
  const PEER_REVIEWED = ',type:article|review|letter,primary_location.source.type:journal|conference,is_retracted:false';

  // All co-authors of a set of authors. Batches ids into OR filters.
  // Returns Map coauthorId -> {name, links: Map(insiderId -> [workIds])}
  async function coauthorsOf(ids, { maxPagesPerBatch = 5, label = '' } = {}) {
    const out = new Map();
    const idSet = new Set(ids);
    for (let b = 0; b < ids.length; b += 50) {
      const batch = ids.slice(b, b + 50);
      let page = 1;
      while (page <= maxPagesPerBatch) {
        const d = await oa(`works?filter=author.id:${batch.join('|')}${PEER_REVIEWED}&${SEL}&per_page=200&page=${page}`);
        if (!d) break;
        for (const w of d.results) {
          if (w.authorships.length > MAX_AUTHORS) continue;
          const rec = keepWork(w);
          const au = [...rec.authors.keys()];
          const insiders = au.filter(a => idSet.has(a));
          for (const a of au) if (!idSet.has(a)) {
            let e = out.get(a);
            if (!e) { e = { name: rec.authors.get(a).name, links: new Map() }; out.set(a, e); }
            for (const i of insiders) { if (!e.links.has(i)) e.links.set(i, []); e.links.get(i).push(rec.id); }
          }
        }
        if (page * 200 >= d.meta.count) page = Infinity; else page++;
        onProgress(`${label}${out.size.toLocaleString()} co-authors found`);
      }
    }
    return out;
  }

  // ---------- same-person check ----------
  // OpenAlex sometimes merges different people who share a name into one profile. To tell whether two papers
  // on one profile belong to the same person, we group that profile's papers: two papers are joined when they
  // share a co-author or an affiliation of this person. Papers by different namesakes end up in different groups.
  const graphs = new Map();
  async function scholarGraph(id) {
    if (graphs.has(id)) return graphs.get(id);
    const parent = new Map();
    const find = x => { while (parent.get(x) !== x) { parent.set(x, parent.get(parent.get(x))); x = parent.get(x); } return x; };
    const union = (a, b) => { a = find(a); b = find(b); if (a !== b) parent.set(a, b); };
    const firstByKey = new Map();
    let page = 1;
    while (page <= 10) {
      const d = await oa(`works?filter=author.id:${id}&${SEL}&per_page=200&page=${page}`);
      if (!d) break;
      for (const w of d.results) {
        const rec = keepWork(w);
        if (!parent.has(rec.id)) parent.set(rec.id, rec.id);
        const me = rec.authors.get(id);
        const keys = (me?.inst || []).map(i => 'i:' + i.id);
        if (rec.nAuthors <= 100) for (const a of rec.authors.keys()) if (a !== id) keys.push('a:' + a);
        for (const k of keys) { const f = firstByKey.get(k); if (f) union(rec.id, f); else firstByKey.set(k, rec.id); }
      }
      if (page * 200 >= d.meta.count) break; page++;
    }
    const sizes = new Map(); for (const w of parent.keys()) { const r = find(w); sizes.set(r, (sizes.get(r) || 0) + 1); }
    const g = { has: w => parent.has(w), group: w => (parent.has(w) ? find(w) : null), sizes };
    graphs.set(id, g); return g;
  }
  // Is `id` the same person on some paper in A and some paper in B?
  async function samePerson(id, A, B) {
    const g = await scholarGraph(id);
    const ga = new Set(A.map(g.group).filter(Boolean));
    return B.some(b => ga.has(g.group(b)));
  }
  // Is `id` on paper set A the main person behind their profile (the largest group)?
  async function mainPerson(id, A) {
    const g = await scholarGraph(id);
    let best = null, bs = 0; for (const [r, n] of g.sizes) if (n > bs) { bs = n; best = r; }
    return A.some(a => g.group(a) === best);
  }

  const weight = e => { let n = 0; for (const v of e.links.values()) n += v.length; return n; };
  const laureateHits = id => (laureateIds[id] !== undefined ? asList(laureateIds[id]) : []);
  const coHits = id => coauthors[id] || [];

  async function workRec(id) {
    if (W.has(id)) return W.get(id);
    const w = await oa('works/' + id + '?' + SEL);
    return w ? keepWork(w) : { id, title: '(paper)', year: null, authors: new Map() };
  }

  // Candidate chains: people [me, p1, ..., pk] where pk co-authored with laureate li on table paper tw (null at distance 1).
  function* chains(rings, k, end) {
    // walk back from `end` (in ring k) to me, trying the best-linked predecessors first
    function* back(level, person, tail) {
      if (level === 0) { yield [person, ...tail]; return; }
      const preds = [...rings[level].get(person).links.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 3);
      for (const [pred] of preds) if (rings[level - 1].has(pred)) yield* back(level - 1, pred, [person, ...tail]);
    }
    yield* back(k, end, []);
  }
  const shared = (rings, people, i) => rings[i + 1].get(people[i + 1]).links.get(people[i]) || [];

  async function verify(rings, people, li, tableWork) {
    // returns null if fine, or a reason string naming the person whose identity doesn't hold up
    if (!(await mainPerson(people[0], shared(rings, people, 0)))) return rings[0].get(people[0]).name;
    for (let i = 1; i < people.length; i++) {
      const A = shared(rings, people, i - 1);
      const B = i < people.length - 1 ? shared(rings, people, i) : (tableWork ? [tableWork] : null);
      if (!B) continue;
      if (!(await samePerson(people[i], A, B))) return rings[i].get(people[i]).name;
    }
    if (tableWork) { // the laureate's side: the linking paper must belong to the laureate, not a namesake on their profile
      const w = await workRec(tableWork);
      const lid = [...w.authors.keys()].find(a => laureateHits(a).includes(li));
      if (lid && !(await mainPerson(lid, [tableWork]))) return laureates[li].name + ' (a namesake on their profile)';
    }
    return null;
  }

  async function nobelNumber(person, { maxDepth = 4 } = {}) {
    requests = 0;
    const me = { id: person.id, name: person.name };
    if (laureateHits(me.id).length) return { number: 0, paths: laureateHits(me.id).map(li => ({ laureate: li, steps: [] })), requests };
    const rings = [new Map([[me.id, { name: me.name, links: new Map() }]])];
    const seen = new Set([me.id]);
    const rejected = [];
    let searched = 0;
    for (let d = 1; d <= maxDepth; d++) {
      // distance d needs co-author rings up to d (for d = 1) or d - 1 (laureate co-author table covers the last hop)
      const need = d === 1 ? 1 : d - 1;
      while (rings.length - 1 < need) {
        const lvl = rings.length;
        const prev = [...rings[lvl - 1].keys()];
        const frontier = lvl === 1 ? prev : prev.sort((a, b) => weight(rings[lvl - 1].get(b)) - weight(rings[lvl - 1].get(a))).slice(0, lvl === 2 ? 400 : 600);
        onProgress(lvl === 1 ? 'Reading your papers…' : `Reading the papers of ${frontier.length.toLocaleString()} co-authors…`);
        const ring = await coauthorsOf(frontier, { maxPagesPerBatch: lvl === 1 ? 10 : lvl === 2 ? 6 : 2, label: `Ring ${lvl}: ` });
        for (const k of [...ring.keys()]) if (seen.has(k)) ring.delete(k);
        for (const k of ring.keys()) seen.add(k);
        rings.push(ring); searched += ring.size;
        if (!ring.size) return { number: null, paths: [], requests, searched, rejected };
      }

      // candidates at distance d
      const cands = [];
      if (d === 1) { for (const c of rings[1].keys()) for (const li of laureateHits(c)) cands.push({ end: c, li, tw: null, k: 1, laureateNode: true }); }
      // a person in ring d-1 who co-authored with a laureate (table) gives distance d
      if (d >= 2) for (const c of rings[d - 1].keys()) for (const [li, tw] of coHits(c)) cands.push({ end: c, li, tw, k: d - 1 });
      // rank: people who share more papers first
      cands.sort((a, b) => weight(rings[b.k].get(b.end)) - weight(rings[a.k].get(a.end)));
      const found = new Map();
      let checks = 0;
      for (const c of cands) {
        if (found.has(c.li) || found.size >= 8 || checks >= 30) continue;
        for (const people of chains(rings, c.k, c.end)) {
          checks++;
          onProgress(`Checking that the people in a chain are who they seem (${checks})…`);
          const why = await verify(rings, people, c.li, c.tw);
          if (!why) { found.set(c.li, { people, ...c }); break; }
          if (rejected.length < 6) rejected.push({ laureate: c.li, person: why });
          if (checks >= 30) break;
        }
      }
      if (found.size) return finish(d, [...found.values()], rings, rejected, cands.length);
    }
    return { number: null, paths: [], requests, searched, rejected };
  }

  function instOn(workId, personId) {
    const a = W.get(workId)?.authors.get(personId);
    return [...new Set((a?.inst || []).map(i => i.name))].slice(0, 2).join(', ');
  }
  async function finish(n, found, rings, rejected, candidates) {
    const paths = [];
    for (const f of found) {
      const steps = [];
      const ppl = f.people;
      for (let i = 0; i < ppl.length - 1; i++) {
        const ws = shared(rings, ppl, i).map(id => W.get(id)).sort((a, b) => (b.year || 0) - (a.year || 0));
        const w = ws[0];
        steps.push({ from: { id: ppl[i], name: rings[i].get(ppl[i]).name, inst: instOn(w.id, ppl[i]) },
          to: { id: ppl[i + 1], name: rings[i + 1].get(ppl[i + 1]).name, inst: instOn(w.id, ppl[i + 1]) },
          work: { id: w.id, title: w.title, year: w.year }, n: ws.length });
      }
      if (f.tw) {
        const w = await workRec(f.tw);
        const last = ppl[ppl.length - 1];
        const lid = [...w.authors.keys()].find(a => laureateHits(a).includes(f.li));
        steps.push({ from: { id: last, name: rings[ppl.length - 1].get(last).name, inst: instOn(w.id, last) },
          to: { laureate: f.li, inst: lid ? instOn(w.id, lid) : '' }, work: { id: w.id, title: w.title, year: w.year } });
      }
      paths.push({ laureate: f.li, steps });
    }
    return { number: n, paths, requests, totalLaureates: paths.length, rejected, candidates };
  }

  return { findAuthors, nobelNumber };
}
