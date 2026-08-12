import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { pick, renderMarkdown } from "../../lib/lang";
import type { SqlRunResult } from "../../lib/pglite";
import type { AttemptResponse, Exercise } from "../../lib/types";
import { useLazyRevealSolutionQuery, useSubmitAttemptMutation } from "../../store/api";
import CodeExercise from "./CodeExercise";
import Matching from "./Matching";
import MultipleChoice from "./MultipleChoice";
import Ordering from "./Ordering";
import SqlExercise from "./SqlExercise";
import TableBuilder, { type TableColumn } from "./TableBuilder";

interface Props {
  exercise: Exercise;
  index: number;
  onSolved?: () => void;
}

function shuffle<T>(arr: T[]): T[] {
  const copy = [...arr];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

export default function ExerciseCard({ exercise, index, onSolved }: Props) {
  const { t, i18n } = useTranslation();
  const [submitAttempt, { isLoading }] = useSubmitAttemptMutation();
  const [result, setResult] = useState<AttemptResponse | null>(null);
  const [llmError, setLlmError] = useState(false);
  const [revealSolution, reveal] = useLazyRevealSolutionQuery();
  const [showReveal, setShowReveal] = useState(false);

  // Per-type answer state
  const [selected, setSelected] = useState<number[]>([]);
  const [pairs, setPairs] = useState<Record<string, string>>({});
  const initialOrder = useMemo(
    () => shuffle((exercise.data.items ?? []).map((i) => i.id)),
    [exercise.id]
  );
  const [order, setOrder] = useState<string[]>(initialOrder);
  const [columns, setColumns] = useState<TableColumn[]>([]);
  const [sqlText, setSqlText] = useState(exercise.data.starter_code ?? "");
  const [sqlResult, setSqlResult] = useState<SqlRunResult | null>(null);
  const [text, setText] = useState(exercise.data.starter_code ?? "");

  const solved = result?.correct === true;
  const answered = result !== null;
  const disabled = solved || isLoading;

  const buildAnswer = (): Record<string, unknown> | null => {
    switch (exercise.type) {
      case "multiple_choice":
        return selected.length ? { selected } : null;
      case "matching":
        return Object.keys(pairs).length === (exercise.data.left?.length ?? 0) ? { pairs } : null;
      case "ordering":
        return { order };
      case "table_builder":
        return columns.length ? { columns } : null;
      case "sql":
        return sqlResult && !sqlResult.error ? { rows: sqlResult.rows, sql: sqlText } : null;
      case "code":
      case "open_text":
        return text.trim() ? { text } : null;
      default:
        return null;
    }
  };

  const answer = buildAnswer();

  const submit = async () => {
    if (!answer) return;
    setLlmError(false);
    try {
      const res = await submitAttempt({ exerciseId: exercise.id, answer }).unwrap();
      setResult(res);
      if (res.correct) onSolved?.();
    } catch (err: unknown) {
      if ((err as { status?: number }).status === 503) setLlmError(true);
    }
  };

  const retry = () => {
    setResult(null);
  };

  const toggleReveal = () => {
    if (!reveal.data && !reveal.isFetching) revealSolution(exercise.id, true);
    setShowReveal((v) => !v);
  };

  const correctIndexes =
    answered && exercise.type === "multiple_choice"
      ? ((result?.solution?.correct as number[] | undefined) ?? null)
      : null;

  const explanation = result?.solution?.explanation as
    | { en: string; es: string }
    | undefined;

  return (
    <div className="card p-5">
      <div className="mb-3 flex items-center gap-2">
        <span className="rounded bg-surface2 px-2 py-0.5 font-mono text-[11px] text-muted">
          {t("exercise")} {index + 1}
        </span>
        {exercise.validation_mode === "llm" && (
          <span className="rounded bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent">
            AI
          </span>
        )}
      </div>
      <div
        className="prose-content mb-4 text-[14px]"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(pick(exercise.data.prompt, i18n.language)) }}
      />
      {exercise.data.hint && (
        <details className="mb-3 text-[13px]">
          <summary className="cursor-pointer text-muted hover:text-text">{t("hint")}</summary>
          <p className="mt-1 text-muted">{pick(exercise.data.hint, i18n.language)}</p>
        </details>
      )}

      {exercise.type === "multiple_choice" && (
        <MultipleChoice
          options={exercise.data.options ?? []}
          multiple={exercise.data.multiple}
          selected={selected}
          onChange={(s) => {
            setSelected(s);
            setResult(null);
          }}
          disabled={disabled}
          correctIndexes={correctIndexes}
        />
      )}
      {exercise.type === "matching" && (
        <Matching
          left={exercise.data.left ?? []}
          right={exercise.data.right ?? []}
          pairs={pairs}
          onChange={(p) => {
            setPairs(p);
            setResult(null);
          }}
          disabled={disabled}
        />
      )}
      {exercise.type === "ordering" && (
        <Ordering
          items={exercise.data.items ?? []}
          order={order}
          onChange={(o) => {
            setOrder(o);
            setResult(null);
          }}
          disabled={disabled}
          layout={exercise.data.layout}
        />
      )}
      {exercise.type === "table_builder" && (
        <TableBuilder
          columns={columns}
          onChange={(c) => {
            setColumns(c);
            setResult(null);
          }}
          typeOptions={exercise.data.type_options}
          disabled={disabled}
        />
      )}
      {exercise.type === "sql" && (
        <SqlExercise
          setupSql={exercise.data.setup_sql}
          verificationQuery={exercise.data.verification_query ?? "SELECT 1"}
          value={sqlText}
          onChange={(v) => {
            setSqlText(v);
            setResult(null);
          }}
          onResult={setSqlResult}
          disabled={disabled}
        />
      )}
      {exercise.type === "code" && (
        <CodeExercise
          language={exercise.data.language}
          value={text}
          onChange={(v) => {
            setText(v);
            setResult(null);
          }}
          disabled={disabled}
        />
      )}
      {exercise.type === "open_text" && (
        <textarea
          className="input min-h-24 resize-y"
          placeholder={t("yourAnswer")}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setResult(null);
          }}
          disabled={disabled}
        />
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {!solved && (
          <button className="btn btn-primary" onClick={submit} disabled={!answer || isLoading}>
            {isLoading ? t("checking") : t("check")}
          </button>
        )}
        {answered && !solved && (
          <button className="btn" onClick={retry}>
            {t("tryAgain")}
          </button>
        )}
        {exercise.validation_mode === "llm" && !solved && (
          <button
            className="btn text-[13px]"
            onClick={toggleReveal}
            disabled={reveal.isFetching}
            aria-expanded={showReveal}
          >
            {reveal.isFetching
              ? t("generatingAnswer")
              : showReveal
                ? t("hideCorrectAnswer")
                : t("showCorrectAnswer")}
          </button>
        )}
        {answered && (
          <span
            className={`rounded-md px-3 py-1.5 text-[13px] font-medium ${
              solved ? "bg-success-soft text-success" : "bg-error-soft text-error"
            }`}
          >
            {solved ? t("correct") : t("incorrect")}
          </span>
        )}
      </div>

      {llmError && <p className="mt-3 text-[13px] text-warning">{t("aiUnavailable")}</p>}
      {showReveal && reveal.isError && (
        <p className="mt-3 text-[13px] text-warning">{t("aiUnavailable")}</p>
      )}
      {showReveal && reveal.data && (
        <div className="mt-3 rounded-lg border border-accent/30 bg-accent-soft/40 px-4 py-3 text-[13.5px]">
          <p className="mb-1 text-[12px] font-medium uppercase tracking-wide text-accent">
            {t("correctAnswer")}
          </p>
          <div
            className="prose-content"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(reveal.data.answer) }}
          />
        </div>
      )}
      {result?.feedback && (
        <div className="mt-3 rounded-lg border border-border bg-surface2 px-4 py-3 text-[13.5px]">
          {result.feedback}
        </div>
      )}
      {answered && explanation && (
        <div className="mt-3 rounded-lg border border-border bg-surface2 px-4 py-3 text-[13.5px]">
          <p className="mb-1 text-[12px] font-medium uppercase tracking-wide text-muted">
            {t("explanation")}
          </p>
          <div
            className="prose-content"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(pick(explanation, i18n.language)) }}
          />
        </div>
      )}
    </div>
  );
}
