// One-off verifier: runs each SQL exercise of the PostgreSQL course in PGlite
// (same engine the browser uses) with a known-correct solution, and compares
// the verification query rows against solution.expected_rows using the same
// normalization as the backend validator.
import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const seedPath = join(here, "..", "..", "backend", "seeds", "courses", "05-postgresql.json");
const course = JSON.parse(readFileSync(seedPath, "utf-8"));

// Known-correct solutions per lesson slug
const solutions = {
  "what-is-a-btree-index": "CREATE INDEX idx_products_name ON products (name);",
  "composite-indexes":
    "CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at);",
  "transactions-and-acid":
    "BEGIN; UPDATE accounts SET balance = balance - 30 WHERE owner = 'alice'; UPDATE accounts SET balance = balance + 30 WHERE owner = 'bob'; COMMIT;",
  "altering-tables-safely":
    "ALTER TABLE employees ADD COLUMN department TEXT NOT NULL DEFAULT 'general';",
  "joins-and-aggregations":
    "CREATE VIEW top_customers AS SELECT c.name, COUNT(o.id) AS order_count, SUM(o.amount) AS total FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.name;",
};

function norm(v) {
  const s = String(v).trim().toLowerCase();
  const f = Number(s);
  if (!Number.isNaN(f) && s !== "") {
    return f === Math.trunc(f) ? String(Math.trunc(f)) : String(f);
  }
  return s;
}

let failures = 0;
for (const lesson of course.lessons) {
  for (const ex of lesson.exercises) {
    if (ex.type !== "sql") continue;
    const userSql = solutions[lesson.slug];
    if (!userSql) {
      console.log(`SKIP ${lesson.slug} (no known solution provided)`);
      continue;
    }
    const db = new PGlite();
    try {
      if (ex.data.setup_sql) await db.exec(ex.data.setup_sql);
      await db.exec(userSql);
      const result = await db.query(ex.data.verification_query);
      const columns = result.fields.map((f) => f.name);
      const rows = result.rows.map((r) => columns.map((c) => r[c]));
      const got = rows.map((r) => r.map(norm));
      const expected = ex.solution.expected_rows.map((r) => r.map(norm));
      const ok = JSON.stringify(got) === JSON.stringify(expected);
      if (ok) {
        console.log(`PASS ${lesson.slug}`);
      } else {
        failures++;
        console.log(`FAIL ${lesson.slug}`);
        console.log("  expected:", JSON.stringify(expected));
        console.log("  got:     ", JSON.stringify(got));
      }
    } catch (e) {
      failures++;
      console.log(`ERROR ${lesson.slug}: ${e.message}`);
    } finally {
      await db.close().catch(() => {});
    }
  }
}
console.log(failures === 0 ? "ALL_SQL_EXERCISES_PASS" : `${failures} FAILURES`);
process.exit(failures === 0 ? 0 : 1);
