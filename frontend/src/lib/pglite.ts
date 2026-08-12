import { PGlite } from "@electric-sql/pglite";

export interface SqlRunResult {
  rows: unknown[][];
  columns: string[];
  error: string | null;
}

/** Runs an SQL exercise in a fresh in-memory Postgres (PGlite):
 * 1. executes the exercise setup SQL, 2. executes the user's SQL,
 * 3. runs the verification query and returns its rows. */
export async function runSqlExercise(
  setupSql: string | undefined,
  userSql: string,
  verificationQuery: string
): Promise<SqlRunResult> {
  const db = new PGlite();
  try {
    if (setupSql && setupSql.trim()) {
      await db.exec(setupSql);
    }
    if (userSql.trim()) {
      await db.exec(userSql);
    }
    const result = await db.query(verificationQuery);
    const columns = result.fields.map((f) => f.name);
    const rows = (result.rows as Record<string, unknown>[]).map((row) =>
      columns.map((c) => row[c])
    );
    return { rows, columns, error: null };
  } catch (e) {
    return { rows: [], columns: [], error: e instanceof Error ? e.message : String(e) };
  } finally {
    await db.close().catch(() => undefined);
  }
}
