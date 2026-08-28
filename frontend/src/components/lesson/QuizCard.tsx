import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { EnrichmentQuizItem } from "../../lib/types";

interface QuizCardProps {
  quiz: EnrichmentQuizItem[];
  /** whether the content came from the LLM or the fallback */
  source: "llm" | "fallback";
}

/** Gamified trivia over the lesson: one question at a time, running score and a
 * visible streak that resets on mistakes. */
export default function QuizCard({ quiz, source }: QuizCardProps) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [bestStreak, setBestStreak] = useState(0);
  const [finished, setFinished] = useState(false);

  if (quiz.length === 0) return null;
  const item = quiz[index];
  const answered = picked !== null;

  const choose = (i: number) => {
    if (answered) return;
    setPicked(i);
    if (i === item.correct_index) {
      setScore((s) => s + 1);
      setStreak((s) => {
        const next = s + 1;
        setBestStreak((b) => Math.max(b, next));
        return next;
      });
    } else {
      setStreak(0);
    }
  };

  const advance = () => {
    if (index + 1 >= quiz.length) {
      setFinished(true);
    } else {
      setIndex((i) => i + 1);
      setPicked(null);
    }
  };

  const restart = () => {
    setIndex(0);
    setPicked(null);
    setScore(0);
    setStreak(0);
    setFinished(false);
  };

  return (
    <section className="card p-5" aria-label={t("quickQuiz")}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-medium uppercase tracking-wider text-muted">
            {t("quickQuiz")}
          </h2>
          <span className="rounded bg-accent-soft px-2 py-0.5 text-2xs font-medium text-accent">
            {source === "llm" ? t("aiGenerated") : t("fallbackContent")}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted">
            {t("score")}: <strong className="text-text">{score}/{quiz.length}</strong>
          </span>
          <AnimatePresence mode="popLayout">
            <motion.span
              key={streak}
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className={`rounded-md px-2 py-0.5 font-medium ${
                streak > 0 ? "bg-warning/15 text-warning" : "bg-surface2 text-muted"
              }`}
              aria-live="polite"
            >
              🔥 {t("streak")}: {streak}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>

      {finished ? (
        <div className="py-4 text-center">
          <motion.p
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-lg font-semibold"
          >
            {t("quizDone")}: {score}/{quiz.length}
          </motion.p>
          <p className="mt-1 text-sm text-muted">
            🔥 {t("streak")} máx: {bestStreak}
          </p>
          <button className="btn mt-4" onClick={restart}>
            {t("playAgain")}
          </button>
        </div>
      ) : (
        <AnimatePresence mode="wait">
          <motion.div
            key={index}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            transition={{ duration: 0.18 }}
          >
            <p className="mb-1 text-xs text-muted">
              {index + 1} / {quiz.length}
            </p>
            <p className="mb-3 text-base font-medium">{item.question}</p>
            <div role="group" aria-label={item.question} className="space-y-2">
              {item.options.map((opt, i) => {
                const isCorrect = answered && i === item.correct_index;
                const isWrongPick = answered && picked === i && i !== item.correct_index;
                return (
                  <motion.button
                    key={i}
                    whileTap={answered ? undefined : { scale: 0.985 }}
                    onClick={() => choose(i)}
                    disabled={answered}
                    aria-pressed={picked === i}
                    className={`block w-full rounded-lg border px-4 py-2.5 text-left text-base transition-colors ${
                      isCorrect
                        ? "border-success bg-success-soft text-success"
                        : isWrongPick
                          ? "border-error bg-error-soft text-error"
                          : "border-border bg-surface hover:bg-surface2 disabled:opacity-70"
                    }`}
                  >
                    {opt}
                  </motion.button>
                );
              })}
            </div>
            {answered && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-3 flex items-center justify-between"
              >
                <span
                  className={`text-sm font-medium ${
                    picked === item.correct_index ? "text-success" : "text-error"
                  }`}
                  aria-live="polite"
                >
                  {picked === item.correct_index ? `✓ ${t("correct")}` : `✗ ${t("incorrect")}`}
                </span>
                <button className="btn btn-primary" onClick={advance}>
                  {index + 1 >= quiz.length ? t("testResult") : t("next")} →
                </button>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>
      )}
    </section>
  );
}
