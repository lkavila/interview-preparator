import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import QuestionFigure from "../components/exam/QuestionFigure";
import MultipleChoice from "../components/exercises/MultipleChoice";
import { formatClock, pick, renderMarkdown } from "../lib/lang";
import type { Bilingual, TestResult } from "../lib/types";
import {
  useCourseQuery,
  useExamQuery,
  useSubmitExamMutation,
  useSubmitTestMutation,
  useTestQuery,
} from "../store/api";

export default function TestPage() {
  const { slug, examSlug } = useParams<{ slug: string; examSlug?: string }>();
  const { t, i18n } = useTranslation();

  const testQuery = useTestQuery(slug!, { skip: !!examSlug });
  const examQuery = useExamQuery({ slug: slug!, examSlug: examSlug! }, { skip: !examSlug });
  const { data: questions, isLoading, isError } = examSlug ? examQuery : testQuery;

  // Exam metadata (title, pass mark, time limit) travels with the course detail.
  const { data: course } = useCourseQuery(slug!);
  const exam = examSlug ? course?.exams.find((e) => e.slug === examSlug) : undefined;

  const [submitTest, { isLoading: submittingTest }] = useSubmitTestMutation();
  const [submitExam, { isLoading: submittingExam }] = useSubmitExamMutation();
  const submitting = submittingTest || submittingExam;

  const [answers, setAnswers] = useState<Record<number, Record<string, unknown>>>({});
  const [result, setResult] = useState<TestResult | null>(null);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [timedOut, setTimedOut] = useState(false);

  // Latest answers without re-creating submit() on every keystroke (the timer holds a ref to it).
  const answersRef = useRef(answers);
  answersRef.current = answers;
  const resultRef = useRef<TestResult | null>(result);
  resultRef.current = result;

  const submit = useCallback(async () => {
    if (resultRef.current) return;
    const payload = answersRef.current;
    const res = examSlug
      ? await submitExam({ slug: slug!, examSlug, answers: payload }).unwrap()
      : await submitTest({ slug: slug!, answers: payload }).unwrap();
    setResult(res);
    setSecondsLeft(null);
    window.scrollTo(0, 0);
  }, [examSlug, slug, submitExam, submitTest]);

  // Countdown for exams that declare a time limit; auto-submits when it hits zero.
  const limitMinutes = exam?.time_limit_minutes ?? null;
  useEffect(() => {
    if (limitMinutes == null || !questions || result) return;
    const deadline = Date.now() + limitMinutes * 60_000;
    setSecondsLeft(Math.round(limitMinutes * 60));
    const id = window.setInterval(() => {
      const left = Math.round((deadline - Date.now()) / 1000);
      setSecondsLeft(left);
      if (left <= 0) {
        window.clearInterval(id);
        setTimedOut(true);
        void submit();
      }
    }, 1000);
    return () => window.clearInterval(id);
    // Restart only when a new exam is loaded, never on every answer.
  }, [limitMinutes, questions, result, submit]);

  if (isLoading) return <p className="text-muted">...</p>;
  if (isError || !questions) return <p className="text-error">{t("loadFailed")}</p>;

  const lang = i18n.language;
  const resultByQuestion = new Map(result?.results.map((r) => [r.question_id, r]));
  const answeredCount = Object.keys(answers).length;
  const unanswered = questions.length - answeredCount;
  const passScore = result?.pass_score ?? exam?.pass_score ?? 70;
  const title = exam ? pick(exam.title, lang) : t("finalTest");

  const reset = () => {
    setAnswers({});
    setResult(null);
    setTimedOut(false);
    setSecondsLeft(limitMinutes == null ? null : Math.round(limitMinutes * 60));
    window.scrollTo(0, 0);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <Link to={`/courses/${slug}`} className="text-sm text-muted hover:text-text">
          ← {t("backToCourse")}
        </Link>
        <h1 className="mt-2 text-xl font-semibold">{title}</h1>
        <p className="mt-1 text-sm text-muted">
          {questions.length} {t("questionsLabel")} · {t("passMark")}: {Math.round(passScore)}%
        </p>
      </div>

      {secondsLeft != null && !result && (
        <div
          className={`sticky top-2 z-10 mb-4 flex items-center justify-between rounded-lg border px-4 py-2 text-sm ${
            secondsLeft <= 120
              ? "border-error bg-error-soft text-error"
              : "border-border bg-surface2 text-muted"
          }`}
        >
          <span>{t("timeLeft")}</span>
          <span className="font-mono text-base">{formatClock(secondsLeft)}</span>
        </div>
      )}

      {result && (
        <div className="card mb-6 p-6 text-center">
          <p className="text-sm uppercase tracking-wider text-muted">{t("testResult")}</p>
          <p
            className={`mt-2 text-4xl font-bold ${
              result.score >= passScore
                ? "text-success"
                : result.score >= passScore - 15
                  ? "text-warning"
                  : "text-error"
            }`}
          >
            {Math.round(result.score)}%
          </p>
          <p className="mt-1 text-base text-muted">
            {t("questionsCorrect", { correct: result.correct, total: result.total })}
          </p>
          <p
            className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-medium ${
              result.score >= passScore
                ? "bg-success-soft text-success"
                : "bg-error-soft text-error"
            }`}
          >
            {result.score >= passScore ? t("passed") : t("notPassed")}
          </p>
          {timedOut && <p className="mt-3 text-sm text-warning">{t("timeUp")}</p>}
          <div>
            <button className="btn mt-4" onClick={reset}>
              {examSlug ? t("retakeExam") : t("retakeTest")}
            </button>
          </div>
        </div>
      )}

      <div className="space-y-5">
        {questions.map((q, qi) => {
          const qResult = resultByQuestion.get(q.id);
          const revealed = qResult != null;
          const selected = (answers[q.id]?.selected as number[] | undefined) ?? [];
          const explanation = qResult?.solution?.explanation as Bilingual | undefined;
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
              <QuestionFigure svg={q.svg_content ?? q.data.svg_content} />
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
              {revealed && explanation && (
                <div className="mt-3 rounded-lg border border-border bg-surface2 px-4 py-3">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted">
                    {t("explanation")}
                  </p>
                  <div
                    className="prose-content text-sm"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(pick(explanation, lang)) }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!result && (
        <div className="sticky bottom-[calc(var(--bottom-nav-h)+8px)] mt-6 flex flex-col items-center gap-2 sm:bottom-4">
          {unanswered > 0 && answeredCount > 0 && (
            <p className="rounded bg-surface2 px-3 py-1 text-2xs text-muted">
              {t("unansweredWarning", { count: unanswered })}
            </p>
          )}
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
