import { sql } from "@codemirror/lang-sql";
import CodeMirror from "@uiw/react-codemirror";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { runSqlExercise, type SqlRunResult } from "../../lib/pglite";
import type { RootState } from "../../store";
import SqlResult from "./SqlResult";

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
        <details className="rounded-lg border border-border bg-surface2 px-3 py-2 text-xs">
          <summary className="cursor-pointer font-medium text-muted">{t("schemaLabel")}</summary>
          <pre className="scroll-x mt-2 font-mono text-2xs text-muted">{setupSql}</pre>
        </details>
      )}
      <div className="overflow-hidden rounded-lg border border-border">
        <CodeMirror
          value={value}
          minHeight="120px"
          maxHeight="45vh"
          theme={theme === "dark" ? "dark" : "light"}
          extensions={[sql()]}
          onChange={onChange}
          editable={!disabled}
          basicSetup={{ lineNumbers: true, foldGutter: false }}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn" onClick={run} disabled={disabled || running || !value.trim()}>
          {running ? "..." : t("runSql")}
        </button>
        {result?.error && <span className="text-xs text-error">{t("sqlError")}: {result.error}</span>}
      </div>
      {result && <SqlResult result={result} />}
    </div>
  );
}
