import fs from 'fs';
import path from 'path';

function walk(dir) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (!ent.name.startsWith('.') && ent.name !== 'node_modules') walk(p);
    } else if (ent.name.endsWith('.tsx')) {
      let c = fs.readFileSync(p, 'utf8');
      const orig = c;
      c = c.replace(/mx-auto max-w-/g, 'mx-auto w-full max-w-');
      c = c.replace(
        /(mx-auto w-full max-w-[^\s"]+ px-4)( py-\d+)?(?![^"]*sm:px-)/g,
        (_, a, py) => `${a}${py ?? ''} sm:px-6 lg:px-8`
      );
      if (c !== orig) fs.writeFileSync(p, c);
    }
  }
}

walk(path.join(process.cwd(), 'src', 'app'));
