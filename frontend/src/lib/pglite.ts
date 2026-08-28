import type { PGlite } from "@electric-sql/pglite";

/** Type-only import above plus this lazy loader: the ~3 MB wasm bundle stays out
 * of the app chunk and is fetched the first time a learner actually runs SQL. */
async function loadPGlite(): Promise<typeof PGlite> {
  const mod = await import("@electric-sql/pglite");
  return mod.PGlite;
}

export interface SqlRunResult {
  rows: unknown[][];
  columns: string[];
  error: string | null;
  /** Set when the script ran but produced no result set (DDL, INSERT, SET...). */
  notice?: string;
  /** Set when rows were cut off by a max-rows limit. */
  truncated?: boolean;
}

/** Setup scripts are split on a `-- @split` line: PGlite wraps a multi-statement
 * exec() in an implicit transaction, and some statements (VACUUM) refuse to run
 * inside one. Each chunk gets its own exec(). */
export const SETUP_SPLIT = /^[ \t]*--[ \t]*@split[ \t]*$/m;

async function execScript(db: PGlite, script: string): Promise<void> {
  for (const chunk of script.split(SETUP_SPLIT)) {
    if (chunk.trim()) await db.exec(chunk);
  }
}

function toResult(
  result: { fields: { name: string }[]; rows: unknown[] },
  maxRows?: number
): SqlRunResult {
  const columns = result.fields.map((f) => f.name);
  const all = (result.rows as Record<string, unknown>[]).map((row) =>
    columns.map((c) => row[c])
  );
  const truncated = maxRows !== undefined && all.length > maxRows;
  return {
    rows: truncated ? all.slice(0, maxRows) : all,
    columns,
    error: null,
    truncated: truncated || undefined,
  };
}

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/** Runs an SQL exercise in a fresh in-memory Postgres (PGlite):
 * 1. executes the exercise setup SQL, 2. executes the user's SQL,
 * 3. runs the verification query and returns its rows. */
export async function runSqlExercise(
  setupSql: string | undefined,
  userSql: string,
  verificationQuery: string
): Promise<SqlRunResult> {
  const PG = await loadPGlite();
  const db = new PG();
  try {
    if (setupSql && setupSql.trim()) {
      await execScript(db, setupSql);
    }
    if (userSql.trim()) {
      await execScript(db, userSql);
    }
    const result = await db.query(verificationQuery);
    return toResult(result as { fields: { name: string }[]; rows: unknown[] });
  } catch (e) {
    return { rows: [], columns: [], error: message(e) };
  } finally {
    await db.close().catch(() => undefined);
  }
}

/** A long-lived in-browser Postgres for the lesson playground. Unlike
 * runSqlExercise, the same database survives across runs — so a CREATE INDEX in
 * one query changes the plan of the next one, which is the whole point. */
export interface PlaygroundSession {
  run(sql: string, maxRows?: number): Promise<SqlRunResult>;
  reset(): Promise<void>;
  close(): Promise<void>;
}

export async function createPlayground(schemaSql: string): Promise<PlaygroundSession> {
  const PG = await loadPGlite();

  const build = async (): Promise<PGlite> => {
    const db = new PG();
    if (schemaSql.trim()) await execScript(db, schemaSql);
    return db;
  };

  let db = await build();

  return {
    async run(sql, maxRows) {
      if (!sql.trim()) return { rows: [], columns: [], error: null };
      try {
        const results = await db.exec(sql);
        // Report the last statement that actually produced a result set.
        for (let i = results.length - 1; i >= 0; i--) {
          if (results[i].fields.length > 0) return toResult(results[i], maxRows);
        }
        const n = results.length;
        return {
          rows: [],
          columns: [],
          error: null,
          notice: `${n} statement${n === 1 ? "" : "s"} executed`,
        };
      } catch (e) {
        return { rows: [], columns: [], error: message(e) };
      }
    },
    async reset() {
      await db.close().catch(() => undefined);
      db = await build();
    },
    async close() {
      await db.close().catch(() => undefined);
    },
  };
}
