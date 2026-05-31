const fs = require('fs');
const path = require('path');

const targetDir = path.resolve(process.cwd(), process.argv[2] || 'dist');
const extensions = new Set(['.html', '.js', '.css']);

function walk(dir, files = []) {
  if (!fs.existsSync(dir)) {
    return files;
  }

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, files);
    } else if (entry.isFile() && extensions.has(path.extname(entry.name))) {
      files.push(full);
    }
  }

  return files;
}

let changed = 0;

for (const file of walk(targetDir)) {
  const original = fs.readFileSync(file, 'utf8');
  const cleaned = original
    .replace(/[\uFE0E\uFE0F]/g, '')
    .replace(/[\p{Extended_Pictographic}\p{Emoji_Presentation}]/gu, '');

  if (cleaned !== original) {
    fs.writeFileSync(file, cleaned, 'utf8');
    changed += 1;
  }
}

if (changed > 0) {
  console.log(`Stripped emoji from ${changed} built file(s).`);
}
