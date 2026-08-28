// Verifies every `sql` exercise in every course seed by running it in PGlite —
// the same engine the browser uses — with the known-correct solution from
// backend/seeds/sql_solutions.json, then comparing the verification query's rows
// against solution.expected_rows using the same normalization as the backend
// validator (backend/app/services/validation_service.py).
//
// A missing solution is a FAILURE, not a skip: that is what makes it impossible
// to land an sql exercise nobody ever ran. Pass --allow-missing to downgrade it.
//
// Usage: npm run verify:sql [--allow-missing]
import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const seedsDir = join(here, "..", "..", "backend", "seeds");
const coursesDir = join(seedsDir, "courses");

const allowMissing = process.argv.includes("--allow-missing");
const solutions = JSON.parse(readFileSync(join(seedsDir, "sql_solutions.json"), "utf-8"));

// Keep in sync with SETUP_SPLIT / execScript in src/lib/pglite.ts.
// A .mjs file cannot import the .ts lib without experimental flags.
const SETUP_SPLIT = /^[ \t]*--[ \t]*@split[ \t]*$/m;
async function execScript(db, script) {
  for (const chunk of script.split(SETUP_SPLIT)) {
    if (chunk.trim()) await db.exec(chunk);
  }
}

// Mirrors _norm() in backend/app/services/validation_service.py
function norm(v) {
  const s = String(v).trim().toLowerCase();
  const f = Number(s);
  if (!Number.isNaN(f) && s !== "") {
    return f === Math.trunc(f) ? String(Math.trunc(f)) : String(f);
  }
  return s;
}

function compare(rows, expected, ordered) {
  const got = rows.map((r) => r.map(norm));
  const want = expected.map((r) => r.map(norm));
  if (ordered) return JSON.stringify(got) === JSON.stringify(want);
  const key = (rs) => JSON.stringify([...rs].map((r) => JSON.stringify(r)).sort());
  return key(got) === key(want);
}

let failures = 0;
let checked = 0;

const files = readdirSync(coursesDir).filter((f) => f.endsWith(".json")).sort();

for (const file of files) {
  const course = JSON.parse(readFileSync(join(coursesDir, file), "utf-8"));
  for (const lesson of course.lessons) {
    for (const [i, ex] of lesson.exercises.entries()) {
      if (ex.type !== "sql") continue;
      const key = `${course.slug}/${lesson.slug}/${i}`;
      checked++;

      if (!Array.isArray(ex.solution?.expected_rows) || ex.solution.expected_rows.length === 0) {
        failures++;
        console.log(`EMPTY    ${key} — solution.expected_rows is empty, this would always pass`);
        continue;
      }

      const userSql = solutions[key];
      if (!userSql) {
        if (allowMissing) {
          console.log(`MISSING  ${key} (allowed)`);
        } else {
          failures++;
          console.log(`MISSING  ${key} — add it to backend/seeds/sql_solutions.json`);
        }
        continue;
      }

      const db = new PGlite();
      try {
        if (ex.data.setup_sql) await execScript(db, ex.data.setup_sql);
        await execScript(db, userSql);
        const result = await db.query(ex.data.verification_query);
        const columns = result.fields.map((f) => f.name);
        const rows = result.rows.map((r) => columns.map((c) => r[c]));
        if (compare(rows, ex.solution.expected_rows, !!ex.solution.ordered)) {
          console.log(`PASS     ${key}`);
        } else {
          failures++;
          console.log(`FAIL     ${key}`);
          console.log("  expected:", JSON.stringify(ex.solution.expected_rows));
          console.log("  got:     ", JSON.stringify(rows));
        }
      } catch (e) {
        failures++;
        console.log(`ERROR    ${key}: ${e.message}`);
      } finally {
        await db.close().catch(() => {});
      }
    }
  }
}

console.log(
  failures === 0
    ? `ALL_SQL_EXERCISES_PASS (${checked} checked)`
    : `${failures} FAILURES of ${checked} checked`
);
process.exit(failures === 0 ? 0 : 1);
