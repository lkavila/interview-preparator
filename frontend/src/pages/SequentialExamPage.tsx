import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import ExamCountdown from "../components/exam/ExamCountdown";
import QuestionFigure from "../components/exam/QuestionFigure";
import MultipleChoice from "../components/exercises/MultipleChoice";
import { pick, renderMarkdown } from "../lib/lang";
import type {
  Bilingual,
  ExamSessionResponse,
  ExamSessionState,
  QuestionCategory,
  TestResult,
} from "../lib/types";
import {
  useCourseQuery,
  useLazyExamSessionQuery,
  useStartExamMutation,
  useSubmitExamMutation,
} from "../store/api";

/** Where the in-flight session token is parked so a reload can pick it back up.
 * sessionStorage, not localStorage: an attempt belongs to one tab. */
const tokenKey = (slug: string, examSlug: string) => `exam-session:${slug}:${examSlug}`;
/** Answers are kept per session token: resuming the clock is only worth doing if
 * the answers already given survive the reload too. */
const draftKey = (token: string) => `exam-draft:${token}`;

interface Draft {
  index: number;
  answers: Record<number, Record<string, unknown>>;
}

/** sessionStorage throws outright in some privacy modes, so every access is
 * guarded and simply falls back to running the attempt without a draft. */
function readStore(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStore(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value);
  } catch {
    // The attempt still works; it just will not survive a reload.
  }
}

function clearStore(...keys: string[]): void {
  try {
    for (const key of keys) sessionStorage.removeItem(key);
  } catch {
    // ignored
  }
}

function readDraft(token: string): Draft | null {
  const raw = readStore(draftKey(token));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Draft;
    return typeof parsed?.index === "number" && parsed.answers ? parsed : null;
  } catch {
    return null;
  }
}

/** Turns the server's timestamps into a local-clock deadline.
 *
 * The offset cancels out any skew in the browser's own clock, so moving the
 * system time forward neither shortens nor extends the attempt. */
function toSessionState(res: ExamSessionResponse): ExamSessionState {
  const offset = new Date(res.server_time).getTime() - Date.now();
  return {
    token: res.session_token,
    questions: res.questions,
    deadline: new Date(res.expires_at).getTime() - offset,
    passScore: res.pass_score,
    timeLimitMinutes: res.time_limit_minutes,
  };
}

export default function SequentialExamPage() {
  const { slug, examSlug } = useParams<{ slug: string; examSlug: string }>();
  const { t, i18n } = useTranslation();
  const lang = i18n.language;

  const { data: course } = useCourseQuery(slug!);
  const exam = course?.exams.find((e) => e.slug === examSlug);

  const [startExam] = useStartExamMutation();
  const [fetchSession] = useLazyExamSessionQuery();
  const [submitExam, { isLoading: submitting }] = useSubmitExamMutation();

  const [session, setSession] = useState<ExamSessionState | null>(null);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, Record<string, unknown>>>({});
  const [result, setResult] = useState<TestResult | null>(null);
  const [locked, setLocked] = useState(false);
  const [failed, setFailed] = useState(false);

  // The countdown fires from an interval, so it reads the latest answers through
  // a ref instead of forcing submit() to be rebuilt on every click.
  const answersRef = useRef(answers);
  answersRef.current = answers;
  const sessionRef = useRef(session);
  sessionRef.current = session;
  const submittedRef = useRef(false);
  const bootstrappedFor = useRef<string | null>(null);

  // Resume the attempt this tab already had, otherwise open a new one.
  //
  // The ref guard is what makes this safe under StrictMode, which mounts effects
  // twice in dev: without it the second mount would burn a second draw. It also
  // means the effect must NOT discard its result on cleanup — the first mount's
  // cleanup would throw away the only bootstrap that ever runs.
  useEffect(() => {
    if (!slug || !examSlug) return;
    const key = tokenKey(slug, examSlug);
    if (bootstrappedFor.current === key) return;
    bootstrappedFor.current = key;

    void (async () => {
      const stored = readStore(key);
      if (stored) {
        try {
          const res = await fetchSession({ slug, token: stored }).unwrap();
          // The server rejects submitted, expired and stale sessions outright,
          // but an empty set would leave nothing to render, so it is treated as
          // a miss here too rather than trusted.
          if (res.questions.length === 0) throw new Error("resumed session has no questions");
          const resumed = toSessionState(res);
          const draft = readDraft(stored);
          if (draft) {
            setAnswers(draft.answers);
            setIndex(Math.min(draft.index, resumed.questions.length - 1));
          }
          setSession(resumed);
          return;
        } catch {
          // Submitted, expired, stale or unknown: start a new attempt instead.
          clearStore(key, draftKey(stored));
        }
      }
      try {
        const res = await startExam({ slug, examSlug }).unwrap();
        writeStore(key, res.session_token);
        setSession(toSessionState(res));
      } catch {
        setFailed(true);
      }
    })();
  }, [slug, examSlug, fetchSession, startExam]);

  const submit = useCallback(async () => {
    const current = sessionRef.current;
    if (!current || submittedRef.current) return;
    submittedRef.current = true;
    setLocked(true);
    try {
      const res = await submitExam({
        slug: slug!,
        examSlug: examSlug!,
        answers: answersRef.current,
        sessionToken: current.token,
      }).unwrap();
      setResult(res);
      clearStore(tokenKey(slug!, examSlug!), draftKey(current.token));
      window.scrollTo(0, 0);
    } catch {
      // Let the candidate retry instead of losing the attempt to one bad request.
      submittedRef.current = false;
      setLocked(false);
      setFailed(true);
    }
  }, [examSlug, slug, submitExam]);

  const questions = session?.questions ?? [];
  const question = questions[index];
  const total = questions.length;
  const isLast = index === total - 1;

  const select = useCallback(
    (selected: number[]) => {
      if (locked || !question) return;
      setAnswers((a) => ({ ...a, [question.id]: { selected } }));
    },
    [locked, question]
  );

  // Keep the draft current so a reload picks up where the candidate left off.
  useEffect(() => {
    if (!session || result) return;
    writeStore(draftKey(session.token), JSON.stringify({ index, answers }));
  }, [answers, index, result, session]);

  /** Drops whatever this tab was holding and asks the server for a new draw. */
  const restart = useCallback(() => {
    if (slug && examSlug) {
      const key = tokenKey(slug, examSlug);
      const stored = readStore(key);
      clearStore(key, ...(stored ? [draftKey(stored)] : []));
    }
    window.location.reload();
  }, [examSlug, slug]);

  const advance = useCallback(() => {
    if (locked) return;
    if (isLast) void submit();
    else setIndex((i) => i + 1);
  }, [isLast, locked, submit]);

  // Keyboard-first: at roughly 14 seconds per question, reaching for the mouse costs.
  useEffect(() => {
    if (locked || result || !question) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const optionCount = question.data.options?.length ?? 0;
      if (/^[1-9]$/.test(e.key)) {
        const i = Number(e.key) - 1;
        if (i < optionCount) {
          e.preventDefault();
          if (question.data.multiple) {
            // Multi-answer items toggle, so a key can also undo a choice.
            const current = (answersRef.current[question.id]?.selected as number[]) ?? [];
            select(current.includes(i) ? current.filter((x) => x !== i) : [...current, i]);
          } else {
            select([i]);
          }
        }
        return;
      }
      if (e.key === "Enter" || e.key === "ArrowRight") {
        e.preventDefault();
        advance();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance, locked, question, result, select]);

  const byCategory = useMemo(() => {
    if (!result) return [];
    const outcome = new Map(result.results.map((r) => [r.question_id, r.correct]));
    const tally = new Map<QuestionCategory, { correct: number; total: number }>();
    for (const q of questions) {
      if (!q.category) continue;
      const row = tally.get(q.category) ?? { correct: 0, total: 0 };
      row.total += 1;
      if (outcome.get(q.id)) row.correct += 1;
      tally.set(q.category, row);
    }
    return [...tally.entries()];
  }, [questions, result]);

  // A session that carries no questions cannot be rendered at all, so it is
  // surfaced as a failure rather than left looking like a slow load.
  const unusable = session != null && questions.length === 0;
  if ((failed && !session) || unusable) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="card p-6 text-center">
          <p className="text-error">{t("examStartFailed")}</p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
            <button className="btn btn-primary" onClick={restart}>
              {t("startFreshAttempt")}
            </button>
            <Link to={`/courses/${slug}`} className="btn">
              {t("backToCourse")}
            </Link>
          </div>
        </div>
      </div>
    );
  }
  if (!session || !question) return <p className="text-muted">...</p>;

  const passScore = result?.pass_score ?? session.passScore;
  const answered = Object.keys(answers).length;
  const title = exam ? pick(exam.title, lang) : t("practiceExams");

  // ---- Results ------------------------------------------------------------
  if (result) {
    const resultByQuestion = new Map(result.results.map((r) => [r.question_id, r]));
    return (
      <div className="mx-auto max-w-3xl">
        <Link to={`/courses/${slug}`} className="text-sm text-muted hover:text-text">
          &larr; {t("backToCourse")}
        </Link>

        <div className="card mb-6 mt-2 p-6 text-center">
          <p className="text-sm uppercase tracking-wider text-muted">{t("testResult")}</p>
          <p
            className={`mt-2 text-4xl font-bold ${
              result.score >= passScore ? "text-success" : "text-error"
            }`}
          >
            {result.correct}/{result.total}
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

          {result.timed_out && (
            <p className="mt-3 rounded-lg border border-warning bg-surface2 px-4 py-2 text-sm text-warning">
              {t("timeExceeded")} {t("attemptNotCounted")}
            </p>
          )}

          {byCategory.length > 0 && (
            <div className="mt-5 grid grid-cols-3 gap-3 text-left">
              {byCategory.map(([category, row]) => (
                <div key={category} className="rounded-lg border border-border bg-surface2 p-3">
                  <p className="text-2xs uppercase tracking-wider text-muted">
                    {t(`category_${category}`)}
                  </p>
                  <p className="mt-1 font-mono text-lg">
                    {row.correct}/{row.total}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-5">
          {questions.map((q, qi) => {
            const qResult = resultByQuestion.get(q.id);
            const explanation = qResult?.solution?.explanation as Bilingual | undefined;
            return (
              <div key={q.id} className="card p-5">
                <div className="mb-3 flex items-center gap-2">
                  <span className="rounded bg-surface2 px-2 py-0.5 font-mono text-2xs text-muted">
                    {qi + 1}/{total}
                  </span>
                  <span
                    className={`rounded px-2 py-0.5 text-2xs font-medium ${
                      qResult?.correct ? "bg-success-soft text-success" : "bg-error-soft text-error"
                    }`}
                  >
                    {qResult?.correct ? t("correct") : t("incorrect")}
                  </span>
                </div>
                <div
                  className="prose-content mb-4 text-base"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(pick(q.data.prompt, lang)) }}
                />
                <QuestionFigure svg={q.svg_content ?? q.data.svg_content} />
                <MultipleChoice
                  options={q.data.options ?? []}
                  multiple={q.data.multiple}
                  selected={(answers[q.id]?.selected as number[] | undefined) ?? []}
                  onChange={() => undefined}
                  disabled
                  correctIndexes={(qResult?.solution?.correct as number[] | undefined) ?? null}
                />
                {explanation && (
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
      </div>
    );
  }

  // ---- Attempt in progress ------------------------------------------------
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-4 text-xl font-semibold">{title}</h1>

      <ExamCountdown deadline={session.deadline} onExpire={submit} />

      <div className="mb-4">
        <div className="mb-1 flex items-center justify-between text-2xs text-muted">
          <span>{t("questionOf", { current: index + 1, total })}</span>
          <span>{t("answeredCount", { answered, total })}</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface2">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${((index + 1) / total) * 100}%` }}
          />
        </div>
      </div>

      <div className="card p-5">
        <div
          className="prose-content mb-4 text-base"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(pick(question.data.prompt, lang)) }}
        />
        <QuestionFigure svg={question.svg_content ?? question.data.svg_content} />
        <MultipleChoice
          options={question.data.options ?? []}
          multiple={question.data.multiple}
          selected={(answers[question.id]?.selected as number[] | undefined) ?? []}
          onChange={select}
          disabled={locked}
        />
      </div>

      {locked && !result && <p className="mt-4 text-center text-sm text-warning">{t("timeUp")}</p>}
      {failed && session && (
        <p className="mt-4 rounded-lg border border-error bg-error-soft px-4 py-2 text-center text-sm text-error">
          {t("submitFailed")}
        </p>
      )}

      <div className="mb-[calc(var(--bottom-nav-h)+16px)] mt-6 flex flex-col items-center gap-2 sm:mb-4">
        <button
          className="btn btn-primary shadow-lg"
          onClick={advance}
          disabled={locked || submitting}
        >
          {submitting ? t("checking") : isLast ? t("finishExam") : t("nextQuestion")}
        </button>
        <p className="text-2xs text-muted">{t("examKeyboardHint")}</p>
      </div>
    </div>
  );
}
