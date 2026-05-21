/**
 * Сканирует public/magazins и пишет manifest.json для галереи на /stores.
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.join(process.cwd(), 'public', 'magazins');
const OUT = path.join(ROOT, 'manifest.json');
const EXT = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif']);

function walk(dir, base = '') {
  const entries = [];
  if (!fs.existsSync(dir)) return entries;
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const rel = base ? `${base}/${name}` : name;
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      if (name === 'node_modules') continue;
      entries.push(...walk(full, rel));
    } else if (EXT.has(path.extname(name).toLowerCase())) {
      entries.push(`/magazins/${rel.replace(/\\/g, '/')}`);
    }
  }
  return entries;
}

const images = walk(ROOT).sort();
fs.mkdirSync(ROOT, { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ images }, null, 2), 'utf8');
console.log(`magazins manifest: ${images.length} image(s)`);
