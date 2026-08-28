import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import MultipleChoice from "../components/exercises/MultipleChoice";
import { pick, renderMarkdown } from "../lib/lang";
import type { TestResult } from "../lib/types";
import { useSubmitTestMutation, useTestQuery } from "../store/api";

export default function TestPage() {
  const { slug } = useParams<{ slug: string }>();
  const { t, i18n } = useTranslation();
  const { data: questions, isLoading, isError } = useTestQuery(slug!);
  const [submitTest, { isLoading: submitting }] = useSubmitTestMutation();
  const [answers, setAnswers] = useState<Record<number, Record<string, unknown>>>({});
  const [result, setResult] = useState<TestResult | null>(null);

  if (isLoading) return <p className="text-muted">...</p>;
  if (isError || !questions) return <p className="text-error">{t("loadFailed")}</p>;

  const lang = i18n.language;
  const resultByQuestion = new Map(result?.results.map((r) => [r.question_id, r]));
  const answeredCount = Object.keys(answers).length;

  const submit = async () => {
    const res = await submitTest({ slug: slug!, answers }).unwrap();
    setResult(res);
    window.scrollTo(0, 0);
  };

  const reset = () => {
    setAnswers({});
    setResult(null);
    window.scrollTo(0, 0);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <Link to={`/courses/${slug}`} className="text-sm text-muted hover:text-text">
          ← {t("backToCourse")}
        </Link>
        <h1 className="mt-2 text-xl font-semibold">{t("finalTest")}</h1>
      </div>

      {result && (
        <div className="card mb-6 p-6 text-center">
          <p className="text-sm uppercase tracking-wider text-muted">{t("testResult")}</p>
          <p
            className={`mt-2 text-4xl font-bold ${
              result.score >= 70 ? "text-success" : result.score >= 50 ? "text-warning" : "text-error"
            }`}
          >
            {Math.round(result.score)}%
          </p>
          <p className="mt-1 text-base text-muted">
            {t("questionsCorrect", { correct: result.correct, total: result.total })}
          </p>
          <button className="btn mt-4" onClick={reset}>
            {t("retakeTest")}
          </button>
        </div>
      )}

      <div className="space-y-5">
        {questions.map((q, qi) => {
          const qResult = resultByQuestion.get(q.id);
          const revealed = qResult != null;
          const selected = (answers[q.id]?.selected as number[] | undefined) ?? [];
          return (
            <div key={q.id} className="card p-5">
              <div className="mb-3 flex items-center gap-2">
                <span className="rounded bg-surface2 px-2 py-0.5 font-mono text-2xs text-muted">
                  {qi + 1}/{questions.length}
                </span>
                {revealed && (
                  <span
                    className={`rounded px-2 py-0.5 text-2xs font-medium ${
                      qResult.correct ? "bg-success-soft text-success" : "bg-error-soft text-error"
                    }`}
                  >
                    {qResult.correct ? t("correct") : t("incorrect")}
                  </span>
                )}
              </div>
              <div
                className="prose-content mb-4 text-base"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(pick(q.data.prompt, lang)) }}
              />
              {q.type === "multiple_choice" ? (
                <MultipleChoice
                  options={q.data.options ?? []}
                  multiple={q.data.multiple}
                  selected={selected}
                  onChange={(s) => setAnswers((a) => ({ ...a, [q.id]: { selected: s } }))}
                  disabled={revealed}
                  correctIndexes={
                    revealed ? ((qResult.solution?.correct as number[] | undefined) ?? null) : null
                  }
                />
              ) : (
                <textarea
                  className="input min-h-24 resize-y"
                  placeholder={t("yourAnswer")}
                  value={(answers[q.id]?.text as string | undefined) ?? ""}
                  onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: { text: e.target.value } }))}
                  disabled={revealed}
                />
              )}
              {qResult?.feedback && (
                <div className="mt-3 rounded-lg border border-border bg-surface2 px-4 py-3 text-sm">
                  {qResult.feedback}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!result && (
        <div className="sticky bottom-[calc(var(--bottom-nav-h)+8px)] mt-6 flex justify-center sm:bottom-4">
          <button
            className="btn btn-primary shadow-lg"
            onClick={submit}
            disabled={submitting || answeredCount === 0}
          >
            {submitting
              ? t("checking")
              : `${t("submitTest")} (${answeredCount}/${questions.length})`}
          </button>
        </div>
      )}
    </div>
  );
}
