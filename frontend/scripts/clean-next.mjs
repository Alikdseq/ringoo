/**
 * Полная очистка кэша Next.js / Turbopack.
 * Запускайте при ошибках вида "Failed to open SST file" или повреждённом .next.
 */
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const targets = ['.next', 'node_modules/.cache'];

for (const name of targets) {
  const dir = path.join(root, name);
  if (!fs.existsSync(dir)) continue;
  fs.rmSync(dir, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 });
  console.log(`Removed ${name}`);
}

console.log('Next.js cache cleared.');
