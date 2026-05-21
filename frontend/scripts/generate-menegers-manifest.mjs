/**
 * Сканирует public/menegers и пишет manifest.json (slug → photo URL).
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.join(process.cwd(), 'public', 'menegers');
const OUT = path.join(ROOT, 'manifest.json');
const EXT = new Set(['.jpg', '.jpeg', '.png', '.webp']);

/** Папка → slug менеджера в API */
const FOLDER_SLUG = {
  Джалилбек: 'dzhalilbek',
  'Авакян Эллина': 'avakyan-ellina',
};

function pickPhotos(files) {
  return files
    .filter(f => EXT.has(path.extname(f).toLowerCase()))
    .sort((a, b) => a.localeCompare(b, 'ru'))
    .map(f => f);
}

const managers = {};
if (fs.existsSync(ROOT)) {
  for (const folder of fs.readdirSync(ROOT)) {
    const full = path.join(ROOT, folder);
    if (!fs.statSync(full).isDirectory()) continue;
    const slug = FOLDER_SLUG[folder];
    if (!slug) continue;
    const files = fs.readdirSync(full);
    const photos = pickPhotos(files);
    if (photos.length === 0) continue;
    const urls = photos.map(
      photo => `/menegers/${folder}/${photo}`.replace(/\\/g, '/')
    );
    managers[slug] = urls.length === 1 ? urls[0] : urls;
  }
}

fs.mkdirSync(ROOT, { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ managers }, null, 2), 'utf8');
console.log(`menegers manifest: ${Object.keys(managers).length} manager(s)`);
