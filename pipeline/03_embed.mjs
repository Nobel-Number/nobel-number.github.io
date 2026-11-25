// Embed prize motivations and candidate papers; pick each laureate's key (prize-relevant) papers.
import { pipeline, env } from '@xenova/transformers';
import fs from 'fs';
env.localModelPath = new URL('./models/', import.meta.url).pathname; env.allowRemoteModels = false;
const ext = await pipeline('feature-extraction', 'Xenova/bge-small-en-v1.5', { quantized: true });
const L = JSON.parse(fs.readFileSync('data/laureates.json'));
const W = Object.fromEntries(JSON.parse(fs.readFileSync('data/openalex_works.json')).map(r => [r.lid + ':' + r.year, r.works]));
const embed = async (texts) => { const out = []; for (let i = 0; i < texts.length; i += 16) { const o = await ext(texts.slice(i, i + 16), { pooling: 'cls', normalize: true }); out.push(...o.tolist()); } return out; };
const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
const paperText = w => (w.title + '. ' + (w.abstract || '')).slice(0, 1200);
const out = []; let t0 = Date.now();
for (const [k, l] of L.entries()) {
  const mot = `${l.category} Nobel Prize: ${l.motivation}`;
  const [mv] = await embed([mot]);
  const works = (W[l.id + ':' + l.year] || []).slice(0, 25);
  const wv = works.length ? await embed(works.map(paperText)) : [];
  const ranked = works.map((w, i) => ({ w, v: wv[i], rel: dot(mv, wv[i]) + 0.02 * Math.log10(w.cites + 1) }))
    .sort((a, b) => b.rel - a.rel).filter(x => x.rel > 0.55).slice(0, 3);
  out.push({ ...l, motivationVec: mv, papers: ranked.map(x => ({ title: x.w.title, year: x.w.year, doi: x.w.doi, cites: x.w.cites, venue: x.w.venue, openalex: x.w.id, hasAbstract: !!x.w.abstract, rel: +x.rel.toFixed(3), vec: x.v })) });
  if (k % 50 === 0) console.log(k, l.name, ((Date.now() - t0) / 1000).toFixed(0) + 's', ranked.map(x => x.w.title.slice(0, 50) + ' ' + x.rel.toFixed(2)));
}
fs.writeFileSync('data/embedded.json', JSON.stringify(out));
console.log('done');
