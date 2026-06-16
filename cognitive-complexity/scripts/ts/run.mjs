// Cognitive-complexity scorer for JS/TS via the ESLint Node API.
//
// One long-lived process scores every file with eslint-plugin-sonarjs (the
// SonarSource implementation), avoiding per-file process startup. ESLint 9 ties
// its base path to the config directory and ignores files outside it, so we
// feed each file's text via lintText() with a RELATIVE filePath (basename) —
// that resolves inside the base path and matches the config's `files` glob.
//
// Input : a JSON array of absolute file paths as argv[2], or via stdin.
// Output: JSON array of { file, line, score } on stdout.
import { ESLint } from 'eslint';
import { readFileSync } from 'node:fs';
import path from 'node:path';

const here = path.dirname(new URL(import.meta.url).pathname);

async function readFileList() {
  if (process.argv[2]) return JSON.parse(process.argv[2]);
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return JSON.parse(Buffer.concat(chunks).toString('utf8') || '[]');
}

const files = await readFileList();
const eslint = new ESLint({
  cwd: here, // plugins resolve from ./node_modules; base path = here
  overrideConfigFile: path.join(here, 'eslint.config.mjs'),
});

const RE = /Cognitive Complexity from (\d+)/;
const out = [];
for (const f of files) {
  let code;
  try {
    code = readFileSync(f, 'utf8');
  } catch {
    continue;
  }
  // Relative filename keeps the original extension (drives parser + glob match)
  // and stays inside the base path.
  const fname = path.basename(f);
  let results;
  try {
    results = await eslint.lintText(code, { filePath: fname, warnIgnored: false });
  } catch {
    continue;
  }
  for (const r of results) {
    for (const m of r.messages) {
      if (m.ruleId === 'sonarjs/cognitive-complexity') {
        const mt = RE.exec(m.message || '');
        if (mt) out.push({ file: f, line: m.line ?? null, score: Number(mt[1]) });
      }
    }
  }
}
process.stdout.write(JSON.stringify(out));
