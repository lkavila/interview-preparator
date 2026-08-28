import { sql } from "@codemirror/lang-sql";
import CodeMirror from "@uiw/react-codemirror";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import SqlResult from "../exercises/SqlResult";
import { pick } from "../../lib/lang";
import { createPlayground, type PlaygroundSession, type SqlRunResult } from "../../lib/pglite";
import type { LessonComponentConfig } from "../../lib/types";
import type { RootState } from "../../store";

/** A real Postgres (PGlite/wasm) the learner can type into. The session is kept
 * alive across runs on purpose: CREATE INDEX in one query has to change the plan
 * of the next one, otherwise the lesson teaches nothing. Boot is lazy — the wasm
 * costs a few seconds, so nothing loads until the learner asks for it. */
export default function SqlPlayground({ config }: { config: LessonComponentConfig }) {
  const { t, i18n } = useTranslation();
  const theme = useSelector((s: RootState) => s.auth.user?.theme ?? "dark");
  const sessionRef = useRef<PlaygroundSession | null>(null);
  const [status, setStatus] = useState<"idle" | "booting" | "ready" | "error">("idle");
  const [bootError, setBootError] = useState<string | null>(null);
  const [query, setQuery] = useState(config.initial_query ?? "");
  const [result, setResult] = useState<SqlRunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    return () => {
      sessionRef.current?.close();
      sessionRef.current = null;
    };
  }, []);

  const boot = async () => {
    setStatus("booting");
    setBootError(null);
    try {
      sessionRef.current = await createPlayground(config.schema_sql ?? "");
      setStatus("ready");
    } catch (e) {
      setBootError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  };

  const run = async () => {
    const session = sessionRef.current;
    if (!session) return;
    setRunning(true);
    try {
      setResult(await session.run(query, config.max_rows ?? 100));
    } finally {
      setRunning(false);
    }
  };

  const reset = async () => {
    const session = sessionRef.current;
    if (!session) return;
    setResetting(true);
    try {
      await session.reset();
      setResult(null);
      setQuery(config.initial_query ?? "");
    } finally {
      setResetting(false);
    }
  };

  const title = config.title ? pick(config.title, i18n.language) : t("sqlPlayground");

  return (
    <section className="card p-4 sm:p-5">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">{title}</h3>
      {config.intro && (
        <p className="mb-3 text-sm text-muted">{pick(config.intro, i18n.language)}</p>
      )}

      {status !== "ready" && (
        <div className="space-y-3">
          <p className="text-sm text-muted">{t("playgroundHint")}</p>
          <button className="btn btn-primary" onClick={boot} disabled={status === "booting"}>
            {status === "booting" ? t("bootingDb") : t("startPlayground")}
          </button>
          {bootError && <p className="text-sm text-error">{bootError}</p>}
        </div>
      )}

      {status === "ready" && (
        <div className="space-y-3">
          {config.schema_sql && (
            <details className="rounded-lg border border-border bg-surface2 px-3 py-2 text-xs">
              <summary className="cursor-pointer font-medium text-muted">{t("schemaLabel")}</summary>
              <pre className="scroll-x mt-2 font-mono text-2xs text-muted">{config.schema_sql}</pre>
            </details>
          )}

          {config.samples && config.samples.length > 0 && (
            <div>
              <p className="mb-1.5 text-2xs font-medium uppercase tracking-wider text-muted">
                {t("sampleQueries")}
              </p>
              <div className="flex flex-wrap gap-2">
                {config.samples.map((sample, i) => (
                  <button
                    key={i}
                    type="button"
                    className="btn !py-1.5 text-xs"
                    onClick={() => setQuery(sample.sql)}
                  >
                    {pick(sample.label, i18n.language)}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="overflow-hidden rounded-lg border border-border">
            <CodeMirror
              value={query}
              minHeight="130px"
              maxHeight="40vh"
              theme={theme === "dark" ? "dark" : "light"}
              extensions={[sql()]}
              onChange={setQuery}
              basicSetup={{ lineNumbers: true, foldGutter: false }}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button className="btn btn-primary" onClick={run} disabled={running || !query.trim()}>
              {running ? t("running") : t("runQuery")}
            </button>
            <button className="btn" onClick={reset} disabled={resetting || running}>
              {resetting ? t("running") : t("resetDb")}
            </button>
          </div>

          {result?.error && <p className="text-sm text-error">{result.error}</p>}
          {result && <SqlResult result={result} />}
        </div>
      )}
    </section>
  );
}
