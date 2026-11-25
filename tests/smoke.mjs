// Runs many real researchers through the site's search code and checks every chain against OpenAlex.
import fs from 'fs';
import { createSearch, MAX_AUTHORS } from '../site/nobel-number.js';
const rd = f => JSON.parse(fs.readFileSync(new URL('../site/data/' + f + '.json', import.meta.url)));
const laureates = rd('laureates'), laureateIds = rd('laureate_ids'), coauthors = rd('coauthors');
const UA = { headers: { 'User-Agent': 'Mozilla/5.0 (research-similarity-prototype)' } };
const fetchImpl = u => fetch(u, UA);
const OK_TYPES = new Set(['article', 'review', 'letter']);
const cases = JSON.parse(fs.readFileSync(new URL('./people.json', import.meta.url)));
const short = id => String(id || '').split('/').pop();
async function checkPaths(res) {
  const problems = [];
  const ids = [...new Set(res.paths.flatMap(p => p.steps.map(s => s.work.id)))];
  if (!ids.length) return problems;
  const r = await (await fetchImpl('https://api.openalex.org/works?filter=openalex_id:' + ids.join('|') + '&per_page=100&select=id,type,is_retracted,primary_location,authorships')).json();
  const W = new Map(r.results.map(w => [short(w.id), w]));
  for (const p of res.paths) for (const s of p.steps) {
    const w = W.get(s.work.id); if (!w) { problems.push('missing paper ' + s.work.id); continue; }
    const au = new Set(w.authorships.map(a => short(a.author?.id)));
    const st = w.primary_location?.source?.type;
    if (!OK_TYPES.has(w.type) || !['journal', 'conference'].includes(st) || w.is_retracted) problems.push(`not peer-reviewed: ${s.work.id} (${w.type}/${st})`);
    if (w.authorships.length > MAX_AUTHORS) problems.push(`too many authors: ${s.work.id}`);
    if (!au.has(s.from.id)) problems.push(`${s.from.name} not on ${s.work.id}`);
    if (s.to.id && !au.has(s.to.id)) problems.push(`${s.to.name} not on ${s.work.id}`);
    if (s.to.laureate != null && ![...au].some(a => [].concat(laureateIds[a] ?? []).includes(s.to.laureate))) problems.push(`laureate ${laureates[s.to.laureate].name} not on ${s.work.id}`);
  }
  for (const p of res.paths) if (p.steps.length !== res.number) problems.push(`path length ${p.steps.length} != ${res.number}`);
  return problems;
}
async function one(c) {
  const t0 = Date.now(); const s = createSearch({ laureates, laureateIds, coauthors, fetchImpl });
  try {
    const cands = await s.findAuthors(c.q);
    if (!cands.length) return { ...c, found: 'no profile', ms: Date.now() - t0, ok: c.expect === 'none' };
    const res = await s.nobelNumber(cands[0]);
    const problems = await checkPaths(res);
    if (c.expect !== undefined && c.expect !== 'none' && res.number !== c.expect) problems.push(`expected ${c.expect}`);
    const first = res.paths[0];
    const chain = first ? [first.steps[0]?.from.name ?? cands[0].name, ...first.steps.map(x => x.to.laureate != null ? laureates[x.to.laureate].name : x.to.name)].join(' → ') : '';
    return { ...c, found: `${cands[0].name} (${cands[0].institution})`, number: res.number, laureates: res.paths.length, requests: res.requests, rejected: (res.rejected || []).length, ms: Date.now() - t0, chain, problems, ok: !problems.length };
  } catch (e) { return { ...c, error: String(e.message || e), ms: Date.now() - t0, ok: false }; }
}
const out = []; let next = 0;
await Promise.all(Array.from({ length: 4 }, async () => { while (next < cases.length) { const c = cases[next++]; const r = await one(c); out.push(r); console.error(`${r.ok ? 'ok ' : 'BAD'} ${r.q} -> ${r.number ?? r.found ?? r.error} ${(r.ms / 1000).toFixed(1)}s ${r.requests ?? ''}req ${r.problems?.join('; ') || r.error || ''}`); } }));
fs.writeFileSync(new URL('./results.json', import.meta.url), JSON.stringify(out, null, 1));
