import { sql } from "@codemirror/lang-sql";
import CodeMirror from "@uiw/react-codemirror";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { runSqlExercise, type SqlRunResult } from "../../lib/pglite";
import type { RootState } from "../../store";

interface Props {
  setupSql?: string;
  verificationQuery: string;
  value: string;
  onChange: (sqlText: string) => void;
  onResult: (result: SqlRunResult) => void;
  disabled?: boolean;
}

/** Real SQL exercise: user SQL runs in an in-browser Postgres (PGlite).
 * The verification query's rows are what gets graded by the backend. */
export default function SqlExercise({
  setupSql,
  verificationQuery,
  value,
  onChange,
  onResult,
  disabled,
}: Props) {
  const { t } = useTranslation();
  const theme = useSelector((s: RootState) => s.auth.user?.theme ?? "dark");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SqlRunResult | null>(null);

  const run = async () => {
    setRunning(true);
    try {
      const res = await runSqlExercise(setupSql, value, verificationQuery);
      setResult(res);
      onResult(res);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-3">
      {setupSql && setupSql.trim() && (
        <details className="rounded-lg border border-border bg-surface2 px-3 py-2 text-[12.5px]">
          <summary className="cursor-pointer font-medium text-muted">Schema / setup SQL</summary>
          <pre className="mt-2 overflow-x-auto font-mono text-[12px] text-muted">{setupSql}</pre>
        </details>
      )}
      <div className="overflow-hidden rounded-lg border border-border">
        <CodeMirror
          value={value}
          height="140px"
          theme={theme === "dark" ? "dark" : "light"}
          extensions={[sql()]}
          onChange={onChange}
          editable={!disabled}
          basicSetup={{ lineNumbers: true, foldGutter: false }}
        />
      </div>
      <div className="flex items-center gap-3">
        <button type="button" className="btn" onClick={run} disabled={disabled || running || !value.trim()}>
          {running ? "..." : t("runSql")}
        </button>
        {result?.error && <span className="text-[12.5px] text-error">{t("sqlError")}: {result.error}</span>}
      </div>
      {result && !result.error && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-[12.5px]">
            <thead>
              <tr className="bg-surface2 text-left text-muted">
                {result.columns.map((c) => (
                  <th key={c} className="border-b border-border px-3 py-1.5 font-mono font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.length === 0 && (
                <tr>
                  <td className="px-3 py-2 text-muted" colSpan={result.columns.length || 1}>
                    0 rows
                  </td>
                </tr>
              )}
              {result.rows.map((row, i) => (
                <tr key={i} className="border-b border-border last:border-b-0">
                  {row.map((v, j) => (
                    <td key={j} className="px-3 py-1.5 font-mono">
                      {v === null ? "NULL" : String(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
