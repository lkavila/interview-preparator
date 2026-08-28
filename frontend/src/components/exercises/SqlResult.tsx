import { useTranslation } from "react-i18next";
import type { SqlRunResult } from "../../lib/pglite";

/** Renders the rows of an SQL run. EXPLAIN output comes back as a single
 * `QUERY PLAN` text column — unreadable in table cells, so it gets a monospace
 * <pre> that scrolls sideways instead. */
export default function SqlResult({ result }: { result: SqlRunResult }) {
  const { t } = useTranslation();

  if (result.error) return null;

  if (result.notice) {
    return <p className="text-xs text-muted">{t("statementsRun")}</p>;
  }

  const isPlan = result.columns.length === 1 && result.columns[0] === "QUERY PLAN";

  if (isPlan) {
    return (
      <pre className="scroll-x rounded-lg border border-border bg-surface2 px-3 py-2.5 font-mono text-xs leading-relaxed whitespace-pre">
        {result.rows.map((r) => String(r[0] ?? "")).join("\n")}
      </pre>
    );
  }

  return (
    <div className="space-y-1.5">
      <div className="scroll-x rounded-lg border border-border">
        <table className="w-full text-xs">
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
                  {t("noRows")}
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
      {result.truncated && (
        <p className="text-2xs text-muted">{t("rowsTruncated", { count: result.rows.length })}</p>
      )}
    </div>
  );
}
