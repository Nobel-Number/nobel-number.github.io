// Precompute example results with the same search code the site uses.
import fs from 'fs';
import { createSearch } from '../site/nobel-number.js';
const rd = f => JSON.parse(fs.readFileSync(new URL('../site/data/' + f + '.json', import.meta.url)));
const s = createSearch({ laureates: rd('laureates'), laureateIds: rd('laureate_ids'), coauthors: rd('coauthors'), onProgress: m => process.stderr.write('\r' + m.padEnd(60)) });
const out = [];
for (const q of process.argv.slice(2)) {
  const [a] = await s.findAuthors(q);
  const result = await s.nobelNumber(a);
  console.error(`\n${a.name}: ${result.number} (${result.requests} req)`);
  out.push({ person: a, result });
}
fs.writeFileSync(new URL('../site/data/examples.json', import.meta.url), JSON.stringify(out));
